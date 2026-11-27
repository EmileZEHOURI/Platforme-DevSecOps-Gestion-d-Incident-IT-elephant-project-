from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.audit_logs import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.database import get_db

app = FastAPI(title="Incident Management API", version="0.1.0")
app.include_router(auth_router)
app.include_router(incidents_router)
app.include_router(users_router)
app.include_router(audit_router)

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def get_request_origin(request: Request) -> str | None:
    origin = request.headers.get("origin")

    if origin is not None:
        return origin

    referer = request.headers.get("referer")

    if not referer:
        return None

    parsed = urlsplit(referer)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
    ):
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


@app.middleware("http")
async def protect_against_csrf(request: Request, call_next):
    if (
    request.method in UNSAFE_METHODS
    and (
        settings.environment == "production"
        or settings.csrf_protection_enabled
    )
):
        origin = get_request_origin(request)

        if (
            not settings.frontend_origin
            or origin != settings.frontend_origin
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Origine de la requête non autorisée."
                },
            )

    return await call_next(request)



@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Verifie que l'API est disponible.
    """
    return {"status": "ok"}


@app.get("/health/database", tags=["Health"])
def database_health_check(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Vérifie que PostgreSQL est accessible."""

    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }
