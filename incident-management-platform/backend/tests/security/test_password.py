import pytest

from app.security import hash_password, verify_password


def test_hash_password_does_not_return_plain_password() -> None:
    plain_password = "StrongPassword123!"

    hashed_password = hash_password(plain_password)

    assert hashed_password != plain_password
    assert len(hashed_password) > len(plain_password)


def test_verify_password_accepts_correct_password() -> None:
    plain_password = "StrongPassword123!"
    hashed_password = hash_password(plain_password)

    assert verify_password(plain_password, hashed_password) is True


def test_verify_password_rejects_incorrect_password() -> None:
    hashed_password = hash_password("StrongPassword123!")

    assert verify_password("WrongPassword", hashed_password) is False


def test_same_password_generates_different_hashes() -> None:
    plain_password = "StrongPassword123!"

    first_hash = hash_password(plain_password)
    second_hash = hash_password(plain_password)

    assert first_hash != second_hash
    assert verify_password(plain_password, first_hash) is True
    assert verify_password(plain_password, second_hash) is True


def test_hash_password_rejects_empty_password() -> None:
    with pytest.raises(
        ValueError,
        match="Le mot de passe ne peut pas être vide",
    ):
        hash_password("")


def test_verify_password_rejects_empty_values() -> None:
    assert verify_password("", "stored-hash") is False
    assert verify_password("password", "") is False
