from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.incident_history_repository import IncidentHistoryRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.services.incident_service import IncidentService

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
