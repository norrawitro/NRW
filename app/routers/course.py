"""NRW Course Router — คอร์สเรียนออนไลน์แบบอินเตอร์แอกทีฟ

ผู้สอน:  สร้างคอร์ส (รอผู้ดูแลอนุมัติ) → เพิ่มบทเรียน: เนื้อหาด้านบน + คำถามด้านล่าง (ปรนัย/อัตนัย)
ผู้เรียน: ซื้อคอร์ส (จ่ายผู้สอนผ่านกระเป๋าเงิน) → เรียนทีละบท → ตอบคำถาม ระบบตรวจทันที
         ตอบถูกครบทุกข้อ = จบบทนั้น (บทที่ไม่มีคำถาม กด "เรียนจบบทนี้" เอง)
เฉลยเก็บที่ server เท่านั้น — ผู้เรียนไม่เห็นเฉลยในหน้าเว็บ"""
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, optional_user
from app.models.work import Course, Lesson, Enrollment, LessonQuestion, LessonAnswer
from app.services.helpers import names, get_or_404
from app.services.moderation import submit, hidden_ids, badge, ensure_visible
from app.services.wallet_ops import move_money, to_money

router = APIRouter()


def _enrollment(db, course_id, user_id):
    return db.query(Enrollment).filter(Enrollment.course_id == course_id, Enrollment.user_id == user_id).first()


def _done_set(en) -> set[str]:
    return set(filter(None, (en.done if en else "").split(",")))


def _mark_done(en, lesson_id: int):
    en.done = ",".join(sorted(_done_set(en) | {str(lesson_id)}, key=int))


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


# ─── รายการคอร์ส ────────────────────────────────────────────────
@router.get("")
def list_courses(request: Request, db: Session = Depends(get_db)):
    me = optional_user(request, db)
    hidden = hidden_ids(db, "course")
    courses = [c for c in db.query(Course).filter(Course.is_published == True).order_by(Course.id.desc()).all()
               if c.id not in hidden or (me and me.id == c.instructor_id)]
    who = names(db, [c.instructor_id for c in courses])
    out = []
    for c in courses:
        en = _enrollment(db, c.id, me.id) if me else None
        n_lessons = db.query(Lesson).filter(Lesson.course_id == c.id).count()
        out.append({"id": c.id, "title": c.title, "description": c.description, "price": float(c.price),
                    "instructor": who.get(c.instructor_id, "—"), "lessons": n_lessons,
                    "students": db.query(Enrollment).filter(Enrollment.course_id == c.id).count(),
                    "is_mine": bool(me and me.id == c.instructor_id), "enrolled": en is not None,
                    "progress": f"{len(_done_set(en))}/{n_lessons}" if en else None,
                    "mod": badge(db, "course", c.id) if (me and me.id == c.instructor_id) else None})
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
    db.flush()
    status = submit(db, "course", c.id, me)
    db.commit()
    return {"id": c.id, "mod_status": status}


# ─── รายละเอียดคอร์ส + บทเรียน ──────────────────────────────────
def _question_dict(db, q: LessonQuestion, user_id: int, show_answer: bool) -> dict:
    a = db.query(LessonAnswer).filter(LessonAnswer.question_id == q.id, LessonAnswer.user_id == user_id).first()
    d = {"id": q.id, "kind": q.kind, "prompt": q.prompt, "choices": json.loads(q.choices or "[]"),
         "my_answer": a.answer if a else None, "correct": bool(a and a.correct), "tries": a.tries if a else 0,
         "explanation": q.explanation if (a and a.correct) or show_answer else None}
    if show_answer:
        d["answer"] = q.answer
    return d


@router.get("/{course_id}")
def course_detail(course_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = get_or_404(db, Course, course_id, "ไม่พบคอร์ส")
    ensure_visible(db, "course", c.id, c.instructor_id, me, "ไม่พบคอร์ส")
    is_owner = c.instructor_id == me.id
    en = _enrollment(db, c.id, me.id)
    can_view = is_owner or en is not None
    done = _done_set(en)
    lessons = db.query(Lesson).filter(Lesson.course_id == c.id).order_by(Lesson.position, Lesson.id).all()
    out = []
    for l in lessons:
        d = {"id": l.id, "title": l.title, "done": str(l.id) in done}
        if can_view:
            qs = db.query(LessonQuestion).filter(LessonQuestion.lesson_id == l.id).order_by(LessonQuestion.position, LessonQuestion.id).all()
            d.update(content=l.content, video_id=l.video_id, questions=[_question_dict(db, q, me.id, is_owner) for q in qs])
        out.append(d)
    return {"id": c.id, "title": c.title, "description": c.description, "price": float(c.price),
            "instructor": names(db, [c.instructor_id]).get(c.instructor_id, "—"),
            "is_mine": is_owner, "enrolled": en is not None, "progress": f"{len(done)}/{len(lessons)}",
            "mod": badge(db, "course", c.id) if is_owner else None, "lessons": out}


class QuestionIn(BaseModel):
    kind: str = Field(..., pattern="^(choice|text)$")
    prompt: str = Field(..., min_length=1, max_length=2000)
    choices: list[str] = Field(default_factory=list, max_length=8)
    answer: str = Field(..., min_length=1, max_length=500)   # choice: ลำดับตัวเลือก (0,1,2..) · text: คำตอบที่ยอมรับ คั่นด้วย |
    explanation: str = Field("", max_length=2000)


class LessonIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=20000)
    video_id: int | None = None
    questions: list[QuestionIn] = Field(default_factory=list, max_length=20)


@router.post("/{course_id}/lessons")
def add_lesson(course_id: int, body: LessonIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = get_or_404(db, Course, course_id, "ไม่พบคอร์ส")
    if c.instructor_id != me.id:
        raise HTTPException(status_code=403, detail="เฉพาะผู้สอน")
    for i, q in enumerate(body.questions, 1):
        if q.kind == "choice":
            opts = [x.strip() for x in q.choices if x.strip()]
            if len(opts) < 2:
                raise HTTPException(status_code=400, detail=f"คำถามข้อ {i}: ปรนัยต้องมีอย่างน้อย 2 ตัวเลือก")
            if not q.answer.isdigit() or int(q.answer) >= len(opts):
                raise HTTPException(status_code=400, detail=f"คำถามข้อ {i}: เลือกตัวเลือกที่ถูกต้อง")
    pos = db.query(Lesson).filter(Lesson.course_id == c.id).count() + 1
    lesson = Lesson(course_id=c.id, position=pos, title=body.title.strip(), content=body.content, video_id=body.video_id)
    db.add(lesson)
    db.flush()
    for i, q in enumerate(body.questions, 1):
        opts = [x.strip() for x in q.choices if x.strip()] if q.kind == "choice" else []
        db.add(LessonQuestion(lesson_id=lesson.id, position=i, kind=q.kind, prompt=q.prompt.strip(),
                              choices=json.dumps(opts, ensure_ascii=False), answer=q.answer.strip(),
                              explanation=q.explanation.strip()))
    db.commit()
    return {"id": lesson.id}


@router.delete("/{course_id}/lessons/{lesson_id}")
def delete_lesson(course_id: int, lesson_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = get_or_404(db, Course, course_id, "ไม่พบคอร์ส")
    l = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == c.id).first()
    if c.instructor_id != me.id or not l:
        raise HTTPException(status_code=404, detail="ไม่พบบทเรียน")
    for q in db.query(LessonQuestion).filter(LessonQuestion.lesson_id == l.id).all():
        db.query(LessonAnswer).filter(LessonAnswer.question_id == q.id).delete()
        db.delete(q)
    db.delete(l)
    db.commit()
    return {"ok": True}


# ─── ซื้อคอร์ส ──────────────────────────────────────────────────
@router.post("/{course_id}/enroll")
def enroll(course_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    c = get_or_404(db, Course, course_id, "ไม่พบคอร์ส")
    if c.instructor_id == me.id:
        raise HTTPException(status_code=400, detail="เป็นผู้สอนคอร์สนี้อยู่แล้ว")
    ensure_visible(db, "course", c.id, c.instructor_id, None, "ไม่พบคอร์ส")
    if _enrollment(db, c.id, me.id):
        raise HTTPException(status_code=400, detail="ซื้อคอร์สนี้แล้ว")
    price = Decimal(str(c.price))
    if price > 0:
        move_money(db, me.id, -price, "course", f"ซื้อคอร์ส: {c.title}")
        move_money(db, c.instructor_id, price, "course", f"รายได้คอร์ส: {c.title}")
    db.add(Enrollment(course_id=c.id, user_id=me.id))
    db.commit()
    return {"ok": True}


# ─── เรียน + ตอบคำถาม ───────────────────────────────────────────
def _lesson_for_student(db, course_id, lesson_id, me):
    en = _enrollment(db, course_id, me.id)
    l = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first()
    if not en or not l:
        raise HTTPException(status_code=404, detail="ไม่พบบทเรียน (ซื้อคอร์สก่อน)")
    return en, l


@router.post("/{course_id}/lessons/{lesson_id}/done")
def mark_done(course_id: int, lesson_id: int, request: Request, db: Session = Depends(get_db)):
    """บทที่ไม่มีคำถาม — กดเรียนจบเอง"""
    me = current_user(request, db)
    en, l = _lesson_for_student(db, course_id, lesson_id, me)
    if db.query(LessonQuestion).filter(LessonQuestion.lesson_id == l.id).count():
        raise HTTPException(status_code=400, detail="บทนี้มีคำถาม — ตอบถูกครบทุกข้อเพื่อจบบท")
    _mark_done(en, l.id)
    db.commit()
    return {"ok": True}


class AnswerIn(BaseModel):
    answer: str = Field(..., min_length=1, max_length=2000)


@router.post("/{course_id}/lessons/{lesson_id}/questions/{question_id}/answer")
def answer(course_id: int, lesson_id: int, question_id: int, body: AnswerIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    en, l = _lesson_for_student(db, course_id, lesson_id, me)
    q = db.query(LessonQuestion).filter(LessonQuestion.id == question_id, LessonQuestion.lesson_id == l.id).first()
    if not q:
        raise HTTPException(status_code=404, detail="ไม่พบคำถาม")
    if q.kind == "choice":
        correct = body.answer.strip() == q.answer.strip()
    else:
        correct = _norm(body.answer) in {_norm(x) for x in q.answer.split("|") if x.strip()}
    a = db.query(LessonAnswer).filter(LessonAnswer.question_id == q.id, LessonAnswer.user_id == me.id).first()
    if not a:
        a = LessonAnswer(question_id=q.id, user_id=me.id, tries=0)
        db.add(a)
    if not a.correct:                       # ตอบถูกแล้วไม่เปลี่ยนผล
        a.answer, a.correct = body.answer.strip()[:2000], correct
    a.tries = (a.tries or 0) + 1
    db.flush()
    qids = [x.id for x in db.query(LessonQuestion).filter(LessonQuestion.lesson_id == l.id).all()]
    right = db.query(LessonAnswer).filter(LessonAnswer.user_id == me.id, LessonAnswer.question_id.in_(qids),
                                          LessonAnswer.correct == True).count()
    lesson_done = right == len(qids)
    if lesson_done:
        _mark_done(en, l.id)
    db.commit()
    return {"correct": correct, "explanation": q.explanation if correct else None,
            "lesson_done": lesson_done, "progress": f"{right}/{len(qids)}"}
