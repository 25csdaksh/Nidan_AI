from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_v1_router
from app.core.config import settings
from app.core.database import init_db
from app.core.errors import register_error_handlers
from app.core.logging import logger
from app.core.middleware import CDSSDisclaimerMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown routines."""
    logger.info("Initializing %s services...", settings.PROJECT_NAME)
    await init_db()
    logger.info("%s backend started successfully. CDSS Guardrails Active.", settings.PROJECT_NAME)
    yield
    logger.info("Shutting down %s services...", settings.PROJECT_NAME)


app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    description=(
        f"**{settings.PROJECT_TAGLINE}**\n\n"
        "Production-oriented clinical decision-support platform (Phase 0 Foundation).\n\n"
        "> ⚠️ **IMPORTANT CLINICAL NOTICE**:\n"
        "> NIDAN AI is NOT a doctor replacement. It must never independently provide "
        "> a definitive medical diagnosis, prescription, or treatment decision. All insights "
        "> require human-in-the-loop clinician review."
    ),
    version="0.1.0-phase0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 1. CDSS Disclaimer & Request Correlation Middleware
app.add_middleware(CDSSDisclaimerMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CDSS-Disclaimer", "X-CDSS-Confidence-Policy", "X-Request-ID", "X-Response-Time-MS"],
)

# 3. Global Exception Handlers
register_error_handlers(app)

# 4. Register V1 API Routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root_info():
    return JSONResponse(
        content={
            "platform": settings.PROJECT_NAME,
            "tagline": settings.PROJECT_TAGLINE,
            "phase": "Phase 0 (Production Foundation)",
            "api_v1": f"{settings.API_V1_STR}/health",
            "docs": "/docs",
            "disclaimer": settings.CDSS_DISCLAIMER,
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
