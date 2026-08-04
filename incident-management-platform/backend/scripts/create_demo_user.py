from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.enums import UserRole
from app.repositories import UserRepository
from app.security import hash_password


email_adapter = TypeAdapter(EmailStr)


def read_email() -> str:
    """Demande une adresse électronique valide."""

    while True:
        raw_email = input("Adresse électronique : ").strip()

        try:
            validated_email = email_adapter.validate_python(raw_email)
        except ValidationError:
            print("L’adresse électronique est invalide.")
            continue

        return str(validated_email).lower()


def read_full_name() -> str:
    """Demande un nom non vide."""

    while True:
        full_name = input("Nom complet : ").strip()

        if full_name:
            return full_name

        print("Le nom complet ne peut pas être vide.")


def read_role() -> UserRole:
    """Demande un rôle valide."""

    available_roles = ", ".join(role.value for role in UserRole)

    while True:
        raw_role = input(
            f"Rôle [{available_roles}] (USER par défaut) : "
        ).strip()

        if not raw_role:
            return UserRole.USER

        try:
            return UserRole(raw_role.upper())
        except ValueError:
            print("Le rôle sélectionné est invalide.")


def read_password() -> str:
    """Demande et confirme le mot de passe."""

    while True:
        password = getpass("Mot de passe : ")

        if len(password) < 8:
            print("Le mot de passe doit contenir au moins 8 caractères.")
            continue

        confirmation = getpass("Confirmer le mot de passe : ")

        if password != confirmation:
            print("Les mots de passe ne correspondent pas.")
            continue

        return password


def main() -> None:
    """Crée un utilisateur local de démonstration."""

    email = read_email()
    full_name = read_full_name()
    role = read_role()
    password = read_password()

    with SessionLocal() as db:
        repository = UserRepository(db)

        if repository.get_by_email(email) is not None:
            print("Un utilisateur possède déjà cette adresse.")
            return

        try:
            user = repository.create(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role=role,
            )

            db.commit()
            db.refresh(user)

        except IntegrityError:
            db.rollback()
            print("La création a été refusée par PostgreSQL.")
            return

        print()
        print("Utilisateur créé avec succès.")
        print(f"Identifiant : {user.id}")
        print(f"Adresse : {user.email}")
        print(f"Nom : {user.full_name}")
        print(f"Rôle : {user.role.value}")


if __name__ == "__main__":
    main()