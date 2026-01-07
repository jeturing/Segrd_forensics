"""HexStrike AI client (Red Team v4.6)
Simple async wrapper around HexStrike REST API with graceful fallbacks.
"""
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

from api.config import settings

logger = logging.getLogger(__name__)


class HexStrikeClient:
    """HTTP client for HexStrike AI MCP server."""

    def __init__(self):
        self.base_url = settings.HEXSTRIKE_BASE_URL.rstrip("/")
        self.api_key = settings.HEXSTRIKE_API_KEY
        self.timeout = settings.HEXSTRIKE_TIMEOUT

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            return await self._get("/health")
        except Exception as e:
            logger.error(f"HexStrike health failed: {e}")
            return {"healthy": False, "error": str(e)}

    async def analyze_target(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._post("/api/intelligence/analyze-target", payload)

    async def select_tools(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._post("/api/intelligence/select-tools", payload)

    async def run_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._post("/api/command", payload)
        # Ensure run_id exists
        run_id = result.get("run_id") or f"rt-run-{uuid.uuid4()}"
        result.setdefault("run_id", run_id)
        return result

    async def get_process_status(self, pid: str) -> Dict[str, Any]:
        return await self._get(f"/api/processes/status/{pid}")

    async def terminate_process(self, pid: str) -> Dict[str, Any]:
        return await self._post(f"/api/processes/terminate/{pid}", {})

    async def list_processes(self) -> Dict[str, Any]:
        return await self._get("/api/processes/list")


hexstrike_client = HexStrikeClient()
