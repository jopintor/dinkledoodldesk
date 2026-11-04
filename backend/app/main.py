"""DinkDesk API entrypoint: `uvicorn app.main:app --reload`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.errors import register_error_handlers
from app.llm import get_llm_provider
from app.ratelimit import limiter
from app.routers import auth, services, tickets

settings = get_settings()

app = FastAPI(
    title="DinkDesk API",
    version=__version__,
    description="AI IT helpdesk for PickleHub Clubs (AI-HAS capstone).",
)

app.state.limiter = limiter
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(services.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness check. Reports config state only; it never calls the LLM."""
    provider = get_llm_provider(settings)
    return {
        "status": "ok",
        "version": __version__,
        "env": settings.app_env,
        "llm_provider": provider.name,
        "llm_configured": provider.is_configured(),
    }
