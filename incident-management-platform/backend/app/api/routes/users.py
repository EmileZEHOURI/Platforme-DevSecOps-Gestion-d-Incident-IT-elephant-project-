from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserActivationUpdate, UserResponse
from app.services.user_service import (
    DesactivateAdminError,
    NotEmptyListIncident,
    NotEnoughAuthorization,
    UserNotFoundError,
    UserService,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.patch(
    "/{user_id}/activation",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
)
def update_user_activation(
    user_id: int,
    data: UserActivationUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:

    incident_repository = IncidentRepository(db)
    user_repository = UserRepository(db)
    audit_repository = AuditRepository(db)

    user_service = UserService(
        user_repository=user_repository,
        incident_repository=incident_repository,
        audit_repository=audit_repository,
    )

    try:
        result = user_service.user_activation(
            actor_id=current_user.id,
            target_id=user_id,
            is_active=data.is_active,
        )

        responses = UserResponse.model_validate(result)

        db.commit()

        return responses

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur inexistant ou inaccessible",
        ) from None

    except DesactivateAdminError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de désactiver un administrateur",
        ) from None

    except NotEnoughAuthorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé, vous n'avez pas l'autorisation nécessaire",
        ) from None

    except NotEmptyListIncident:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Liste non vide, impossibilité de désactivation",
        ) from None

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la modification du compte utilisateur",
        ) from None


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[UserResponse],
)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> list[UserResponse]:

    user_repository = UserRepository(db)
    incident_repository = IncidentRepository(db)

    audit_repository = AuditRepository(db)

    user_service = UserService(
        user_repository=user_repository,
        incident_repository=incident_repository,
        audit_repository=audit_repository,
    )

    try:
        users = user_service.list_users(
            actor_id=current_user.id,
            role=role,
            is_active=is_active,
        )

        return [UserResponse.model_validate(user) for user in users]

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur inexistant",
        ) from None

    except NotEnoughAuthorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        ) from None

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des utilisateurs",
        ) from None
