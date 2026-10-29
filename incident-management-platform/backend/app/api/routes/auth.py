from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.models.enums import AuditEventType, AuditResult
from app.repositories import AuditRepository, UserRepository
from app.schemas import LoginRequest, UserResponse
from app.services import AuthenticationError, AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=UserResponse,
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Authentifie un utilisateur."""

    user_repository = UserRepository(db)
    audit_repository = AuditRepository(db)

    auth_service = AuthService(
        user_repository=user_repository,
        audit_repository=audit_repository,
    )

    ip_address = request.client.host if request.client is not None else None

    user_agent = request.headers.get("user-agent")

    try:
        result = auth_service.authenticate(
            email=str(payload.email),
            password=payload.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    except AuthenticationError:
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse électronique ou mot de passe incorrect.",
        ) from None

    db.commit()

    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )

    return UserResponse.model_validate(result.user)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> UserResponse:
    """Contrôle le cookie de l'utilisateur"""

    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Supprime le cookie de l'utilisateur et le déconnecte"""

    audit_repository = AuditRepository(db)

    ip_address = request.client.host if request.client is not None else None

    user_agent = request.headers.get("user-agent")

    audit_repository.create(
        event_type=AuditEventType.LOGOUT,
        result=AuditResult.SUCCESS,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()

    response.delete_cookie(key="access_token", path="/")

    return {"message": "Déconnexion réussie "}
