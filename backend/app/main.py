from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import articles, search, chat, trends

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-agent AI News Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(trends.router)

@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
