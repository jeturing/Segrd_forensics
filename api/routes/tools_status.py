"""
Tools status endpoint (v4.1) used by maintenance panel.
Returns static info for now; extend with real checks per tool.
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/v41/tools", tags=["Tools Status"])


@router.get("/status")
async def tools_status():
    now = datetime.utcnow().isoformat() + "Z"
    return {
        "checked_at": now,
        "tools": [
            {"name": "sparrow", "status": "ok"},
            {"name": "hawk", "status": "ok"},
            {"name": "o365_extractor", "status": "unknown"},
            {"name": "loki", "status": "ok"},
            {"name": "yara", "status": "ok"}
        ]
    }
