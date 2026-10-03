"""
NRW - Norrawit Roopsoong Web
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
import os

from app.routers import iot, shop, admin, game, members, news, wallet, cloud, ai
from app.routers import manage, logistics, market, token, analytics
from app.routers import chat, course, jobs, workspace, ads, video, games, events, creator, iot_devices, health
from app.database import engine, Base
from app.models import User, Product, SensorData, Player  # register all models
from app.models.wallet import Wallet, WalletTransaction   # register wallet models
from app.models.cloud import CloudFolder, CloudFile       # register cloud models
import app.models  # noqa: F401 — register all models (shop, market, ...)

# Create all tables on startup
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"⚠️  Database init skipped: {e}")

app = FastAPI(
    title="NRW Server",
    description="Norrawit Roopsoong Web — Multi-purpose server",
    version="1.0.0"
)

# Static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    """ให้เบราว์เซอร์เช็คไฟล์ CSS/JS ใหม่ทุกครั้ง — แก้ไฟล์แล้วกด refresh เห็นผลทันที"""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
env = Environment(loader=FileSystemLoader("app/templates"))

# Include routers
app.include_router(iot.router,   prefix="/iot",   tags=["IoT / ESP32"])
app.include_router(shop.router,  prefix="/shop",  tags=["Shop"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(game.router,    prefix="/game",    tags=["Game"])
app.include_router(members.router, prefix="/members", tags=["Members"])
app.include_router(news.router,    prefix="/news",    tags=["News"])
app.include_router(wallet.router,  prefix="/wallet",  tags=["Wallet"])
app.include_router(cloud.router,   prefix="/cloud",   tags=["Cloud"])
app.include_router(ai.router,      prefix="/ai",      tags=["AI"])
app.include_router(manage.router,    prefix="/manage",    tags=["Manage (admin web)"])
app.include_router(logistics.router, prefix="/logistics", tags=["Logistics"])
app.include_router(market.router,    prefix="/market",    tags=["Market"])
app.include_router(token.router,     prefix="/token",     tags=["Token"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
# ช่วงที่ 3
app.include_router(chat.router,      prefix="/chat",      tags=["Chat"])
app.include_router(course.router,    prefix="/course",    tags=["Course"])
app.include_router(jobs.router,      prefix="/jobs",      tags=["Jobs"])
app.include_router(workspace.router, prefix="/workspace", tags=["Workspace"])
app.include_router(ads.router,       prefix="/ads",       tags=["Ads"])
# ช่วงที่ 4
app.include_router(video.router,       prefix="/video",   tags=["Video"])
app.include_router(games.router,       prefix="/games",   tags=["Games"])
app.include_router(events.router,      prefix="/events",  tags=["Events"])
app.include_router(creator.router,     prefix="/creator", tags=["Creator"])
app.include_router(iot_devices.router, prefix="/iot",     tags=["IoT / ESP32"])
app.include_router(health.router,      prefix="/health",  tags=["Health"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    with open("app/templates/nora-web.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/nora-web", response_class=HTMLResponse)
async def nora_web():
    with open("app/templates/nora-web.html", "r", encoding="utf-8") as f:
        return f.read()
