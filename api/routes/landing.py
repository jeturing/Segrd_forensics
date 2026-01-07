"""
Landing Content Routes
Admin + Public endpoints para gestionar y exponer el contenido del landing (i18n)
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.middleware.auth import get_current_user, require_global_admin
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LandingSectionPayload(BaseModel):
    items: Any = Field(..., description="Arreglo/objeto con los elementos de la sección")


# Public router (sin autenticación)
public_router = APIRouter(prefix="/api/public", tags=["Public Landing"])


def _fetch_landing(conn, locale: str) -> Dict[str, Any]:
    from psycopg2.extras import RealDictCursor
    data: Dict[str, Any] = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT section, content
            FROM landing_content
            WHERE locale = %s AND is_active = TRUE
            ORDER BY section, display_order
            """,
            (locale,),
        )
        rows = cur.fetchall()
    for r in rows:
        # content is a JSONB; normalize to python dict
        section = r["section"]
        content = r["content"]
        # Unificar a {items:[...]} si es simple
        if isinstance(content, dict) and "items" in content:
            data[section] = content
        else:
            data[section] = {"items": content}
    return data


@public_router.get("/landing")
async def get_public_landing(locale: str = Query("es", max_length=8)):
    """
    Obtener contenido del landing público por `locale`.
    """
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
        )
        data = _fetch_landing(conn, locale)
        conn.close()

        return {"success": True, "locale": locale, "data": data}
    except Exception as e:
        logger.warning(f"⚠️ Landing público no disponible: {e}")
        # Fallback mínimo
        return {
            "success": True,
            "locale": locale,
            "data": {
                "plans": {"items": []},
                "features": {"items": []},
                "testimonials": {"items": []},
                "stats": {"items": []},
                "integrations": {"items": []},
                "capabilities": {"items": []},
            },
            "note": "landing_content no inicializado",
        }


# Admin router (protegido por Global Admin)
admin_router = APIRouter(
    prefix="/api/global-admin",
    tags=["Global Admin Landing"],
    dependencies=[Depends(require_global_admin)],
)


@admin_router.get("/landing")
async def admin_get_landing(locale: str = Query("es", max_length=8), current_user: dict = Depends(get_current_user)):
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
        )
        data = _fetch_landing(conn, locale)
        conn.close()
        return {"success": True, "locale": locale, "data": data}
    except Exception as e:
        logger.error(f"❌ Error leyendo landing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.put("/landing/{section}")
async def admin_update_landing_section(
    section: str,
    payload: LandingSectionPayload,
    locale: str = Query("es", max_length=8),
    current_user: dict = Depends(get_current_user),
):
    """
    Actualiza o crea una sección del landing (i18n).
    section ∈ {plans,features,testimonials,stats,integrations,capabilities,hero}
    payload: { items: [...] } ó un objeto libre por sección (hero)
    """
    try:
        import psycopg2
        from psycopg2.extras import Json

        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO landing_content (section, locale, content, display_order, is_active, updated_at, updated_by)
                VALUES (%s, %s, %s, 0, TRUE, NOW(), %s)
                ON CONFLICT (section, locale) DO UPDATE
                SET content = EXCLUDED.content,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                """,
                (section, locale, Json(payload.dict()), current_user.get("user_id")),
            )
            conn.commit()
        conn.close()

        logger.info(f"⚙️ Landing section '{section}' actualizada ({locale})")
        return {"success": True, "message": f"Section {section} updated", "locale": locale}
    except Exception as e:
        logger.error(f"❌ Error actualizando landing {section}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
