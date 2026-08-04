from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Transforme un mot de passe brut en hash sécurisé."""

    if password == "":
        raise ValueError("Le mot de passe ne peut pas être vide.")

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Vérifie qu'un mot de passe correspond au hash enregistré."""

    if plain_password == "" or hashed_password == "":
        return False

    return password_hasher.verify(
        plain_password,
        hashed_password,
    )
