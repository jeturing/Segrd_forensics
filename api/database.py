"""
MCP Kali Forensics - Database Configuration
SQLAlchemy engine, session and base configuration
"""

from sqlalchemy import create_engine, TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager, asynccontextmanager
import os
import uuid
from pathlib import Path

from api.config import settings


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as string.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value

# Database URL - SQLite por defecto, configurable via env
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL) or f"sqlite:///{BASE_DIR}/forensics.db"

# Convertir asyncpg a psycopg2 para operaciones sincrónicas
if "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Para SQLite necesitamos check_same_thread=False
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG
    )
else:
    engine = create_engine(DATABASE_URL, echo=settings.DEBUG)

# SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class para modelos
Base = declarative_base()


def get_db():
    """
    Dependency para obtener sesión de BD en endpoints FastAPI.
    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager síncrono para usar fuera de endpoints FastAPI.
    Usage:
        with get_db_context() as db:
            db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_context():
    """
    Context manager async para usar en funciones async.
    Usage:
        async with get_async_db_context() as db:
            db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Inicializar base de datos - crear todas las tablas.
    Llamar en startup de la aplicación.
    """
    from api.models import ioc, investigation, case, tool_report  # noqa: F401
    from api.models import tools, redteam, user, tenant  # noqa: F401
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """
    Eliminar todas las tablas - SOLO PARA DESARROLLO/TESTING.
    """
    Base.metadata.drop_all(bind=engine)
