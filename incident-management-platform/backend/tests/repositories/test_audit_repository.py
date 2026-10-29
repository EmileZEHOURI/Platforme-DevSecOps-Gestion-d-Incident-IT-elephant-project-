from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.enums import AuditEventType, AuditResult
from app.repositories.audit_repository import AuditRepository


def test_create_get_audit_log_by_values() -> None:
    db = MagicMock(spec=Session)

    repository = AuditRepository(db)

    audit_log = repository.create(
        event_type=AuditEventType.LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        user_id=1,
        resource_id=42,
        resource_type="incident",
    )

    assert audit_log.user_id == 1
    assert audit_log.resource_id == 42
    assert audit_log.resource_type == "incident"
    assert audit_log.result == "SUCCESS"
    assert audit_log.event_type == "LOGIN_SUCCESS"


def test_create_audit_db_add_flush() -> None:
    db = MagicMock(spec=Session)

    repository = AuditRepository(db)

    audit_log = repository.create(
        event_type=AuditEventType.LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        user_id=1,
        resource_id=42,
        resource_type="incident",
    )

    db.add.assert_called_once_with(audit_log)
    db.flush.assert_called_once()
    db.commit.assert_not_called()
