"""NRW HR Router — พนักงาน/ตารางงาน/เงินเดือน (สมาชิกทุกคนเป็นเจ้าของกิจการ จัดการพนักงานของตัวเองได้)

พนักงาน:    GET/POST /hr/staff · PUT /hr/staff/{id}
ตารางงาน:   GET /hr/shifts?start=YYYY-MM-DD&days=7 · POST /hr/shifts (สร้าง/แทนที่กะของวันนั้น)
            DELETE /hr/shifts/{id} · POST /hr/shifts/{id}/status {status}
            POST /hr/shifts/copy-week {from_start, to_start} · POST /hr/shifts/confirm {start, days}
เงินเดือน:  GET /hr/payroll?month=YYYY-MM · POST/DELETE /hr/adjusts · POST /hr/payroll/{staff_id}/pay
            GET /hr/payroll/export.csv?month=
ฝั่งพนักงาน: GET /hr/me — ตารางงานของฉัน + สลิปเงินเดือน"""
import csv
import io
import re
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.user import User
from app.models.hr import Staff, Shift, PayAdjust, PayRun
from app.services.helpers import fmt, names
from app.services.payroll import calc, shift_hours, PAY_TYPES
from app.services.wallet_ops import move_money, to_money

router = APIRouter()
STATUS_LABELS = {"planned": "ตามตาราง", "worked": "มาทำงาน", "absent": "ขาด", "leave": "ลา"}
TIME_RE = r"^([01]\d|2[0-3]):[0-5]\d$"


def _month_range(month: str) -> tuple[date, date]:
    if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month or ""):
        raise HTTPException(status_code=400, detail="รูปแบบเดือนต้องเป็น YYYY-MM")
    y, m = map(int, month.split("-"))
    first = date(y, m, 1)
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return first, nxt


def _staff(db: Session, me: User, staff_id: int) -> Staff:
    s = db.query(Staff).filter(Staff.id == staff_id, Staff.owner_id == me.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงานของคุณ")
    return s


def staff_dict(s: Staff, unames: dict) -> dict:
    return {"id": s.id, "name": s.name, "position": s.position, "pay_type": s.pay_type,
            "pay_type_label": PAY_TYPES.get(s.pay_type, s.pay_type), "rate": float(s.rate),
            "ot_multiplier": float(s.ot_multiplier), "social_security": bool(s.social_security),
            "active": bool(s.active), "username": unames.get(s.user_id)}


def _unames(db: Session, ids) -> dict:
    ids = {i for i in ids if i}
    return {u.id: u.username for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}


# ─── พนักงาน ────────────────────────────────────────────────────
@router.get("/staff")
def list_staff(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    rows = db.query(Staff).filter(Staff.owner_id == me.id).order_by(Staff.active.desc(), Staff.name).all()
    un = _unames(db, [s.user_id for s in rows])
    return {"staff": [staff_dict(s, un) for s in rows]}


class StaffIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    position: str = Field("", max_length=120)
    pay_type: str = Field("monthly", pattern="^(monthly|daily|hourly)$")
    rate: float = Field(..., gt=0, le=10_000_000)
    ot_multiplier: float = Field(1.5, ge=1, le=5)
    social_security: bool = True
    active: bool = True
    username: str = Field("", max_length=50)      # ผูกบัญชีสมาชิก (ไม่บังคับ)


def _apply_staff(db: Session, s: Staff, body: StaffIn, me: User) -> None:
    s.name, s.position, s.pay_type = body.name.strip(), body.position.strip(), body.pay_type
    s.rate, s.ot_multiplier = to_money(body.rate), Decimal(str(body.ot_multiplier))
    s.social_security, s.active = body.social_security, body.active
    uname = body.username.strip().lstrip("@").lower()
    if uname:
        u = db.query(User).filter(User.username == uname, User.is_active == True).first()
        if not u:
            raise HTTPException(status_code=404, detail=f"ไม่พบสมาชิก @{uname}")
        s.user_id = u.id
    else:
        s.user_id = None


@router.post("/staff")
def add_staff(body: StaffIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    s = Staff(owner_id=me.id, name="", rate=0)
    _apply_staff(db, s, body, me)
    db.add(s)
    db.commit()
    return staff_dict(s, _unames(db, [s.user_id]))


@router.put("/staff/{staff_id}")
def edit_staff(staff_id: int, body: StaffIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    s = _staff(db, me, staff_id)
    _apply_staff(db, s, body, me)
    db.commit()
    return staff_dict(s, _unames(db, [s.user_id]))


# ─── ตารางงาน ───────────────────────────────────────────────────
def shift_dict(sh: Shift) -> dict:
    return {"id": sh.id, "staff_id": sh.staff_id, "day": sh.day.isoformat(), "start": sh.start, "end": sh.end,
            "break_min": sh.break_min, "hours": float(shift_hours(sh.start, sh.end, sh.break_min)),
            "status": sh.status, "status_label": STATUS_LABELS[sh.status], "note": sh.note}


@router.get("/shifts")
def list_shifts(request: Request, start: date | None = None, days: int = 7, db: Session = Depends(get_db)):
    me = current_user(request, db)
    start = start or (date.today() - timedelta(days=date.today().weekday()))
    days = max(1, min(days, 42))
    rows = (db.query(Shift).filter(Shift.owner_id == me.id, Shift.day >= start, Shift.day < start + timedelta(days=days))
              .order_by(Shift.day, Shift.start).all())
    staff = db.query(Staff).filter(Staff.owner_id == me.id, Staff.active == True).order_by(Staff.name).all()
    un = _unames(db, [s.user_id for s in staff])
    return {"start": start.isoformat(), "days": [(start + timedelta(days=i)).isoformat() for i in range(days)],
            "staff": [staff_dict(s, un) for s in staff], "shifts": [shift_dict(x) for x in rows]}


class ShiftIn(BaseModel):
    staff_id: int
    day: date
    start: str = Field(..., pattern=TIME_RE)
    end: str = Field(..., pattern=TIME_RE)
    break_min: int = Field(60, ge=0, le=600)
    status: str = Field("planned", pattern="^(planned|worked|absent|leave)$")
    note: str = Field("", max_length=200)


@router.post("/shifts")
def save_shift(body: ShiftIn, request: Request, db: Session = Depends(get_db)):
    """1 คน 1 กะต่อวัน — ถ้ามีอยู่แล้วจะแทนที่"""
    me = current_user(request, db)
    _staff(db, me, body.staff_id)
    if shift_hours(body.start, body.end, body.break_min) <= 0:
        raise HTTPException(status_code=400, detail="ชั่วโมงทำงานต้องมากกว่าเวลาพัก")
    sh = db.query(Shift).filter(Shift.staff_id == body.staff_id, Shift.day == body.day).first()
    if not sh:
        sh = Shift(owner_id=me.id, staff_id=body.staff_id, day=body.day)
        db.add(sh)
    sh.start, sh.end, sh.break_min, sh.status, sh.note = body.start, body.end, body.break_min, body.status, body.note.strip()
    db.commit()
    return shift_dict(sh)


def _my_shift(db: Session, me: User, shift_id: int) -> Shift:
    sh = db.query(Shift).filter(Shift.id == shift_id, Shift.owner_id == me.id).first()
    if not sh:
        raise HTTPException(status_code=404, detail="ไม่พบกะงาน")
    return sh


@router.delete("/shifts/{shift_id}")
def delete_shift(shift_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    db.delete(_my_shift(db, me, shift_id))
    db.commit()
    return {"ok": True}


class StatusIn(BaseModel):
    status: str = Field(..., pattern="^(planned|worked|absent|leave)$")


@router.post("/shifts/{shift_id}/status")
def shift_status(shift_id: int, body: StatusIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    sh = _my_shift(db, me, shift_id)
    sh.status = body.status
    db.commit()
    return shift_dict(sh)


class CopyIn(BaseModel):
    from_start: date
    to_start: date


@router.post("/shifts/copy-week")
def copy_week(body: CopyIn, request: Request, db: Session = Depends(get_db)):
    """คัดลอกตาราง 7 วัน ไปยังอีกสัปดาห์ (กะที่มีอยู่แล้วในวันปลายทางจะไม่ถูกทับ)"""
    me = current_user(request, db)
    src = db.query(Shift).filter(Shift.owner_id == me.id, Shift.day >= body.from_start,
                                 Shift.day < body.from_start + timedelta(days=7)).all()
    shift_by = body.to_start - body.from_start
    taken = {(s.staff_id, s.day) for s in db.query(Shift).filter(
        Shift.owner_id == me.id, Shift.day >= body.to_start, Shift.day < body.to_start + timedelta(days=7)).all()}
    n = 0
    for s in src:
        key = (s.staff_id, s.day + shift_by)
        if key in taken:
            continue
        db.add(Shift(owner_id=me.id, staff_id=s.staff_id, day=s.day + shift_by, start=s.start, end=s.end,
                     break_min=s.break_min, status="planned", note=s.note))
        n += 1
    db.commit()
    return {"copied": n}


class ConfirmIn(BaseModel):
    start: date
    days: int = Field(7, ge=1, le=42)


@router.post("/shifts/confirm")
def confirm_worked(body: ConfirmIn, request: Request, db: Session = Depends(get_db)):
    """เปลี่ยนกะ 'ตามตาราง' ที่ผ่านมาแล้ว (ถึงวันนี้) เป็น 'มาทำงาน' ทีเดียว"""
    me = current_user(request, db)
    end = min(body.start + timedelta(days=body.days), date.today() + timedelta(days=1))
    n = (db.query(Shift).filter(Shift.owner_id == me.id, Shift.status == "planned", Shift.day >= body.start, Shift.day < end)
           .update({"status": "worked"}, synchronize_session=False))
    db.commit()
    return {"confirmed": n}


# ─── เงินเดือน ──────────────────────────────────────────────────
def _payroll(db: Session, me: User, month: str) -> list[dict]:
    first, nxt = _month_range(month)
    staff = db.query(Staff).filter(Staff.owner_id == me.id).order_by(Staff.name).all()
    shifts = db.query(Shift).filter(Shift.owner_id == me.id, Shift.day >= first, Shift.day < nxt).all()
    adjusts = db.query(PayAdjust).filter(PayAdjust.owner_id == me.id, PayAdjust.month == month).all()
    runs = {r.staff_id: r for r in db.query(PayRun).filter(PayRun.owner_id == me.id, PayRun.month == month).all()}
    un = _unames(db, [s.user_id for s in staff])
    out = []
    for s in staff:
        mine = [x for x in shifts if x.staff_id == s.id]
        adj = [a for a in adjusts if a.staff_id == s.id]
        if not s.active and not mine and not adj and s.id not in runs:
            continue
        r = runs.get(s.id)
        out.append({"staff": staff_dict(s, un), **calc(s, mine, adj),
                    "planned_unconfirmed": sum(1 for x in mine if x.status == "planned"),
                    "adjusts": [{"id": a.id, "amount": float(a.amount), "note": a.note} for a in adj],
                    "paid": {"net": float(r.net), "method": r.method, "date": fmt(r.paid_at)} if r else None})
    return out


@router.get("/payroll")
def payroll(request: Request, month: str = "", db: Session = Depends(get_db)):
    me = current_user(request, db)
    month = month or date.today().strftime("%Y-%m")
    rows = _payroll(db, me, month)
    return {"month": month, "rows": rows,
            "totals": {k: round(sum(r[k] for r in rows), 2) for k in ("gross", "deductions", "social_security", "net")}}


class AdjustIn(BaseModel):
    staff_id: int
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    amount: float = Field(..., ge=-10_000_000, le=10_000_000)
    note: str = Field(..., min_length=1, max_length=200)


@router.post("/adjusts")
def add_adjust(body: AdjustIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    _staff(db, me, body.staff_id)
    if not body.amount:
        raise HTTPException(status_code=400, detail="จำนวนเงินต้องไม่เป็น 0")
    if db.query(PayRun).filter(PayRun.staff_id == body.staff_id, PayRun.month == body.month).first():
        raise HTTPException(status_code=400, detail="จ่ายเงินเดือนเดือนนี้ไปแล้ว แก้ไม่ได้")
    a = PayAdjust(owner_id=me.id, staff_id=body.staff_id, month=body.month, amount=to_money(body.amount), note=body.note.strip())
    db.add(a)
    db.commit()
    return {"id": a.id}


@router.delete("/adjusts/{adjust_id}")
def delete_adjust(adjust_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    a = db.query(PayAdjust).filter(PayAdjust.id == adjust_id, PayAdjust.owner_id == me.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="ไม่พบรายการ")
    if db.query(PayRun).filter(PayRun.staff_id == a.staff_id, PayRun.month == a.month).first():
        raise HTTPException(status_code=400, detail="จ่ายเงินเดือนเดือนนี้ไปแล้ว แก้ไม่ได้")
    db.delete(a)
    db.commit()
    return {"ok": True}


class PayIn(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    method: str = Field("wallet", pattern="^(wallet|manual)$")


@router.post("/payroll/{staff_id}/pay")
def pay(staff_id: int, body: PayIn, request: Request, db: Session = Depends(get_db)):
    """wallet = โอนจากกระเป๋าเจ้าของเข้ากระเป๋าพนักงาน (ต้องผูกบัญชี) · manual = บันทึกว่าจ่ายเองแล้ว (เงินสด/โอนธนาคาร)"""
    me = current_user(request, db)
    s = _staff(db, me, staff_id)
    if db.query(PayRun).filter(PayRun.staff_id == s.id, PayRun.month == body.month).first():
        raise HTTPException(status_code=400, detail="จ่ายเงินเดือนเดือนนี้ไปแล้ว")
    row = next((r for r in _payroll(db, me, body.month) if r["staff"]["id"] == s.id), None)
    if not row or row["net"] <= 0:
        raise HTTPException(status_code=400, detail="ยอดสุทธิเป็น 0 — ยืนยันการมาทำงานในตารางก่อน")
    net = to_money(row["net"])
    if body.method == "wallet":
        if not s.user_id:
            raise HTTPException(status_code=400, detail="พนักงานยังไม่ผูกบัญชีสมาชิก — เลือก 'บันทึกว่าจ่ายแล้ว' แทน")
        move_money(db, me.id, -net, "payroll", f"จ่ายเงินเดือน {body.month}: {s.name}")
        move_money(db, s.user_id, net, "payroll", f"เงินเดือน {body.month} จาก {me.full_name or me.username}")
    db.add(PayRun(owner_id=me.id, staff_id=s.id, month=body.month, gross=to_money(row["gross"]),
                  deductions=to_money(row["deductions"]), net=net, method=body.method))
    db.commit()
    return {"ok": True, "net": float(net)}


@router.get("/payroll/export.csv")
def payroll_csv(request: Request, month: str = "", db: Session = Depends(get_db)):
    me = current_user(request, db)
    month = month or date.today().strftime("%Y-%m")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["พนักงาน", "ตำแหน่ง", "ประเภท", "อัตรา", "วันทำงาน", "ขาด", "ลา", "ชม.ปกติ", "ชม.OT", "ค่าจ้างฐาน",
                "หักขาดงาน", "ค่า OT", "เงินเพิ่ม", "ประกันสังคม", "หักอื่น", "รวมรับ", "รวมหัก", "สุทธิ", "สถานะ"])
    for r in _payroll(db, me, month):
        s = r["staff"]
        w.writerow([s["name"], s["position"], s["pay_type_label"], s["rate"], r["days_worked"], r["days_absent"], r["days_leave"],
                    r["regular_hours"], r["ot_hours"], r["base"], r["absent_deduct"], r["ot_pay"], r["additions"],
                    r["social_security"], r["other_deductions"], r["gross"], r["deductions"], r["net"],
                    "จ่ายแล้ว" if r["paid"] else "ยังไม่จ่าย"])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=payroll-{month}.csv"})


# ─── ฝั่งพนักงาน ────────────────────────────────────────────────
@router.get("/me")
def my_work(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    jobs = db.query(Staff).filter(Staff.user_id == me.id).all()
    if not jobs:
        return {"jobs": [], "shifts": [], "payslips": []}
    ids = [s.id for s in jobs]
    employers = names(db, [s.owner_id for s in jobs])
    by_id = {s.id: s for s in jobs}
    today = date.today()
    shifts = (db.query(Shift).filter(Shift.staff_id.in_(ids), Shift.day >= today - timedelta(days=7),
                                     Shift.day < today + timedelta(days=21)).order_by(Shift.day, Shift.start).all())
    runs = db.query(PayRun).filter(PayRun.staff_id.in_(ids)).order_by(PayRun.id.desc()).limit(24).all()
    return {"jobs": [{"employer": employers.get(s.owner_id, "—"), "position": s.position, "active": bool(s.active)} for s in jobs],
            "shifts": [{**shift_dict(x), "employer": employers.get(by_id[x.staff_id].owner_id, "—")} for x in shifts],
            "payslips": [{"month": r.month, "employer": employers.get(by_id[r.staff_id].owner_id, "—"), "gross": float(r.gross),
                          "deductions": float(r.deductions), "net": float(r.net),
                          "method": "โอนเข้ากระเป๋า" if r.method == "wallet" else "จ่ายนอกระบบ", "date": fmt(r.paid_at)} for r in runs]}
