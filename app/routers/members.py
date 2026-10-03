"""NRW Members Router — สมัครสมาชิก / login / ดูโปรไฟล์"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jinja2 import Environment, FileSystemLoader

from app.database import get_db
from app.models.user import User
from app.auth import hash_password, verify_password, create_token, get_current_user_from_cookie, require_login

router = APIRouter()
env = Environment(loader=FileSystemLoader("app/templates"))

def _render(template_name: str, **ctx) -> HTMLResponse:
    t = env.get_template(template_name)
    return HTMLResponse(t.render(**ctx))


# ─── Register ────────────────────────────────────────────────────
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = get_current_user_from_cookie(request)
    if user:
        return RedirectResponse("/members/profile", status_code=302)
    return _render("members/register.html", error=None, values={})

@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    username:  str = Form(...),
    email:     str = Form(...),
    phone:     str = Form(""),
    password:  str = Form(...),
    confirm:   str = Form(...),
    db: Session = Depends(get_db)
):
    values = {"full_name": full_name, "username": username,
              "email": email, "phone": phone}

    # Validate
    if len(password) < 8:
        return _render("members/register.html",
                       error="รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร", values=values)
    if password != confirm:
        return _render("members/register.html",
                       error="รหัสผ่านไม่ตรงกัน", values=values)
    if len(username) < 3:
        return _render("members/register.html",
                       error="Username ต้องมีอย่างน้อย 3 ตัวอักษร", values=values)

    user = User(
        full_name = full_name.strip(),
        username  = username.strip().lower(),
        email     = email.strip().lower(),
        phone     = phone.strip() or None,
        hashed_pw = hash_password(password),
    )
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        return _render("members/register.html",
                       error="Username หรือ Email นี้ถูกใช้ไปแล้ว", values=values)

    return _render("members/register_success.html", username=username)


# ─── Login ───────────────────────────────────────────────────────
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user_from_cookie(request)
    if user:
        return RedirectResponse("/members/profile", status_code=302)
    return _render("members/login.html", error=None)

@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.username == username.lower()) | (User.email == username.lower())
    ).first()

    if not user or not verify_password(password, user.hashed_pw):
        return _render("members/login.html", error="Username/Email หรือรหัสผ่านไม่ถูกต้อง")

    if not user.is_active:
        return _render("members/login.html", error="บัญชีนี้ถูกระงับการใช้งาน")

    token = create_token({"sub": str(user.id), "username": user.username,
                          "is_admin": user.is_admin})
    resp = RedirectResponse("/members/profile", status_code=302)
    resp.set_cookie("nrw_token", token, httponly=True, samesite="lax", max_age=86400)
    return resp


# ─── Logout ──────────────────────────────────────────────────────
@router.get("/logout")
async def logout():
    resp = RedirectResponse("/members/login", status_code=302)
    resp.delete_cookie("nrw_token")
    return resp


# ─── Profile ─────────────────────────────────────────────────────
@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    payload = require_login(request)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        return RedirectResponse("/members/logout", status_code=302)
    return _render("members/profile.html", user=user)


# ─── API สำหรับหน้าเว็บ (JSON) ───────────────────────────────────
from pydantic import BaseModel as _BaseModel, Field as _Field
from app.deps import optional_user, current_user
from app.models.post import Post, PostLike, PostComment
from app.services.wallet_ops import get_wallet


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    """ผู้ใช้ที่ login อยู่ (ไม่ได้ login → logged_in: false)"""
    user = optional_user(request, db)
    if not user:
        return {"logged_in": False}
    w = get_wallet(db, user.id)
    db.commit()
    return {"logged_in": True, "id": user.id, "username": user.username, "full_name": user.full_name,
            "initial": (user.full_name or user.username)[:1].upper(), "email": user.email,
            "phone": user.phone, "is_admin": user.is_admin,
            "balance": float(w.balance or 0), "token": int(w.token or 0)}


class ProfileUpdate(_BaseModel):
    full_name: str | None = _Field(None, min_length=1, max_length=100)
    email: str | None = _Field(None, max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str | None = _Field(None, max_length=20)


@router.patch("/me")
def update_me(body: ProfileUpdate, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.email is not None:
        user.email = body.email.strip().lower()
    if body.phone is not None:
        user.phone = body.phone.strip() or None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email นี้ถูกใช้ไปแล้ว")
    return {"full_name": user.full_name, "email": user.email, "phone": user.phone}


class PasswordChange(_BaseModel):
    current: str
    new: str = _Field(..., min_length=8, max_length=200)


@router.post("/me/password")
def change_password(body: PasswordChange, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not verify_password(body.current, user.hashed_pw):
        raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")
    user.hashed_pw = hash_password(body.new)
    db.commit()
    return {"ok": True}


@router.get("/me/posts")
def my_posts(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    posts = (db.query(Post).filter(Post.author_id == user.id, Post.is_deleted == False)
               .order_by(Post.id.desc()).limit(50).all())
    return {"posts": [{"id": p.id, "cat": p.cat, "text": p.text,
                       "likes": db.query(PostLike).filter(PostLike.post_id == p.id).count(),
                       "comments": db.query(PostComment).filter(PostComment.post_id == p.id).count(),
                       "when": p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else "—"} for p in posts]}
