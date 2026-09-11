"""NRW News Router — POST /news/posts, GET, like, comment"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user_from_cookie
from app.models.user import User
from app.models.post import Post, PostLike, PostComment
from pydantic import BaseModel

router = APIRouter()

VALID_CATS = {"announce", "update", "event"}

# ─── Schemas ────────────────────────────────────────────────
class PostCreate(BaseModel):
    text: str
    cat: str = "announce"

class CommentCreate(BaseModel):
    text: str

# ─── Helpers ────────────────────────────────────────────────
def _require_user(request: Request, db: Session):
    payload = get_current_user_from_cookie(request)
    if not payload:
        raise HTTPException(status_code=401, detail="กรุณา login ก่อน")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้")
    return user

def _post_dict(post: Post, db: Session, current_user_id: int | None = None):
    author = db.query(User).filter(User.id == post.author_id).first()
    likes  = db.query(PostLike).filter(PostLike.post_id == post.id).count()
    liked  = False
    if current_user_id:
        liked = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user_id
        ).first() is not None
    comments = db.query(PostComment).filter(PostComment.post_id == post.id).count()
    return {
        "id":         post.id,
        "cat":        post.cat,
        "author":     author.full_name if author else "ไม่ระบุ",
        "author_id":  post.author_id,
        "text":       post.text,
        "is_pinned":  post.is_pinned,
        "likes":      likes,
        "liked":      liked,
        "comments":   comments,
        "when":       post.created_at.strftime("%d/%m/%Y %H:%M") if post.created_at else "—",
        "created_at": str(post.created_at),
    }

# ─── GET /news/posts ─────────────────────────────────────────
@router.get("/posts")
async def get_posts(
    request: Request,
    cat: str = "all",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    payload = get_current_user_from_cookie(request)
    uid = int(payload["sub"]) if payload else None

    q = db.query(Post).filter(Post.is_deleted == False)
    if cat and cat != "all":
        q = q.filter(Post.cat == cat)
    posts = q.order_by(Post.is_pinned.desc(), Post.created_at.desc()).limit(limit).all()
    return {"posts": [_post_dict(p, db, uid) for p in posts]}

# ─── POST /news/posts ────────────────────────────────────────
@router.post("/posts")
async def create_post(
    body: PostCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _require_user(request, db)
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="ข้อความว่าง")
    if body.cat not in VALID_CATS:
        raise HTTPException(status_code=400, detail="หมวดไม่ถูกต้อง")

    post = Post(author_id=user.id, cat=body.cat, text=body.text.strip())
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_dict(post, db, user.id)

# ─── POST /news/posts/{id}/like ──────────────────────────────
@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _require_user(request, db)
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="ไม่พบโพสต์")

    existing = db.query(PostLike).filter(
        PostLike.post_id == post_id, PostLike.user_id == user.id
    ).first()
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(PostLike(post_id=post_id, user_id=user.id))
        liked = True
    db.commit()
    likes = db.query(PostLike).filter(PostLike.post_id == post_id).count()
    return {"liked": liked, "likes": likes}

# ─── GET /news/posts/{id}/comments ──────────────────────────
@router.get("/posts/{post_id}/comments")
async def get_comments(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    payload = get_current_user_from_cookie(request)
    uid = int(payload["sub"]) if payload else None
    comments = db.query(PostComment).filter(
        PostComment.post_id == post_id
    ).order_by(PostComment.created_at.asc()).all()
    result = []
    for c in comments:
        author = db.query(User).filter(User.id == c.author_id).first()
        result.append({
            "id":      c.id,
            "text":    c.text,
            "author":  author.full_name if author else "ไม่ระบุ",
            "is_mine": c.author_id == uid,
            "when":    c.created_at.strftime("%d/%m/%Y %H:%M") if c.created_at else "—",
        })
    return {"comments": result}

# ─── POST /news/posts/{id}/comments ─────────────────────────
@router.post("/posts/{post_id}/comments")
async def add_comment(
    post_id: int,
    body: CommentCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _require_user(request, db)
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="ความเห็นว่าง")
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="ไม่พบโพสต์")
    c = PostComment(post_id=post_id, author_id=user.id, text=body.text.strip())
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "text": c.text, "author": user.full_name,
            "is_mine": True, "when": "เมื่อสักครู่"}

# ─── DELETE /news/posts/{id} ─────────────────────────────────
@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _require_user(request, db)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="ไม่พบโพสต์")
    if post.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ลบโพสต์นี้")
    post.is_deleted = True
    db.commit()
    return {"deleted": post_id}
