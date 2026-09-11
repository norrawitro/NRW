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
