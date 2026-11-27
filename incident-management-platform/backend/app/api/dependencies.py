from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories import UserRepository
from app.security import InvalidAccessTokenError
from app.security.token import decode_access_token_claims
from app.security.token_revocation import RevocationUnavailableError, is_revoked


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:

    user_repository = UserRepository(db)

    access_token = request.cookies.get("access_token")

    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié."
        )

    try:
        claims = decode_access_token_claims(access_token)
        if settings.jwt_revocation_required:
            if claims.jti is None or is_revoked(db, claims.jti):
                raise InvalidAccessTokenError
        request.state.access_token_claims = claims
        user = user_repository.get_by_id(claims.user_id)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Non authentifié.",
            )

    except RevocationUnavailableError as err:
        raise HTTPException(
            status_code=503, detail="Service temporairement indisponible."
        ) from err
    except InvalidAccessTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié.",
        ) from err

    return user
