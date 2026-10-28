from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
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
    db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    """Authentifie un utilisateur."""

    user_repository = UserRepository(db)
    audit_repository = AuditRepository(db)

    auth_service = AuthService(
        user_repository=user_repository,
        audit_repository=audit_repository,
    )

    ip_address = (
        request.client.host
        if request.client is not None
        else None
    )

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