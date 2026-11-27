from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.enums import AuditEventType, AuditResult
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.audit import PaginatedAuditLogsResponse
from app.services.audit_service import AuditService, InvalidAuditDateRangeError
from app.services.incident_service import (
    PaginationError,
)
from app.services.user_service import (
    NotEnoughAuthorization,
    UserNotFoundError,
)

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedAuditLogsResponse,
)
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: int | None = None,
    event_type: AuditEventType | None = None,
    result: AuditResult | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> PaginatedAuditLogsResponse:
    user_repository = UserRepository(db)

    audit_repository = AuditRepository(db)

    audit_service = AuditService(
        user_repository=user_repository,
        audit_repository=audit_repository,
    )

    try:
        audit_logs = audit_service.paginate_audit_logs(
            actor_id=current_user.id,
            page=page,
            page_size=page_size,
            user_id=user_id,
            event_type=event_type,
            result=result,
            date_to=date_to,
            date_from=date_from,
        )

        return PaginatedAuditLogsResponse.model_validate(audit_logs)

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

    except PaginationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None

    except InvalidAuditDateRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des journaux d'audit",
        ) from None
