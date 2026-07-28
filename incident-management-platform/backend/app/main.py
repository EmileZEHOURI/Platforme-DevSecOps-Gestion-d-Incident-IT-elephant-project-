from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

app = FastAPI(title="Incident Management API", version="0.1.0")

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
