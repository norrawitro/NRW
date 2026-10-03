"""NRW Course Router — คอร์สเรียนออนไลน์: ใครก็สร้างคอร์สได้, ผู้เรียนจ่ายผ่านกระเป๋าเงิน (เงินเข้าผู้สอน)
บทเรียนเปิดดูได้เฉพาะผู้สอนและผู้ที่ลงทะเบียนแล้ว · บทเรียนแนบวิดีโอจากระบบวิดีโอได้ (video_id)"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.work import Course, Lesson, Enrollment
from app.services.helpers import names, get_or_404
from app.services.wallet_ops import move_money, to_money

router = APIRouter()


def _enrollment(db, course_id, user_id):
    return db.query(Enrollment).filter(Enrollment.course_id == course_id, Enrollment.user_id == user_id).first()


@router.get("")
def list_courses(request: Request, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    courses = db.query(Course).filter(Course.is_published == True).order_by(Course.id.desc()).all()
    who = names(db, [c.instructor_id for c in courses])
    out = []
    for c in courses:
        out.append({"id": c.id, "title": c.title, "description": c.description, "price": float(c.price),
                    "instructor": who.get(c.instructor_id, "—"),
                    "lessons": db.query(Lesson).filter(Lesson.course_id == c.id).count(),
                    "students": db.query(Enrollment).filter(Enrollment.course_id == c.id).count(),
                    "is_mine": bool(me and me.id == c.instructor_id),
                    "enrolled": bool(me and _enrollment(db, c.id, me.id))})
    return {"courses": out}


class CourseIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field("", max_length=5000)
    price: float = Field(0, ge=0, le=1_000_000)


@router.post("")
def create_course(body: CourseIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = Course(instructor_id=me.id, title=body.title.strip(), description=body.description.strip(), price=to_money(body.price))
    db.add(c)
    db.commit()
    return {"id": c.id}


@router.get("/{course_id}")
def course_detail(course_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = get_or_404(db, Course, course_id, "ไม่พบคอร์ส")
    is_owner = c.instructor_id == me.id
    en = _enrollment(db, c.id, me.id)
    can_view = is_owner or en is not None
    done = set(filter(None, (en.done if en else "").split(",")))
    lessons = db.query(Lesson).filter(Lesson.course_id == c.id).order_by(Lesson.position, Lesson.id).all()
    return {"id": c.id, "title": c.title, "description": c.description, "price": float(c.price),
            "is_mine": is_owner, "enrolled": en is not None, "progress": f"{len(done)}/{len(lessons)}",
            "lessons": [{"id": l.id, "title": l.title, "done": str(l.id) in done,
                         **({"content": l.content, "video_id": l.video_id} if can_view else {})} for l in lessons]}


class LessonIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=20000)
    video_id: int | None = None


@router.post("/{course_id}/lessons")
def add_lesson(course_id: int, body: LessonIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = get_or_404(db, Course, course_id, "ไม่พบคอร์ส")
    if c.instructor_id != me.id:
        raise HTTPException(status_code=403, detail="เฉพาะผู้สอน")
    pos = db.query(Lesson).filter(Lesson.course_id == c.id).count() + 1
    db.add(Lesson(course_id=c.id, position=pos, title=body.title.strip(), content=body.content, video_id=body.video_id))
    db.commit()
    return {"ok": True}


@router.post("/{course_id}/enroll")
def enroll(course_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = get_or_404(db, Course, course_id, "ไม่พบคอร์ส")
    if c.instructor_id == me.id:
        raise HTTPException(status_code=400, detail="เป็นผู้สอนคอร์สนี้อยู่แล้ว")
    if _enrollment(db, c.id, me.id):
        raise HTTPException(status_code=400, detail="ลงทะเบียนแล้ว")
    price = Decimal(str(c.price))
    if price > 0:
        move_money(db, me.id, -price, "course", f"ลงทะเบียนคอร์ส: {c.title}")
        move_money(db, c.instructor_id, price, "course", f"รายได้คอร์ส: {c.title}")
    db.add(Enrollment(course_id=c.id, user_id=me.id))
    db.commit()
    return {"ok": True}


@router.post("/{course_id}/lessons/{lesson_id}/done")
def mark_done(course_id: int, lesson_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    en = _enrollment(db, course_id, me.id)
    if not en or not db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first():
        raise HTTPException(status_code=404, detail="ไม่พบบทเรียน")
    done = set(filter(None, en.done.split(","))) | {str(lesson_id)}
    en.done = ",".join(sorted(done, key=int))
    db.commit()
    return {"ok": True}
