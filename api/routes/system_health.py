"""
Simple health endpoints for UI status checks.
"""

from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "mcp-kali-forensics",
        "version": "4.5.0",
        "api_port": int(os.getenv("BACKEND_PORT", "9000")),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
