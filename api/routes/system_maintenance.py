"""
System Maintenance Routes

Objetivo:
- Exponer estadísticas de BD (SQLite actual, preparado para migración a Postgres).
- Permitir optimización (VACUUM) y limpieza controlada de datos de desarrollo.
- Entregar metadata de entorno para facilitar el paso a producción.
- Permitir seleccionar motor (SQLite local o PostgREST/PG) y lanzar migración.
"""

import os
import sqlite3
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from api.middleware.auth import verify_api_key
from api.config import settings
from sqlalchemy import create_engine, text

router = APIRouter(
    prefix="/api/v41/system",
    tags=["System Maintenance"],
    dependencies=[Depends(verify_api_key)],
)


DEFAULT_TABLES = [
    "cases",
    "investigations",
    "iocs",
    "m365_users",
    "tool_executions",
    "agents",
    "playbooks",
    "correlation_rules",
    "graph_nodes",
    "timeline_events",
    "forensic_analyses",
    "tenants",
    "activity_log",
]


class CleanRequest(BaseModel):
    """Petición para limpieza/optimización de BD."""

    confirm: bool = False
    scope: Optional[List[str]] = None
    optimize_only: bool = False


class DbModeRequest(BaseModel):
    """Seleccionar modo de BD desde el panel."""

    mode: str  # sqlite | postgrest
    postgrest_url: Optional[str] = None
    database_url: Optional[str] = None  # conexión Postgres para stats/migración


class MigrateRequest(BaseModel):
    """Solicitud para migrar SQLite -> Postgres."""

    target_url: Optional[str] = None


DB_MODE_FILE = settings.PROJECT_ROOT / "config" / "db_mode.json"


def _load_db_mode():
    if DB_MODE_FILE.exists():
        try:
            with open(DB_MODE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "mode": settings.DB_MODE,
        "postgrest_url": settings.POSTGREST_URL,
        "database_url": settings.DATABASE_URL,
    }


def _save_db_mode(mode: str, postgrest_url: Optional[str], database_url: Optional[str]):
    DB_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "mode": mode,
        "postgrest_url": postgrest_url,
        "database_url": database_url or settings.DATABASE_URL,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(DB_MODE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def _sqlite_path_from_url(database_url: str) -> Path:
    """Extrae el path de sqlite://... a Path local."""
    if database_url.startswith("sqlite:///"):
        return Path(database_url.replace("sqlite:///", "", 1))
    if database_url.startswith("sqlite://"):
        return Path(database_url.replace("sqlite://", "", 1))
    parsed = urlparse(database_url)
    if parsed.scheme == "sqlite":
        return Path(parsed.path)
    # Fallback: usar path por defecto en el repo
    return Path("forensics.db")


def _get_sqlite_conn() -> sqlite3.Connection:
    db_path = _sqlite_path_from_url(settings.DATABASE_URL)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _get_postgres_engine(pg_url: str):
    # Usa SQLAlchemy para consultas rápidas
    return create_engine(pg_url, future=True)


@router.get("/environment")
async def get_environment_info():
    """
    Devuelve información básica del motor de BD y estado actual.
    Útil para preparar migración a Postgres manteniendo SQLite operativo.
    """
    mode_cfg = _load_db_mode()
    db_url = mode_cfg.get("database_url") or settings.DATABASE_URL
    parsed = urlparse(db_url)
    engine = parsed.scheme or "sqlite"
    is_sqlite = engine.startswith("sqlite")
    db_path = str(_sqlite_path_from_url(db_url)) if is_sqlite else db_url

    return {
        "engine": engine,
        "database": db_path,
        "mode": mode_cfg.get("mode", "sqlite"),
        "postgrest_url": mode_cfg.get("postgrest_url"),
        "migration_hint": "Para Postgres, configure DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname",
        "api_port": int(os.getenv("BACKEND_PORT", "9000")),
        "frontend_port": int(os.getenv("FRONTEND_PORT", "3000")),
        "evidence_dir": str(settings.EVIDENCE_DIR),
    }


@router.get("/db-stats")
async def get_db_stats():
    """
    Retorna estadísticas mínimas de tablas en SQLite local.
    Si en el futuro se usa Postgres, este endpoint puede adaptarse a consultas PG.
    """
    mode_cfg = _load_db_mode()
    db_url = mode_cfg.get("database_url") or settings.DATABASE_URL
    engine_scheme = urlparse(db_url).scheme or "sqlite"
    is_sqlite = engine_scheme.startswith("sqlite")

    if is_sqlite:
        db_path = _sqlite_path_from_url(db_url)
        if not db_path.exists():
            raise HTTPException(status_code=404, detail=f"Archivo SQLite no encontrado: {db_path}")

        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        tables_info = []

        for table in DEFAULT_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()["count"]
            except Exception:
                count = 0  # Tabla puede no existir
            tables_info.append({"name": table, "rows": count})

        size_bytes = os.path.getsize(db_path)
        conn.close()

        return {
            "engine": engine_scheme,
            "database": str(db_path),
            "size_bytes": size_bytes,
            "last_checked": datetime.utcnow().isoformat() + "Z",
            "tables": tables_info,
            "mode": mode_cfg.get("mode", "sqlite"),
        }

    # Postgres stats vía SQLAlchemy (solo conteo de tablas conocidas)
    try:
        engine = _get_postgres_engine(db_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo crear engine Postgres: {e}")

    tables_info = []
    with engine.connect() as conn:
        for table in DEFAULT_TABLES:
            try:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = res.scalar() or 0
            except Exception:
                count = 0
            tables_info.append({"name": table, "rows": count})
    size_bytes = None  # No fácil sin extensión; omitimos

    return {
        "engine": engine_scheme,
        "database": db_url,
        "size_bytes": size_bytes,
        "last_checked": datetime.utcnow().isoformat() + "Z",
        "tables": tables_info,
        "mode": mode_cfg.get("mode", "postgrest"),
    }


@router.post("/db-clean")
async def clean_database(request: CleanRequest):
    """
    Limpia datos de desarrollo y/o ejecuta VACUUM.
    - confirm=True es obligatorio para evitar borrados accidentales.
    - scope: lista de tablas a limpiar. Si se omite, usa DEFAULT_TABLES.
    - optimize_only: True ejecuta solo VACUUM (sin borrar datos).
    """
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Se requiere confirm=true para ejecutar limpieza")

    db_url = settings.DATABASE_URL
    engine = urlparse(db_url).scheme or "sqlite"
    is_sqlite = engine.startswith("sqlite")

    if not is_sqlite:
        raise HTTPException(status_code=400, detail="Solo se soporta limpieza SQLite en esta versión")

    conn = _get_sqlite_conn()
    cursor = conn.cursor()
    cleared_tables = []

    try:
        if not request.optimize_only:
            target_tables = request.scope or DEFAULT_TABLES
            for table in target_tables:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    cleared_tables.append(table)
                except Exception:
                    # Ignorar tablas inexistentes para no romper el proceso
                    continue
        # Optimización
        cursor.execute("VACUUM")
        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "optimized": True,
        "cleared_tables": cleared_tables,
        "engine": engine,
    }


@router.get("/db-mode")
async def get_db_mode():
    """Devuelve modo actual (sqlite | postgrest) y URLs configuradas."""
    return _load_db_mode()


@router.post("/db-mode")
async def set_db_mode(request: DbModeRequest):
    mode = request.mode.lower()
    if mode not in {"sqlite", "postgrest"}:
        raise HTTPException(status_code=400, detail="mode debe ser sqlite o postgrest")
    if mode == "postgrest" and not (request.postgrest_url or settings.POSTGREST_URL):
        raise HTTPException(status_code=400, detail="postgrest_url requerido para modo postgrest")

    cfg = _save_db_mode(
        mode=mode,
        postgrest_url=request.postgrest_url or settings.POSTGREST_URL,
        database_url=request.database_url or settings.DATABASE_URL,
    )
    return {"success": True, **cfg}


@router.post("/db-migrate")
async def migrate_sqlite_to_postgres(request: MigrateRequest):
    """Ejecuta migración SQLite -> Postgres usando script local.

    target_url: URI de Postgres. Si no se envía, se intenta usar la config guardada o fallback local.
    """
    mode_cfg = _load_db_mode()
    sqlite_path = _sqlite_path_from_url(settings.DATABASE_URL)
    target_url = (
        request.target_url
        or mode_cfg.get("database_url")
        or os.getenv("DATABASE_URL")
        or "postgresql://root:.@localhost:5433/forensics_db"
    )

    script_path = settings.PROJECT_ROOT / "scripts" / "migrate_sqlite_to_postgres.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Script de migración no encontrado")

    if not sqlite_path.exists():
        raise HTTPException(status_code=404, detail=f"SQLite no encontrado en {sqlite_path}")

    cmd = ["python3", str(script_path), "--sqlite", str(sqlite_path), "--pg", target_url]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Migración falló: {stderr.decode()[:400]}"
        )

    return {
        "success": True,
        "mode": mode_cfg.get("mode", "sqlite"),
        "target": target_url,
        "stdout": stdout.decode()[:4000],
    }
