from sqlalchemy import func, select
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
    
    
