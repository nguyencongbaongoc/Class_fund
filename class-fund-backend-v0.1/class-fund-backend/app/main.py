from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, campaigns, chat, fund, health, uploads, messages, vision, review
from app.api.routes import ai_internal, public, admin, realtime
from app.core.config import get_settings
from app.db.init_db import init_db
from app.services.realtime import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    # Initialize realtime manager
    await manager.initialize()
    # Local/dev convenience. Production should use Alembic migrations only.
    if settings.environment != "production":
        init_db()
    yield
    # Cleanup
    await manager.close()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = "/api/v1"
app.include_router(health.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)
app.include_router(public.router, prefix=prefix)
app.include_router(fund.router, prefix=prefix)
app.include_router(uploads.router, prefix=prefix)
app.include_router(ai_internal.router, prefix=prefix)
app.include_router(campaigns.router, prefix=prefix)
app.include_router(chat.router, prefix=prefix)
app.include_router(messages.router, prefix=prefix)
app.include_router(vision.router, prefix=prefix)
app.include_router(review.router, prefix=prefix)
app.include_router(admin.router, prefix=prefix)

# WebSocket routes (no prefix, they use /ws/)
app.include_router(realtime.router)
