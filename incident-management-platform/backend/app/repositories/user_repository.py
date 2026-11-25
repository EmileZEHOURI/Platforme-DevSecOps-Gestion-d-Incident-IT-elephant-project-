from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


class UserRepository:
    """Accès aux données des utilisateurs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        """Recherche un utilisateur par sa clé primaire."""

        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Recherche un utilisateur par son adresse électronique."""

        normalized_email = email.strip().lower()

        statement = select(User).where(func.lower(User.email) == normalized_email)

        return self.db.scalar(statement)

    def list_active_technicians(self) -> list[User]:
        statement = (
            select(User)
            .where(
                User.role == UserRole.TECHNICIAN,
                User.is_active.is_(True),
            )
            .order_by(User.full_name.asc())
        )

        return list(self.db.scalars(statement).all())

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Prépare et ajoute un utilisateur à la session."""

        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name.strip(),
            role=role,
            is_active=True,
        )

        self.db.add(user)
        self.db.flush()

        return user

    

    def list_all(
            self,
            *,
            is_active: bool | None = None,
            role: UserRole | None = None,
    ) -> list[User]:

                statement = select(User)
        
                statement = self._apply_filters_user(
                    statement, role=role, is_active= is_active
                )
        
                statement = statement.order_by(
                    User.id.asc(),
                )
        
                return list(self.db.scalars(statement).all())
        
    def _apply_filters_user(
            self,
            statement: Select[tuple[User]],
            *,
            role: UserRole | None = None,
            is_active : bool | None = None,
        ) -> Select[tuple[User]]:
    
            if role is not None:
                statement = statement.where(User.role == role)
    
            if is_active is not None:
                statement = statement.where(User.is_active == is_active)

            return statement

    def update_is_active(
    self,
    *,
    user: User,
    is_active: bool,
) -> User:

        user.is_active = is_active

        self.db.flush()

        return user