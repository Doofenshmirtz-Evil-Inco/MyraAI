import json
import os
import time

import redis


class SessionManager:
    def __init__(self):
        self._fallback_store = {}
        self.use_redis = False
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            self.client.ping()
            self.use_redis = True
            print("[SessionManager] Connected to Redis.", flush=True)
        except Exception as error:
            self.client = None
            print(f"[SessionManager] Redis unavailable ({error}); using local TTL fallback.", flush=True)

    def set_pending(self, session_id: str, payload: dict, ttl: int = 300):
        data = json.dumps(payload)
        if self.use_redis:
            self.client.setex(f"session:{session_id}", ttl, data)
        else:
            self._fallback_store[session_id] = (time.monotonic() + ttl, data)

    def get_pending(self, session_id: str) -> dict | None:
        if self.use_redis:
            data = self.client.get(f"session:{session_id}")
        else:
            item = self._fallback_store.get(session_id)
            if item and item[0] > time.monotonic():
                data = item[1]
            else:
                self._fallback_store.pop(session_id, None)
                data = None
        return json.loads(data) if data else None

    def clear_pending(self, session_id: str):
        if self.use_redis:
            self.client.delete(f"session:{session_id}")
        else:
            self._fallback_store.pop(session_id, None)


session_manager = SessionManager()
