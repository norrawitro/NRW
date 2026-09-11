"""NRW Authentication — password hashing + JWT token"""
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import os

# ─── Password hashing ───────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── JWT ────────────────────────────────────────────────────────
SECRET_KEY  = os.getenv("SECRET_KEY", "change-me-in-env")
ALGORITHM   = "HS256"
TOKEN_EXPIRE_HOURS = 24

def create_token(data: dict, expires_hours: int = TOKEN_EXPIRE_HOURS) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=expires_hours)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token ไม่ถูกต้องหรือหมดอายุ")

# ─── Session cookie helper ───────────────────────────────────────
def get_current_user_from_cookie(request: Request) -> dict | None:
    token = request.cookies.get("nrw_token")
    if not token:
        return None
    try:
        return decode_token(token)
    except Exception:
        return None

def require_login(request: Request) -> dict:
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
    return user

def require_admin(request: Request) -> dict:
    user = require_login(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="เฉพาะ Admin เท่านั้น")
    return user

# ─── Admin Basic Auth (เดิม — ใช้กับ /admin API) ───────────────
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("ADMIN_USERNAME", "admin")
    correct_password = os.getenv("ADMIN_PASSWORD", "")
    if not correct_password:
        raise HTTPException(status_code=500, detail="ADMIN_PASSWORD not configured")
    ok_user = secrets.compare_digest(credentials.username.encode(), correct_username.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), correct_password.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, detail="Invalid credentials",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username

def verify_iot_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    correct_api_key = os.getenv("IOT_API_KEY", "")
    if not correct_api_key:
        raise HTTPException(status_code=500, detail="IOT_API_KEY not configured")
    if not secrets.compare_digest(x_api_key, correct_api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True
