"""
Lightweight presence tracking backed by Django's cache.

Deliberately REST/heartbeat-driven rather than websocket-driven, so it
keeps working even while the ws/unread/ connection issue is unresolved.
The frontend calls HeartbeatView every ~30s while the app is open; if a
heartbeat hasn't landed in ONLINE_TTL seconds, the user is considered
offline.
"""

from django.core.cache import cache
from django.utils import timezone

ONLINE_TTL = 90  # seconds


def set_online(user_id):
    cache.set(f"presence:online:{user_id}", True, timeout=ONLINE_TTL)
    cache.set(f"presence:last_seen:{user_id}", timezone.now().isoformat(), timeout=None)


def set_offline(user_id):
    """Optional — called on clean websocket disconnect if/when that's fixed.
    Heartbeat expiry (ONLINE_TTL) handles the common case regardless."""
    cache.delete(f"presence:online:{user_id}")


def is_online(user_id):
    return bool(cache.get(f"presence:online:{user_id}", False))


def get_last_seen(user_id):
    return cache.get(f"presence:last_seen:{user_id}")