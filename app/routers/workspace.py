"""NRW Workspace Router — พื้นที่ทำงานร่วมกัน: สร้างพื้นที่, เชิญสมาชิก, บอร์ดงาน (todo/doing/done), โน้ตร่วม"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.user import User
from app.models.work import Workspace, WorkspaceMember, WorkspaceTask
from app.services.helpers import names

router = APIRouter()


def _member_ws(db, ws_id, user_id) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    if not ws or not db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws_id,
                                                     WorkspaceMember.user_id == user_id).first():
        raise HTTPException(status_code=404, detail="ไม่พบพื้นที่ทำงาน")
    return ws


@router.get("")
def my_workspaces(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ids = [m.workspace_id for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == me.id).all()]
    wss = db.query(Workspace).filter(Workspace.id.in_(ids)).order_by(Workspace.id.desc()).all() if ids else []
    return {"workspaces": [{"id": w.id, "name": w.name, "is_owner": w.owner_id == me.id} for w in wss]}


class WsIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


@router.post("")
def create(body: WsIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ws = Workspace(owner_id=me.id, name=body.name.strip())
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=me.id))
    db.commit()
    return {"id": ws.id}


@router.get("/{ws_id}")
def detail(ws_id: int, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ws = _member_ws(db, ws_id, me.id)
    member_ids = [m.user_id for m in db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).all()]
    tasks = db.query(WorkspaceTask).filter(WorkspaceTask.workspace_id == ws.id).order_by(WorkspaceTask.id).all()
    who = names(db, member_ids + [t.assignee_id for t in tasks])
    return {"id": ws.id, "name": ws.name, "notes": ws.notes, "is_owner": ws.owner_id == me.id,
            "members": [{"id": i, "name": who.get(i, "—")} for i in member_ids],
            "tasks": [{"id": t.id, "title": t.title, "status": t.status, "assignee_id": t.assignee_id,
                       "assignee": who.get(t.assignee_id)} for t in tasks]}


class Invite(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


@router.post("/{ws_id}/members")
def invite(ws_id: int, body: Invite, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ws = _member_ws(db, ws_id, me.id)
    if ws.owner_id != me.id:
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของพื้นที่")
    u = db.query(User).filter(User.username == body.username.strip().lower(), User.is_active == True).first()
    if not u:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
    if not db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == u.id).first():
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=u.id))
        db.commit()
    return {"ok": True}


class TaskIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    assignee_id: int | None = None


@router.post("/{ws_id}/tasks")
def add_task(ws_id: int, body: TaskIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ws = _member_ws(db, ws_id, me.id)
    db.add(WorkspaceTask(workspace_id=ws.id, title=body.title.strip(), assignee_id=body.assignee_id))
    db.commit()
    return {"ok": True}


class TaskMove(BaseModel):
    status: str = Field(..., pattern="^(todo|doing|done|delete)$")


@router.post("/{ws_id}/tasks/{task_id}")
def move_task(ws_id: int, task_id: int, body: TaskMove, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ws = _member_ws(db, ws_id, me.id)
    t = db.query(WorkspaceTask).filter(WorkspaceTask.id == task_id, WorkspaceTask.workspace_id == ws.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="ไม่พบงาน")
    if body.status == "delete":
        db.delete(t)
    else:
        t.status = body.status
    db.commit()
    return {"ok": True}


class Notes(BaseModel):
    notes: str = Field("", max_length=50000)


@router.put("/{ws_id}/notes")
def save_notes(ws_id: int, body: Notes, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    ws = _member_ws(db, ws_id, me.id)
    ws.notes = body.notes
    db.commit()
    return {"ok": True}
