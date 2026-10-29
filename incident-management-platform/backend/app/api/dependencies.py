from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.repositories import UserRepository
from app.security import InvalidAccessTokenError, decode_access_token


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
        user_id = decode_access_token(access_token)
        user = user_repository.get_by_id(user_id)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Non authentifié.",
            )

    except InvalidAccessTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié.",
        ) from err

    return user
