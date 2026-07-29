from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import get_settings
from app.api.limiter import limiter
from app.api.routes import (
    articles, search, chat, trends, companies, graph,
    newsletter, recommendations, internal, health,
)
from app.scheduler import start_scheduler, shutdown_scheduler

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-agent AI News Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
# Internal routes first (exempt from rate limiting)
app.include_router(internal.router)
# Health check route
app.include_router(health.router)
# Public routes (rate-limited)
app.include_router(articles.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(trends.router)
app.include_router(companies.router)
app.include_router(graph.router)
app.include_router(newsletter.router)
app.include_router(recommendations.router)

@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} API is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}