"""NRW Games Router — เกม/บันเทิง: บันทึกคะแนน, ตารางอันดับ, รางวัลโทเคน
เกมเล่นในเบราว์เซอร์ (js/modules/games.js) · ได้ 1 โทเคนต่อรอบที่เล่นจบ สูงสุด GAME_DAILY_TOKENS ต่อวัน (ค่าเริ่มต้น 5)"""
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models.community import GameScore
from app.services.helpers import now, names
from app.services.wallet_ops import move_tokens

router = APIRouter()
GAMES = {"memory": 1000, "quickmath": 1000}       # เกม: คะแนนสูงสุดที่เป็นไปได้
DAILY_TOKENS = int(os.getenv("GAME_DAILY_TOKENS", "5"))


class ScoreIn(BaseModel):
    game: str
    score: int = Field(..., ge=0)


@router.post("/score")
def submit(body: ScoreIn, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    if body.game not in GAMES or body.score > GAMES[body.game]:
        raise HTTPException(status_code=400, detail="คะแนนไม่ถูกต้อง")
    start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    played_today = db.query(GameScore).filter(GameScore.user_id == me.id, GameScore.created_at >= start).count()
    db.add(GameScore(user_id=me.id, game=body.game, score=body.score))
    reward = 1 if played_today < DAILY_TOKENS else 0
    if reward:
        move_tokens(db, me.id, reward, "earn", f"รางวัลเกม {body.game}")
    db.commit()
    return {"reward": reward, "left_today": max(0, DAILY_TOKENS - played_today - 1)}


@router.get("/leaderboard")
def leaderboard(game: str = "memory", db: Session = Depends(get_db)):
    rows = (db.query(GameScore.user_id, func.max(GameScore.score).label("best"))
              .filter(GameScore.game == game).group_by(GameScore.user_id)
              .order_by(func.max(GameScore.score).desc()).limit(10).all())
    who = names(db, [r.user_id for r in rows])
    return {"game": game, "top": [{"name": who.get(r.user_id, "—"), "score": r.best} for r in rows]}
