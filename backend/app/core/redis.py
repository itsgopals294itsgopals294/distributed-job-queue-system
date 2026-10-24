import tempfile
import os
import sys
import time
import json
import sqlite3
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

# Use high-speed local IPC directory for Redis mock database to avoid cloud sync file locks
LOCAL_IPC_DIR = os.path.join(tempfile.gettempdir(), "nexus_jobqueue")
os.makedirs(LOCAL_IPC_DIR, exist_ok=True)
DB_PATH = os.path.abspath(os.path.join(LOCAL_IPC_DIR, "_shared_redis.db"))


class FileBackedMockRedis:
    """
    Process-shared SQLite-backed Redis mock used when Redis server is not running on localhost.
    Allows independent backend, worker, and reaper processes to communicate seamlessly.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS redis_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT,
                    value TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_redis_lists_key ON redis_lists(key, id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS redis_zsets (
                    key TEXT,
                    member TEXT,
                    score REAL,
                    PRIMARY KEY (key, member)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS redis_sets (
                    key TEXT,
                    member TEXT,
                    PRIMARY KEY (key, member)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS redis_kv (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at REAL
                )
            """)
            conn.commit()

    async def ping(self) -> bool:
        return True

    async def rpush(self, key: str, *values: str) -> int:
        def _run():
            with self._get_conn() as conn:
                for v in values:
                    conn.execute("INSERT INTO redis_lists (key, value) VALUES (?, ?)", (key, str(v)))
                conn.commit()
                cur = conn.execute("SELECT COUNT(*) FROM redis_lists WHERE key = ?", (key,))
                return cur.fetchone()[0]
        return await asyncio.to_thread(_run)

    async def lpop(self, key: str) -> Optional[str]:
        def _run():
            with self._get_conn() as conn:
                cur = conn.execute("SELECT id, value FROM redis_lists WHERE key = ? ORDER BY id ASC LIMIT 1", (key,))
                row = cur.fetchone()
                if row:
                    row_id, val = row
                    conn.execute("DELETE FROM redis_lists WHERE id = ?", (row_id,))
                    conn.commit()
                    return val
                return None
        return await asyncio.to_thread(_run)

    async def llen(self, key: str) -> int:
        def _run():
            with self._get_conn() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM redis_lists WHERE key = ?", (key,))
                return cur.fetchone()[0]
        return await asyncio.to_thread(_run)

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        def _run():
            with self._get_conn() as conn:
                cur = conn.execute("SELECT value FROM redis_lists WHERE key = ? ORDER BY id ASC", (key,))
                rows = [r[0] for r in cur.fetchall()]
                if end == -1:
                    return rows[start:]
                return rows[start : end + 1]
        return await asyncio.to_thread(_run)

    async def lrem(self, key: str, count: int, value: str) -> int:
        def _run():
            with self._get_conn() as conn:
                if count == 0:
                    cur = conn.execute("DELETE FROM redis_lists WHERE key = ? AND value = ?", (key, str(value)))
                else:
                    cur = conn.execute("DELETE FROM redis_lists WHERE id IN (SELECT id FROM redis_lists WHERE key = ? AND value = ? LIMIT ?)", (key, str(value), count))
                conn.commit()
                return cur.rowcount
        return await asyncio.to_thread(_run)

    async def brpop(self, keys: Any, timeout: int = 0) -> Optional[Tuple[str, str]]:
        if isinstance(keys, str):
            keys = [keys]
        start_time = time.time()
        while True:
            for k in keys:
                item = await self.lpop(k)
                if item is not None:
                    return (k, item)
            if timeout > 0 and (time.time() - start_time) >= timeout:
                return None
            await asyncio.sleep(0.2)

    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        def _run():
            with self._get_conn() as conn:
                for member, score in mapping.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO redis_zsets (key, member, score) VALUES (?, ?, ?)",
                        (key, str(member), float(score))
                    )
                conn.commit()
                return len(mapping)
        return await asyncio.to_thread(_run)

    async def zrangebyscore(self, key: str, min_val: float, max_val: float, withscores: bool = False) -> List[Any]:
        def _run():
            with self._get_conn() as conn:
                cur = conn.execute(
                    "SELECT member, score FROM redis_zsets WHERE key = ? AND score >= ? AND score <= ? ORDER BY score ASC",
                    (key, float(min_val), float(max_val))
                )
                rows = cur.fetchall()
                if withscores:
                    return rows
                return [r[0] for r in rows]
        return await asyncio.to_thread(_run)

    async def zrem(self, key: str, *members: str) -> int:
        def _run():
            with self._get_conn() as conn:
                count = 0
                for m in members:
                    cur = conn.execute("DELETE FROM redis_zsets WHERE key = ? AND member = ?", (key, str(m)))
                    count += cur.rowcount
                conn.commit()
                return count
        return await asyncio.to_thread(_run)

    async def zcard(self, key: str) -> int:
        def _run():
            with self._get_conn() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM redis_zsets WHERE key = ?", (key,))
                return cur.fetchone()[0]
        return await asyncio.to_thread(_run)

    async def sadd(self, key: str, *members: str) -> int:
        def _run():
            with self._get_conn() as conn:
                count = 0
                for m in members:
                    try:
                        conn.execute("INSERT INTO redis_sets (key, member) VALUES (?, ?)", (key, str(m)))
                        count += 1
                    except sqlite3.IntegrityError:
                        pass
                conn.commit()
                return count
        return await asyncio.to_thread(_run)

    async def sismember(self, key: str, member: str) -> bool:
        def _run():
            with self._get_conn() as conn:
                cur = conn.execute("SELECT 1 FROM redis_sets WHERE key = ? AND member = ?", (key, str(member)))
                return cur.fetchone() is not None
        return await asyncio.to_thread(_run)

    async def srem(self, key: str, *members: str) -> int:
        def _run():
            with self._get_conn() as conn:
                count = 0
                for m in members:
                    cur = conn.execute("DELETE FROM redis_sets WHERE key = ? AND member = ?", (key, str(m)))
                    count += cur.rowcount
                conn.commit()
                return count
        return await asyncio.to_thread(_run)

    async def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        def _run():
            now = time.time()
            exp = (now + ex) if ex else None
            with self._get_conn() as conn:
                # Clean expired
                conn.execute("DELETE FROM redis_kv WHERE key = ? AND expires_at IS NOT NULL AND expires_at < ?", (key, now))
                if nx:
                    cur = conn.execute("SELECT 1 FROM redis_kv WHERE key = ?", (key,))
                    if cur.fetchone():
                        return False
                conn.execute("INSERT OR REPLACE INTO redis_kv (key, value, expires_at) VALUES (?, ?, ?)", (key, str(value), exp))
                conn.commit()
                return True
        return await asyncio.to_thread(_run)

    async def get(self, key: str) -> Optional[str]:
        def _run():
            now = time.time()
            with self._get_conn() as conn:
                cur = conn.execute("SELECT value, expires_at FROM redis_kv WHERE key = ?", (key,))
                row = cur.fetchone()
                if not row:
                    return None
                val, exp = row
                if exp and exp < now:
                    conn.execute("DELETE FROM redis_kv WHERE key = ?", (key,))
                    conn.commit()
                    return None
                return val
        return await asyncio.to_thread(_run)

    async def delete(self, *keys: str) -> int:
        def _run():
            with self._get_conn() as conn:
                count = 0
                for k in keys:
                    c1 = conn.execute("DELETE FROM redis_kv WHERE key = ?", (k,)).rowcount
                    c2 = conn.execute("DELETE FROM redis_lists WHERE key = ?", (k,)).rowcount
                    c3 = conn.execute("DELETE FROM redis_zsets WHERE key = ?", (k,)).rowcount
                    c4 = conn.execute("DELETE FROM redis_sets WHERE key = ?", (k,)).rowcount
                    count += (c1 + c2 + c3 + c4)
                conn.commit()
                return count
        return await asyncio.to_thread(_run)

    async def incr(self, key: str) -> int:
        def _run():
            with self._get_conn() as conn:
                now = time.time()
                cur = conn.execute("SELECT value, expires_at FROM redis_kv WHERE key = ?", (key,))
                row = cur.fetchone()
                val = 0
                exp = None
                if row:
                    v_str, exp = row
                    if exp is None or exp > now:
                        try:
                            val = int(v_str)
                        except (ValueError, TypeError):
                            val = 0
                    else:
                        val = 0
                val += 1
                conn.execute(
                    "INSERT OR REPLACE INTO redis_kv (key, value, expires_at) VALUES (?, ?, ?)",
                    (key, str(val), exp)
                )
                conn.commit()
                return val
        return await asyncio.to_thread(_run)

    async def expire(self, key: str, seconds: int) -> bool:
        def _run():
            exp = time.time() + seconds
            with self._get_conn() as conn:
                cur = conn.execute("UPDATE redis_kv SET expires_at = ? WHERE key = ?", (exp, key))
                conn.commit()
                return cur.rowcount > 0
        return await asyncio.to_thread(_run)

    async def close(self):
        pass


class RedisClient:
    _instance: Optional[Any] = None

    @classmethod
    async def get_client(cls):
        if cls._instance is None:
            try:
                client = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2.0
                )
                await client.ping()
                logger.info(f"Connected to Redis server at {settings.REDIS_URL}")
                cls._instance = client
            except Exception as e:
                logger.warning(f"Could not connect to Redis at {settings.REDIS_URL} ({e}). Using FileBackedMockRedis fallback.")
                cls._instance = FileBackedMockRedis()
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
