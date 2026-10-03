"""NRW Jobs Router — ตลาดงาน/ฟรีแลนซ์ (มีระบบพักเงิน)

ผู้จ้างลงงาน → ฟรีแลนซ์ยื่นข้อเสนอ → ผู้จ้างเลือกคน (หักเงินพักไว้กับระบบ) →
ผู้จ้างกด "งานเสร็จ" = จ่ายฟรีแลนซ์ / ยกเลิก = คืนเงินผู้จ้าง (ทำได้ก่อนงานเสร็จ)"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.work import Job, JobProposal
from app.services.helpers import names, get_or_404, fmt
from app.services.wallet_ops import move_money, to_money

router = APIRouter()
LABELS = {"open": "เปิดรับ", "hired": "กำลังทำ", "done": "เสร็จแล้ว", "cancelled": "ยกเลิก"}


def job_dict(db, j, me):
    who = names(db, [j.client_id, j.freelancer_id])
    d = {"id": j.id, "title": j.title, "description": j.description, "budget": float(j.budget),
         "status": j.status, "status_label": LABELS[j.status], "client": who.get(j.client_id, "—"),
         "freelancer": who.get(j.freelancer_id), "date": fmt(j.created_at, False),
         "is_mine": bool(me and me.id == j.client_id), "is_hired_me": bool(me and me.id == j.freelancer_id)}
    if me and me.id == j.client_id:
        props = db.query(JobProposal).filter(JobProposal.job_id == j.id).all()
        pw = names(db, [p.freelancer_id for p in props])
        d["proposals"] = [{"id": p.id, "freelancer": pw.get(p.freelancer_id, "—"), "message": p.message} for p in props]
    return d


@router.get("")
def list_jobs(request: Request, scope: str = "open", db: Session = Depends(get_db)):
    me = optional_user(request, db)
    q = db.query(Job)
    if scope == "mine":
        if not me:
            raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
        q = q.filter((Job.client_id == me.id) | (Job.freelancer_id == me.id))
    else:
        q = q.filter(Job.status == "open")
    return {"jobs": [job_dict(db, j, me) for j in q.order_by(Job.id.desc()).limit(100).all()]}


class JobIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=5000)
    budget: float = Field(..., gt=0, le=10_000_000)


@router.post("")
def post_job(body: JobIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    j = Job(client_id=me.id, title=body.title.strip(), description=body.description.strip(), budget=to_money(body.budget))
    db.add(j)
    db.commit()
    return {"id": j.id}


class ProposalIn(BaseModel):
    message: str = Field(..., min_length=5, max_length=2000)


@router.post("/{job_id}/proposals")
def propose(job_id: int, body: ProposalIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    j = get_or_404(db, Job, job_id, "ไม่พบงาน")
    if j.status != "open" or j.client_id == me.id:
        raise HTTPException(status_code=400, detail="ยื่นข้อเสนองานนี้ไม่ได้")
    if db.query(JobProposal).filter(JobProposal.job_id == j.id, JobProposal.freelancer_id == me.id).first():
        raise HTTPException(status_code=400, detail="ยื่นข้อเสนอไปแล้ว")
    db.add(JobProposal(job_id=j.id, freelancer_id=me.id, message=body.message.strip()))
    db.commit()
    return {"ok": True}


@router.post("/{job_id}/hire/{proposal_id}")
def hire(job_id: int, proposal_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    j = get_or_404(db, Job, job_id, "ไม่พบงาน", lock=True)
    p = db.query(JobProposal).filter(JobProposal.id == proposal_id, JobProposal.job_id == j.id).first()
    if j.client_id != me.id or j.status != "open" or not p:
        raise HTTPException(status_code=400, detail="จ้างไม่ได้")
    move_money(db, me.id, -Decimal(str(j.budget)), "escrow", f"พักเงินค่าจ้าง งาน #{j.id}")
    j.status, j.freelancer_id = "hired", p.freelancer_id
    db.commit()
    return job_dict(db, j, me)


@router.post("/{job_id}/{action}")
def finish(job_id: int, action: str, request: Request, db: Session = Depends(get_db)):
    """action = complete (จ่ายฟรีแลนซ์) / cancel (คืนเงิน หรือปิดงานที่ยังไม่จ้าง)"""
    me = current_user(request, db)
    j = get_or_404(db, Job, job_id, "ไม่พบงาน", lock=True)
    if j.client_id != me.id or action not in ("complete", "cancel"):
        raise HTTPException(status_code=403, detail="เฉพาะผู้จ้าง")
    budget = Decimal(str(j.budget))
    if action == "complete":
        if j.status != "hired":
            raise HTTPException(status_code=400, detail="งานยังไม่ได้จ้างใคร")
        move_money(db, j.freelancer_id, budget, "job", f"ค่าจ้างงาน #{j.id}: {j.title}")
        j.status = "done"
    else:
        if j.status not in ("open", "hired"):
            raise HTTPException(status_code=400, detail="ยกเลิกไม่ได้แล้ว")
        if j.status == "hired":
            move_money(db, me.id, budget, "refund", f"คืนเงินพัก งาน #{j.id} ถูกยกเลิก")
        j.status = "cancelled"
    db.commit()
    return job_dict(db, j, me)
