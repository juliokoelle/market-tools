"""Shared Redis helpers: connection, cross-service log sink, and heartbeats.

The Coolify deployment runs each app (backend, telegram-bot, cache-warmer) in
a separate container that shares one Redis instance (see
docker-compose.coolify.yml). Redis is therefore the only place state can be
shared across containers and survive redeploys.

Every function degrades gracefully: if REDIS_URL is unset or Redis is
unreachable, callers get None/empty results and never an exception.
"""

from __future__ import annotations

import json
import logging
import os
import time
from logging import Handler, LogRecord

log = logging.getLogger(__name__)

# None = not yet tried, False = unavailable, else a live client.
_client: object | None = None


def get_redis():
    """Return a live Redis client, or None if unavailable. Cached after first call."""
    global _client
    if _client is not None:
        return _client or None
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        _client = False
        return None
    try:
        import redis

        c = redis.from_url(
            url, socket_timeout=2, socket_connect_timeout=2, decode_responses=True
        )
        c.ping()
        _client = c
        log.info("Redis connected (redis_state)")
        return c
    except Exception as e:  # noqa: BLE001 — degrade to no-Redis mode
        log.warning("Redis unavailable (%s) — running without shared state", e)
        _client = False
        return None


def _reset_for_tests() -> None:
    """Clear the cached client so tests can re-evaluate REDIS_URL."""
    global _client
    _client = None


# ---------------------------------------------------------------------------
# Cross-service log sink — so /health sees errors from other containers
# ---------------------------------------------------------------------------

_LOG_KEY = "mt:logs:{service}"
_LOG_MAX = 500            # keep the most recent N records per service
_LOG_TTL = 7 * 86400      # expire after 7 days of inactivity


class RedisLogHandler(Handler):
    """Logging handler that pushes WARNING+ records into a capped Redis list.

    Lets /health surface errors/warnings across separate Coolify containers.
    Never raises — logging must not break the app.
    """

    def __init__(self, service: str, level: int = logging.WARNING):
        super().__init__(level)
        self.service = service
        self._key = _LOG_KEY.format(service=service)

    def emit(self, record: LogRecord) -> None:
        r = get_redis()
        if r is None:
            return
        try:
            payload = json.dumps(
                {"ts": record.created, "level": record.levelname, "msg": self.format(record)}
            )
            pipe = r.pipeline()
            pipe.lpush(self._key, payload)
            pipe.ltrim(self._key, 0, _LOG_MAX - 1)
            pipe.expire(self._key, _LOG_TTL)
            pipe.execute()
        except Exception:  # noqa: BLE001
            pass


def install_redis_log_handler(service: str) -> None:
    """Attach a RedisLogHandler to the root logger once."""
    root = logging.getLogger()
    if any(isinstance(h, RedisLogHandler) for h in root.handlers):
        return
    h = RedisLogHandler(service)
    h.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    root.addHandler(h)


def read_recent_logs(service: str, hours: float) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) message strings from the last `hours`, oldest first."""
    r = get_redis()
    if r is None:
        return [], []
    cutoff = time.time() - hours * 3600
    errors: list[str] = []
    warnings: list[str] = []
    try:
        for raw in r.lrange(_LOG_KEY.format(service=service), 0, -1):
            d = json.loads(raw)
            if d.get("ts", 0) < cutoff:
                continue
            msg = (d.get("msg") or "")[:160]
            level = d.get("level")
            if level in ("ERROR", "CRITICAL"):
                errors.append(msg)
            elif level == "WARNING":
                warnings.append(msg)
    except Exception:  # noqa: BLE001
        return [], []
    errors.reverse()    # lpush stores newest-first; present chronologically
    warnings.reverse()
    return errors, warnings


# ---------------------------------------------------------------------------
# Heartbeats — genuine liveness signal per service
# ---------------------------------------------------------------------------

_HB_KEY = "mt:hb:{service}"
_HB_TTL = 86400


def heartbeat(service: str) -> None:
    """Record that `service` is alive right now."""
    r = get_redis()
    if r is None:
        return
    try:
        r.set(_HB_KEY.format(service=service), time.time(), ex=_HB_TTL)
    except Exception:  # noqa: BLE001
        pass


def last_heartbeat(service: str) -> float | None:
    """Return the unix timestamp of the last heartbeat, or None."""
    r = get_redis()
    if r is None:
        return None
    try:
        v = r.get(_HB_KEY.format(service=service))
        return float(v) if v is not None else None
    except Exception:  # noqa: BLE001
        return None
