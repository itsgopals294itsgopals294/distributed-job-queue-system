import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SQLITE_FILE = os.path.join(ROOT_DIR, "jobqueue.db").replace("\\", "/")

# Configure engine with connection pool
engine_args = {}
if "sqlite" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False, "timeout": 30.0}
else:
    engine_args["pool_size"] = 20
    engine_args["max_overflow"] = 10
    engine_args["pool_pre_ping"] = True

_engine = create_async_engine(settings.DATABASE_URL, echo=False, **engine_args)

_sessionmaker = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class AsyncSessionMakerProxy:
    def __call__(self, *args, **kwargs) -> AsyncSession:
        return _sessionmaker(*args, **kwargs)


AsyncSessionLocal = AsyncSessionMakerProxy()
engine = _engine


async def init_db():
    global _engine, _sessionmaker, engine
    try:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Database initialized with engine URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    except Exception as e:
        logger.warning(f"Could not connect to primary database ({settings.DATABASE_URL}): {e}")
        # If PostgreSQL failed and it's local development, fallback to SQLite
        if "postgresql" in settings.DATABASE_URL:
            fallback_url = f"sqlite+aiosqlite:///{SQLITE_FILE}"
            logger.info(f"Attempting fallback to local SQLite ({fallback_url})...")
            _engine = create_async_engine(fallback_url, echo=False, connect_args={"check_same_thread": False, "timeout": 30.0})
            engine = _engine
            _sessionmaker = async_sessionmaker(
                bind=_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Fallback to SQLite succeeded.")
        else:
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
