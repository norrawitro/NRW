"""
NRW - Norrawit Roopsoong Web
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.routers import iot, shop, admin, game
from app.database import engine, Base
from app.models import User, Product, SensorData, Player  # register all models

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NRW Server",
    description="Norrawit Roopsoong Web — Multi-purpose server",
    version="1.0.0"
)

# Static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(iot.router,   prefix="/iot",   tags=["IoT / ESP32"])
app.include_router(shop.router,  prefix="/shop",  tags=["Shop"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(game.router,  prefix="/game",  tags=["Game"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
