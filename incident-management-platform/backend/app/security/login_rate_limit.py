
import hashlib
import hmac
from functools import lru_cache

from redis import Redis

from app.core.config import settings


IP_LIMIT = 20
IP_WINDOW = 300

ACCOUNT_LIMIT = 10
ACCOUNT_WINDOW = 900


# Lecture, vérification et incrémentation atomiques.
# Deux processus FastAPI ne peuvent pas dépasser
# simultanément les limites en lisant l'ancien compteur.
RATE_LIMIT_SCRIPT = """
local ip_count = tonumber(redis.call('GET', KEYS[1]) or '0')
local account_count = tonumber(redis.call('GET', KEYS[2]) or '0')

local ip_limit = tonumber(ARGV[1])
local account_limit = tonumber(ARGV[2])

if ip_count >= ip_limit or account_count >= account_limit then
    local retry = 1

    if ip_count >= ip_limit then
        retry = math.max(retry, redis.call('TTL', KEYS[1]))
    end

    if account_count >= account_limit then
        retry = math.max(retry, redis.call('TTL', KEYS[2]))
    end

    return {0, retry}
end

if redis.call('INCR', KEYS[1]) == 1 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
end

if redis.call('INCR', KEYS[2]) == 1 then
    redis.call('EXPIRE', KEYS[2], tonumber(ARGV[4]))
end

return {1, 0}
"""


@lru_cache
def get_redis_client() -> Redis:
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL manquant.")

    return Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def make_key(kind: str, value: str) -> str:
    """Évite de stocker l'email ou l'IP en clair dans la clé."""

    content = f"login-rate:{kind}:{value}".encode("utf-8")

    digest = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        content,
        hashlib.sha256,
    ).hexdigest()

    return f"rate:login:{kind}:{digest}"


def check_login_rate_limit(
    ip_address: str,
    email: str,
) -> int:
    """Retourne 0 si autorisé, sinon Retry-After en secondes."""

    ip_key = make_key("ip", ip_address)

    account_key = make_key(
        "account",
        email.strip().lower(),
    )

    result = get_redis_client().eval(
        RATE_LIMIT_SCRIPT,
        2,
        ip_key,
        account_key,
        IP_LIMIT,
        ACCOUNT_LIMIT,
        IP_WINDOW,
        ACCOUNT_WINDOW,
    )

    allowed, retry_after = result

    if int(allowed) == 1:
        return 0

    return max(1, int(retry_after))
