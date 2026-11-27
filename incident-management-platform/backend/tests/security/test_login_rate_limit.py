
import fakeredis
import pytest

from app.security import login_rate_limit


@pytest.fixture
def fake_redis(monkeypatch):
    client = fakeredis.FakeRedis()

    monkeypatch.setattr(
        login_rate_limit,
        "get_redis_client",
        lambda: client,
    )

    return client


def test_login_allowed_below_limits(fake_redis):
    result = login_rate_limit.check_login_rate_limit(
        ip_address="192.0.2.10",
        email="user@example.com",
    )

    assert result == 0


def test_ip_limit(fake_redis):
    for index in range(login_rate_limit.IP_LIMIT):
        result = login_rate_limit.check_login_rate_limit(
            ip_address="192.0.2.11",
            email=f"user{index}@example.com",
        )
        assert result == 0

    retry = login_rate_limit.check_login_rate_limit(
        ip_address="192.0.2.11",
        email="another@example.com",
    )

    assert retry > 0


def test_account_limit_across_multiple_ips(fake_redis):
    for index in range(login_rate_limit.ACCOUNT_LIMIT):
        result = login_rate_limit.check_login_rate_limit(
            ip_address=f"192.0.2.{index + 20}",
            email="victim@example.com",
        )
        assert result == 0

    retry = login_rate_limit.check_login_rate_limit(
        ip_address="192.0.2.100",
        email="victim@example.com",
    )

    assert retry > 0


def test_email_normalization(fake_redis):
    for index in range(login_rate_limit.ACCOUNT_LIMIT):
        result = login_rate_limit.check_login_rate_limit(
            ip_address=f"198.51.100.{index + 1}",
            email="  USER@EXAMPLE.COM  ",
        )
        assert result == 0

    retry = login_rate_limit.check_login_rate_limit(
        ip_address="198.51.100.100",
        email="user@example.com",
    )

    assert retry > 0


def test_keys_do_not_expose_email(fake_redis):
    login_rate_limit.check_login_rate_limit(
        ip_address="203.0.113.10",
        email="private@example.com",
    )

    keys = list(fake_redis.scan_iter("rate:login:*"))

    assert keys
    assert all(b"private@example.com" not in key for key in keys)
    assert all(fake_redis.ttl(key) > 0 for key in keys)
