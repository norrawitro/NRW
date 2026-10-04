"""NRW payroll — คำนวณเงินเดือนจากตารางกะ (ฟังก์ชันล้วน ไม่แตะฐานข้อมูล ทดสอบง่าย)

กติกา (แก้ค่าคงที่ได้ที่นี่):
- ชั่วโมงทำงานต่อกะ = เวลาเลิก − เวลาเข้า − พัก; เกิน 8 ชม./วัน = OT (ค่าแรงต่อชั่วโมง × ot_multiplier)
- รายเดือน: ได้เต็ม, หักวันขาดงาน = เงินเดือน/30 ต่อวัน, ค่าแรงต่อชม. = เงินเดือน/30/8
- รายวัน: ค่าแรง × วันที่มาทำงาน, ค่าแรงต่อชม. = ค่าแรงต่อวัน/8
- รายชั่วโมง: ค่าแรง × ชั่วโมงปกติ
- ประกันสังคม 5% ของค่าจ้าง (ฐาน 1,650–15,000 บาท → หักสูงสุด 750)
- นับเฉพาะกะที่สถานะ worked (มาทำงาน) — planned ยังไม่นับจนกว่าจะยืนยัน, absent = ขาด, leave = ลา (รายเดือนไม่หัก)"""
from decimal import Decimal, ROUND_HALF_UP

DAY_HOURS = Decimal(8)
SSO_RATE = Decimal("0.05")
SSO_MIN_BASE, SSO_MAX_BASE = Decimal(1650), Decimal(15000)
PAY_TYPES = {"monthly": "รายเดือน", "daily": "รายวัน", "hourly": "รายชั่วโมง"}


def q2(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def shift_hours(start: str, end: str, break_min: int) -> Decimal:
    sh, sm = map(int, start.split(":")); eh, em = map(int, end.split(":"))
    mins = (eh * 60 + em) - (sh * 60 + sm)
    if mins <= 0:
        mins += 24 * 60                    # กะข้ามคืน
    return max(Decimal(mins - (break_min or 0)) / 60, Decimal(0))


def calc(staff, shifts, adjusts) -> dict:
    """staff: มี pay_type, rate, ot_multiplier, social_security · shifts: มี start,end,break_min,status · adjusts: มี amount,note"""
    rate, mult = Decimal(str(staff.rate)), Decimal(str(staff.ot_multiplier or 1.5))
    worked = [s for s in shifts if s.status == "worked"]
    absent = sum(1 for s in shifts if s.status == "absent")
    leave = sum(1 for s in shifts if s.status == "leave")
    reg_h = ot_h = Decimal(0)
    for s in worked:
        h = shift_hours(s.start, s.end, s.break_min)
        reg_h += min(h, DAY_HOURS)
        ot_h += max(h - DAY_HOURS, Decimal(0))
    if staff.pay_type == "monthly":
        hourly = rate / 30 / DAY_HOURS
        base, absent_deduct = rate, rate / 30 * absent
    elif staff.pay_type == "daily":
        hourly = rate / DAY_HOURS
        base, absent_deduct = rate * len(worked), Decimal(0)
    else:
        hourly = rate
        base, absent_deduct = rate * reg_h, Decimal(0)
    ot_pay = hourly * mult * ot_h
    plus = sum((Decimal(str(a.amount)) for a in adjusts if Decimal(str(a.amount)) > 0), Decimal(0))
    minus = -sum((Decimal(str(a.amount)) for a in adjusts if Decimal(str(a.amount)) < 0), Decimal(0))
    wage = max(base - absent_deduct + ot_pay, Decimal(0))
    sso = q2(min(max(wage, SSO_MIN_BASE), SSO_MAX_BASE) * SSO_RATE) if staff.social_security and wage > 0 else Decimal(0)
    gross = q2(wage + plus)
    deductions = q2(sso + minus)
    return {"pay_type": staff.pay_type, "pay_type_label": PAY_TYPES.get(staff.pay_type, staff.pay_type),
            "days_worked": len(worked), "days_absent": absent, "days_leave": leave,
            "regular_hours": float(q2(reg_h)), "ot_hours": float(q2(ot_h)), "hourly_rate": float(q2(hourly)),
            "base": float(q2(base)), "absent_deduct": float(q2(absent_deduct)), "ot_pay": float(q2(ot_pay)),
            "additions": float(q2(plus)), "other_deductions": float(q2(minus)), "social_security": float(sso),
            "gross": float(gross), "deductions": float(deductions), "net": float(max(gross - deductions, Decimal(0)))}
