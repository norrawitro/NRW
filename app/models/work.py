"""NRW ช่วงที่ 3 models — แชท, คอร์สเรียน, ตลาดงาน, พื้นที่ทำงาน, โฆษณา"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base


# ─── แชท ────────────────────────────────────────────────────────
class ChatMessage(Base):
    """room = 'general' (ห้องรวม) หรือ 'dm:<id เล็ก>:<id ใหญ่>' (คุยส่วนตัว)"""
    __tablename__ = "chat_messages"
    id         = Column(Integer, primary_key=True)
    room       = Column(String(50), nullable=False, index=True)
    sender_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── คอร์สเรียน ─────────────────────────────────────────────────
class Course(Base):
    __tablename__ = "courses"
    id            = Column(Integer, primary_key=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title         = Column(String(200), nullable=False)
    description   = Column(Text, nullable=False, default="")
    price         = Column(Numeric(12, 2), nullable=False, default=0)
    is_published  = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class Lesson(Base):
    __tablename__ = "course_lessons"
    id         = Column(Integer, primary_key=True)
    course_id  = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    position   = Column(Integer, nullable=False, default=1)
    title      = Column(String(200), nullable=False)
    content    = Column(Text, nullable=False, default="")
    video_id   = Column(Integer, nullable=True)            # วิดีโอจากระบบวิดีโอ (ถ้ามี)


class Enrollment(Base):
    __tablename__ = "course_enrollments"
    id         = Column(Integer, primary_key=True)
    course_id  = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    done       = Column(Text, nullable=False, default="")  # id บทที่เรียนจบ คั่นด้วย ,
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── ตลาดงาน/ฟรีแลนซ์ ───────────────────────────────────────────
class Job(Base):
    """open → hired (เงินพักไว้กับระบบ) → done (จ่ายฟรีแลนซ์) / cancelled (คืนผู้จ้าง)"""
    __tablename__ = "jobs"
    id            = Column(Integer, primary_key=True)
    client_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title         = Column(String(200), nullable=False)
    description   = Column(Text, nullable=False, default="")
    budget        = Column(Numeric(12, 2), nullable=False)
    status        = Column(String(20), nullable=False, default="open", index=True)
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class JobProposal(Base):
    __tablename__ = "job_proposals"
    id            = Column(Integer, primary_key=True)
    job_id        = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message       = Column(Text, nullable=False, default="")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


# ─── พื้นที่ทำงานร่วมกัน ─────────────────────────────────────────
class Workspace(Base):
    __tablename__ = "workspaces"
    id         = Column(Integer, primary_key=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    name       = Column(String(200), nullable=False)
    notes      = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    id           = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)


class WorkspaceTask(Base):
    __tablename__ = "workspace_tasks"
    id           = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    title        = Column(String(300), nullable=False)
    status       = Column(String(20), nullable=False, default="todo")   # todo / doing / done
    assignee_id  = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


# ─── โฆษณา ──────────────────────────────────────────────────────
class Ad(Base):
    __tablename__ = "ads"
    id         = Column(Integer, primary_key=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title      = Column(String(100), nullable=False)
    text       = Column(String(300), nullable=False, default="")
    link       = Column(String(500), nullable=False, default="")
    paid       = Column(Numeric(12, 2), nullable=False)
    ends_at    = Column(DateTime(timezone=True), nullable=False)
    is_active  = Column(Boolean, nullable=False, default=True)   # ผู้ดูแลปิดได้
    views      = Column(Integer, nullable=False, default=0)
    clicks     = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LessonQuestion(Base):
    """คำถามท้ายบทเรียน — choice = ปรนัย (answer = ลำดับตัวเลือกที่ถูก เริ่ม 0), text = อัตนัย (answer = คำตอบที่ยอมรับ คั่นด้วย |)"""
    __tablename__ = "lesson_questions"
    id          = Column(Integer, primary_key=True)
    lesson_id   = Column(Integer, ForeignKey("course_lessons.id"), nullable=False, index=True)
    position    = Column(Integer, nullable=False, default=1)
    kind        = Column(String(10), nullable=False)            # choice / text
    prompt      = Column(Text, nullable=False)
    choices     = Column(Text, nullable=False, default="[]")    # JSON list (เฉพาะ choice)
    answer      = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False, default="")


class LessonAnswer(Base):
    """คำตอบล่าสุดของผู้เรียนต่อคำถาม"""
    __tablename__ = "lesson_answers"
    id          = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("lesson_questions.id"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    answer      = Column(Text, nullable=False, default="")
    correct     = Column(Boolean, nullable=False, default=False)
    tries       = Column(Integer, nullable=False, default=0)
