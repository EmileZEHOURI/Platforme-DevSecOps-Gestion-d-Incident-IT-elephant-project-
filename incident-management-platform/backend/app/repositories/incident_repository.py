from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate


class IncidentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, data: IncidentCreate, created_by_id: int) -> Incident:

        incident = Incident(
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            created_by_id=created_by_id,
            status=IncidentStatus.OPEN,
        )
        self.db.add(incident)
        self.db.flush()

        return incident

    def get_all_incident(self) -> list[Incident]:
        statement = select(Incident)

        return self.db.scalars(statement).all()

    def list_by_creator(
        self, *, created_by_id: int,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
        limit: int | None = None, offset: int = 0,
    ) -> list[Incident]:
        statement = select(Incident).where(Incident.created_by_id == created_by_id)
        statement = self._apply_filters(
            statement, status=status, priority=priority, category=category
        ).order_by(Incident.created_at.desc(), Incident.id.desc())
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.scalars(statement.offset(offset)).all())

    def count_by_creator(
        self, *, created_by_id: int,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ) -> int:
        statement = select(Incident).where(Incident.created_by_id == created_by_id)
        statement = self._apply_filters(
            statement, status=status, priority=priority, category=category
        ).with_only_columns(func.count(Incident.id), maintain_column_froms=True)
        return self.db.scalar(statement) or 0

    def get_by_id_and_creator(
        self,
        *,
        incident_id: int,
        created_by_id: int,
    ) -> Incident | None:
        statement = (
            select(Incident)
            .where(Incident.id == incident_id)
            .where(Incident.created_by_id == created_by_id)
        )

        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id(
        self,
        *,
        incident_id: int,
    ) -> Incident | None:
        statement = select(Incident).where(Incident.id == incident_id)

        return self.db.execute(statement).scalar_one_or_none()

    def list_by_assignee(
        self,
        assignee_id: int,
        *,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Incident]:
        statement = select(Incident).where(Incident.assigned_to_id == assignee_id)

        statement = self._apply_filters(
            statement, status=status, priority=priority, category=category
        )

        statement = statement.order_by(Incident.created_at.desc(), Incident.id.desc())

        if limit is not None:
            statement = statement.limit(limit)

        statement = statement.offset(offset)

        return list(self.db.scalars(statement).all())

    def list_all(
        self,
        *,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Incident]:
        statement = select(Incident)

        statement = self._apply_filters(
            statement, status=status, priority=priority, category=category
        )

        statement = statement.order_by(
            Incident.created_at.desc(),
            Incident.id.desc(),
        )

        if limit is not None:
            statement = statement.limit(limit)

        statement = statement.offset(offset)

        return list(self.db.scalars(statement).all())

    def _apply_filters(
        self,
        statement: Select[tuple[Incident]],
        *,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ) -> Select[tuple[Incident]]:

        if status is not None:
            statement = statement.where(Incident.status == status)

        if priority is not None:
            statement = statement.where(Incident.priority == priority)

        if category is not None:
            statement = statement.where(Incident.category == category)

        return statement

    def count_by_assignee(
        self,
        *,
        assignee_id: int,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ) -> int:

        statement = select(Incident).where(Incident.assigned_to_id == assignee_id)

        statement = self._apply_filters(
            statement, status=status, priority=priority, category=category
        )

        statement = statement.with_only_columns(
            func.count(Incident.id),
            maintain_column_froms=True,
        )

        return self.db.scalar(statement) or 0

    def count_all(
        self,
        *,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        category: IncidentCategory | None = None,
    ) -> int:
        statement = select(Incident)

        statement = self._apply_filters(
            statement, status=status, priority=priority, category=category
        )

        statement = statement.with_only_columns(
            func.count(Incident.id),
            maintain_column_froms=True,
        )

        return self.db.scalar(statement) or 0

    def count_active_by_assignee(
        self,
        *,
        assignee_id: int,
    ) -> int:
        statement = (
            select(Incident)
            .where(Incident.assigned_to_id == assignee_id)
            .where(
                Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS])
            )
        )

        statement = statement.with_only_columns(
            func.count(Incident.id),
            maintain_column_froms=True,
        )

        return self.db.scalar(statement) or 0
