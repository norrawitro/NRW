"""
NRW - Norrawit Roopsoong Web
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
import os

from app.routers import iot, shop, admin, game, members, news
from app.database import engine, Base
from app.models import User, Product, SensorData, Player  # register all models

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
env = Environment(loader=FileSystemLoader("app/templates"))

# Include routers
app.include_router(iot.router,   prefix="/iot",   tags=["IoT / ESP32"])
app.include_router(shop.router,  prefix="/shop",  tags=["Shop"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(game.router,    prefix="/game",    tags=["Game"])
app.include_router(members.router, prefix="/members", tags=["Members"])
app.include_router(news.router,    prefix="/news",    tags=["News"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    with open("app/templates/nora-web.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/nora-web", response_class=HTMLResponse)
async def nora_web():
    with open("app/templates/nora-web.html", "r", encoding="utf-8") as f:
        return f.read()
