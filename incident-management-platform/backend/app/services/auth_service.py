from dataclasses import dataclass

from app.models.enums import AuditEventType, AuditResult
from app.models.user import User
from app.repositories import AuditRepository, UserRepository
from app.security import create_access_token, verify_password


class AuthenticationError(Exception):
    """Authentification refusée."""


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """Résultat d'une authentification réussie."""

    user: User
    access_token: str


class AuthService:
    """Applique les règles métier liées à l'authentification."""

    def __init__(
        self,
        user_repository: UserRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self.user_repository = user_repository
        self.audit_repository = audit_repository

    def authenticate(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticationResult:
        """Authentifie un utilisateur et génère son jeton."""

        user = self.user_repository.get_by_email(email)

        if user is None:
            self.audit_repository.create(
                event_type=AuditEventType.LOGIN_FAILURE,
                result=AuditResult.FAILURE,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "reason": "invalid_credentials",
                },
            )

            raise AuthenticationError

        password_is_valid = verify_password(
            password,
            user.password_hash,
        )

        if not password_is_valid:
            self.audit_repository.create(
                user_id=user.id,
                event_type=AuditEventType.LOGIN_FAILURE,
                result=AuditResult.FAILURE,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "reason": "invalid_credentials",
                },
            )

            raise AuthenticationError

        if not user.is_active:
            self.audit_repository.create(
                user_id=user.id,
                event_type=AuditEventType.LOGIN_FAILURE,
                result=AuditResult.FAILURE,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "reason": "inactive_account",
                },
            )

            raise AuthenticationError

        access_token = create_access_token(user.id)

        if not access_token:
            self.audit_repository.create(
                user_id=user.id,
                event_type=AuditEventType.LOGOUT,
                result=AuditResult.SUCCESS,
                details={"reason": "logout_account"},
            )

        self.audit_repository.create(
            user_id=user.id,
            event_type=AuditEventType.LOGIN_SUCCESS,
            result=AuditResult.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return AuthenticationResult(
            user=user,
            access_token=access_token,
        )
