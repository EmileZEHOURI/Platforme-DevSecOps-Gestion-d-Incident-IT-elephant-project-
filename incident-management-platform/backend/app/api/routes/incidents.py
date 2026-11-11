from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_comment_repository import IncidentCommentRepository
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.incident import (
    IncidentAssignmentUpdate,
    IncidentCreate,
    IncidentResponse,
)
from app.schemas.incident_comment import CommentCreate, CommentResponse
from app.services.incident_comment_service import (
    IncidentClosedError,
    IncidentCommentService,
)
from app.services.incident_service import (
    IncidentNotFoundError,
    IncidentService,
    IncidentStatusClosedError,
    InvalidAssignmentTargetError,
    NotEnoughAuthorization,
    UserInactiveError,
    UserNotFoundError,
)

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
)


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    data: IncidentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IncidentResponse:

    incident_repository = IncidentRepository(db)
    incident_history_repository = IncidentHistoryRepository(db)

    incident_service = IncidentService(
        incident_repository,
        incident_history_repository,
        AuditRepository(db),
        UserRepository(db),
    )

    try:
        incident = incident_service.create_incident(
            data=data, created_by_id=current_user.id
        )
        db.refresh(incident)
        response = IncidentResponse.model_validate(incident)
        db.commit()

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la création de l'incident",
        ) from None

    return response


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[IncidentResponse],
)
def get_incident_list(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[IncidentResponse]:
    incident_repository = IncidentRepository(db)
    incident_history_repository = IncidentHistoryRepository(db)

    incident_service = IncidentService(
        incident_repository,
        incident_history_repository,
        AuditRepository(db),
    )

    result = incident_service.list_user_incidents(created_by_id=current_user.id)

    responses = [IncidentResponse.model_validate(incident) for incident in result]

    return responses


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    response_model=list[IncidentResponse],
)
def get_all_incident(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[IncidentResponse]:
    incident_repository = IncidentRepository(db)
    incident_history_repository = IncidentHistoryRepository(db)

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )

    incident_service = IncidentService(
        incident_repository,
        incident_history_repository,
        AuditRepository(db),
        UserRepository(db)
    )

    result = incident_service.list_all_incidents()

    responses = [IncidentResponse.model_validate(incident) for incident in result]

    return responses


@router.get(
    "/assigned",
    status_code=status.HTTP_200_OK,
    response_model=list[IncidentResponse],
)
def get_assigned_incident_list(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[IncidentResponse]:

    incident_repository = IncidentRepository(db)
    incident_history_repository = IncidentHistoryRepository(db)

    incident_service = IncidentService(
        incident_repository,
        incident_history_repository,
        AuditRepository(db),
    )

    if current_user.role not in (UserRole.ADMIN, UserRole.TECHNICIAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé, vous n'avez pas l'authorisation nécessaire",
        ) from None
    result = incident_service.list_assigned_incidents(assigned_to_id=current_user.id)

    responses = [IncidentResponse.model_validate(incident) for incident in result]

    return responses


@router.get(
    "/{incident_id}",
    status_code=status.HTTP_200_OK,
    response_model=IncidentResponse,
)
def get_incident_detail(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    incident_id: int,
) -> IncidentResponse:
    incident_repository = IncidentRepository(db)
    incident_history_repository = IncidentHistoryRepository(db)

    incident_service = IncidentService(
        incident_repository,
        incident_history_repository,
        AuditRepository(db),
    )

    try:
        result = incident_service.get_incident_detail(
            incident_id=incident_id, created_by_id=current_user.id
        )

        response = IncidentResponse.model_validate(result)

    except IncidentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Échec du chargement des détails de l'incident",
        ) from None

    return response


@router.post(
    "/{incident_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
)
def create_incident_comment(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    data: CommentCreate,
) -> CommentResponse:

    incident_repository = IncidentRepository(db)
    incident_comment_repository = IncidentCommentRepository(db)
    incident_history_repository = IncidentHistoryRepository(db)

    incident_service = IncidentCommentService(
        incident_repository, incident_history_repository, incident_comment_repository
    )

    try:
        added_comment = incident_service.add_comment(
            incident_id=incident_id, author_id=current_user.id, data=data
        )
        db.commit()
        db.refresh(added_comment)

        response = CommentResponse.model_validate(added_comment)

    except IncidentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident inexistant ou inaccessible",
        ) from None

    except IncidentClosedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible d’ajouter un commentaire à un incident fermé",
        ) from None

    return response


@router.patch(
    "/{incident_id}/assignment",
    status_code=status.HTTP_200_OK,
    response_model=IncidentResponse,
)
def assign_incident(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    data: IncidentAssignmentUpdate,
) -> IncidentResponse:

    incident_repository = IncidentRepository(db)
    incident_history_repository = IncidentHistoryRepository(db)
    audit_repository = AuditRepository(db)
    user_repository = UserRepository(db)

    incident_service = IncidentService(
        incident_repository,
        incident_history_repository,
        audit_repository,
        user_repository,
    )

    try:
        updated_incident = incident_service.assign_incident(
            incident_id=incident_id,
            assigned_to_id=data.assigned_to_id,
            actor_id=current_user.id,
        )

        db.commit()
        db.refresh(updated_incident)
        response = IncidentResponse.model_validate(updated_incident)

    except IncidentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident inexistant ou inaccessible",
        ) from None

    except IncidentStatusClosedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible d’assigner un incident fermé",
        ) from None

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur inexistant ou inaccessible",
        ) from None

    except NotEnoughAuthorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé, vous n'avez pas l'authorisation nécessaire",
        ) from None

    except UserInactiveError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible d’assigner un incident à un utiliseur inactif",
        ) from None

    except InvalidAssignmentTargetError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé, vous n'avez pas l'authorisation nécessaire",
        ) from None

    return response
