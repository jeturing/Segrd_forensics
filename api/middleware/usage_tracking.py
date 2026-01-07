"""
Usage Tracking Middleware & Analytics
Combines Stripe billing tracking with detailed usage metrics.
"""

import hashlib
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Callable, Optional, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy import Column, String, Integer, DateTime, Float, JSON, BigInteger
from sqlalchemy.orm import Session

from api.database import Base, get_db_context
from api.models.billing import UsageType
from api.services.billing_service import get_billing_service

logger = logging.getLogger(__name__)


class ApiUsage(Base):
    """API usage tracking for billing and analytics."""

    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Request identification
    tenant_id = Column(String(100), index=True, nullable=True)
    user_id = Column(String(100), index=True, nullable=True)
    api_key_hash = Column(String(64), index=True, nullable=True)  # Hashed API key

    # Request details
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    path = Column(String(500), nullable=False)
    endpoint = Column(String(200), index=True, nullable=True)  # Normalized endpoint

    # Response
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)

    # Resource usage
    request_size_bytes = Column(BigInteger, nullable=True)
    response_size_bytes = Column(BigInteger, nullable=True)

    # Billing category
    usage_category = Column(
        String(50), index=True, nullable=True
    )  # compute, storage, api_call
    billable_units = Column(
        Float, default=1.0
    )  # Units to bill (e.g., API calls, GB transferred)

    # Metadata
    client_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_metadata = Column(
        JSON, nullable=True
    )  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "method": self.method,
            "path": self.path,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "usage_category": self.usage_category,
            "billable_units": self.billable_units,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API usage for billing and analytics.

    Tracks:
    - API calls by tenant/user
    - Response times and payload sizes
    - Endpoint usage with categories for billing
    """

    # Endpoints that are billable
    BILLABLE_ENDPOINTS = {
        "/api/v1/evidence-management/upload": "storage",
        "/api/v1/evidence-management/bulk-upload": "storage",
        "/api/v1/m365/analyze": "compute",
        "/api/v1/endpoint/scan": "compute",
        "/api/v1/credentials/check": "compute",
        "/reports/generate": "compute",
    }

    # Endpoints exempt from tracking (health checks, docs, etc.)
    EXEMPT_ENDPOINTS = ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]

    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
        exclude_paths: Optional[List[str]] = None,
        batch_size: int = 100,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.exclude_paths = exclude_paths or self.EXEMPT_ENDPOINTS
        self.batch_size = batch_size
        self._call_count = defaultdict(int)
        self.billing_service = get_billing_service() if enabled else None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track usage."""

        # Skip if disabled or excluded path
        if not self.enabled or self._should_exclude(request.url.path):
            return await call_next(request)

        tenant_id = self._extract_tenant_id(request)
        user_id = request.headers.get("X-User-ID")
        api_key = request.headers.get("X-API-Key")

        # Start timing
        start_time = time.time()
        request_size = int(request.headers.get("content-length", 0) or 0)

        try:
            response = await call_next(request)

            response_size = 0
            if hasattr(response, "headers") and response.headers.get("content-length"):
                response_size = int(response.headers.get("content-length"))

            duration_ms = int((time.time() - start_time) * 1000)
            usage_category, billable_units = self._classify_usage(
                request.url.path, request_size, response_size
            )
            normalized_path = self._normalize_path(request.url.path)

            # Record detailed usage for analytics
            try:
                with get_db_context() as db:
                    usage = ApiUsage(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        api_key_hash=self._hash_api_key(api_key) if api_key else None,
                        method=request.method,
                        path=request.url.path,
                        endpoint=normalized_path,
                        status_code=response.status_code,
                        response_time_ms=duration_ms,
                        request_size_bytes=request_size,
                        response_size_bytes=response_size,
                        usage_category=usage_category,
                        billable_units=billable_units,
                        client_ip=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        timestamp=datetime.utcnow(),
                    )
                    db.add(usage)
            except Exception as db_error:
                logger.error(f"❌ Error tracking usage: {db_error}", exc_info=True)

            # Record usage for Stripe billing (batched)
            if self.billing_service and tenant_id:
                await self._record_api_call(tenant_id, request, normalized_path)

            if tenant_id:
                response.headers["X-Billing-Tenant-ID"] = tenant_id
            response.headers["X-Billing-Tracked"] = "true"

            return response

        except Exception as e:
            logger.error(f"❌ Error in usage tracking middleware: {e}")
            raise
        finally:
            duration = time.time() - start_time
            if duration > 1.0:  # Log slow requests
                logger.warning(
                    f"⚠️ Slow request: {request.method} {request.url.path} ({duration:.2f}s)"
                )

    async def _record_api_call(
        self, tenant_id: str, request: Request, normalized_path: str
    ):
        """Record API usage to billing service in batches."""
        try:
            self._call_count[tenant_id] += 1

            if self._call_count[tenant_id] % self.batch_size != 0:
                return

            await self.billing_service.record_usage(
                tenant_id=tenant_id,
                usage_type=UsageType.API_CALL,
                quantity=self.batch_size,
                metadata={
                    "endpoint": normalized_path,
                    "method": request.method,
                    "batch_size": self.batch_size,
                },
            )

            logger.info(
                f"📊 API usage recorded: {tenant_id} - {self.batch_size} calls"
            )

        except Exception as e:
            logger.error(f"❌ Failed to record API usage: {e}")

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from tracking."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """
        Extract tenant_id from request.

        Tries multiple sources:
        1. Query parameter: ?tenant_id=...
        2. Header: X-Tenant-ID
        3. Path parameter (if present)
        """
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id

        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        path_parts = request.url.path.split("/")
        if "tenant" in path_parts:
            try:
                idx = path_parts.index("tenant")
                if idx + 1 < len(path_parts):
                    return path_parts[idx + 1]
            except (ValueError, IndexError):
                pass

        return None

    @staticmethod
    def _classify_usage(path: str, request_size: int, response_size: int):
        """
        Determine usage category and billable units based on endpoint.
        """
        usage_category = "api_call"
        billable_units = 1.0

        for endpoint, category in UsageTrackingMiddleware.BILLABLE_ENDPOINTS.items():
            if path.startswith(endpoint):
                usage_category = category
                if category == "storage":
                    billable_units = (request_size + response_size) / (1024**3)
                elif category == "compute":
                    billable_units = 1.0
                break

        return usage_category, billable_units

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Normalize path by replacing dynamic segments with placeholders.

        Examples:
        - /api/v1/evidence-management/EVD-2024-ABC -> /api/v1/evidence-management/{id}
        - /api/v1/cases/CASE-2024-001/commands -> /api/v1/cases/{id}/commands
        """
        parts = path.split("/")
        normalized = []

        for part in parts:
            # Check if part looks like an ID
            if (
                part.startswith("EVD-")
                or part.startswith("CASE-")
                or part.startswith("CMD-")
            ):
                normalized.append("{id}")
            elif part and part[0].isupper() and "-" in part:
                # Generic ID pattern (e.g., FA-2024-ABC)
                normalized.append("{id}")
            else:
                normalized.append(part)

        return "/".join(normalized)

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """Hash API key for storage (for analytics, not auth)."""
        return hashlib.sha256(api_key.encode()).hexdigest()


class UsageMetricsService:
    """Service for querying usage metrics."""

    @staticmethod
    def get_usage_summary(
        db: Session,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get usage summary for billing."""
        from sqlalchemy import func

        query = db.query(ApiUsage)

        if tenant_id:
            query = query.filter(ApiUsage.tenant_id == tenant_id)

        if user_id:
            query = query.filter(ApiUsage.user_id == user_id)

        if start_date:
            query = query.filter(ApiUsage.timestamp >= start_date)

        if end_date:
            query = query.filter(ApiUsage.timestamp <= end_date)

        # Calculate totals
        total_calls = query.count()
        total_billable_units = (
            db.query(func.sum(ApiUsage.billable_units))
            .filter(
                *[
                    f
                    for f in [
                        ApiUsage.tenant_id == tenant_id if tenant_id else None,
                        ApiUsage.user_id == user_id if user_id else None,
                        ApiUsage.timestamp >= start_date if start_date else None,
                        ApiUsage.timestamp <= end_date if end_date else None,
                    ]
                    if f is not None
                ]
            )
            .scalar()
            or 0
        )

        # Group by category
        by_category = (
            db.query(
                ApiUsage.usage_category,
                func.count(ApiUsage.id),
                func.sum(ApiUsage.billable_units),
            )
            .filter(
                *[
                    f
                    for f in [
                        ApiUsage.tenant_id == tenant_id if tenant_id else None,
                        ApiUsage.user_id == user_id if user_id else None,
                        ApiUsage.timestamp >= start_date if start_date else None,
                        ApiUsage.timestamp <= end_date if end_date else None,
                    ]
                    if f is not None
                ]
            )
            .group_by(ApiUsage.usage_category)
            .all()
        )

        # Group by endpoint
        by_endpoint = (
            db.query(ApiUsage.endpoint, func.count(ApiUsage.id))
            .filter(
                *[
                    f
                    for f in [
                        ApiUsage.tenant_id == tenant_id if tenant_id else None,
                        ApiUsage.user_id == user_id if user_id else None,
                        ApiUsage.timestamp >= start_date if start_date else None,
                        ApiUsage.timestamp <= end_date if end_date else None,
                    ]
                    if f is not None
                ]
            )
            .group_by(ApiUsage.endpoint)
            .order_by(func.count(ApiUsage.id).desc())
            .limit(10)
            .all()
        )

        return {
            "total_api_calls": total_calls,
            "total_billable_units": float(total_billable_units),
            "usage_by_category": [
                {"category": cat, "calls": count, "billable_units": float(units or 0)}
                for cat, count, units in by_category
            ],
            "top_endpoints": [
                {"endpoint": ep, "calls": count} for ep, count in by_endpoint
            ],
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }

    @staticmethod
    def export_usage_for_billing(
        db: Session, tenant_id: str, month: int, year: int
    ) -> dict:
        """Export usage data for billing system integration."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        summary = UsageMetricsService.get_usage_summary(
            db=db, tenant_id=tenant_id, start_date=start_date, end_date=end_date
        )

        return {
            "tenant_id": tenant_id,
            "billing_period": f"{year}-{month:02d}",
            "usage_summary": summary,
            "invoice_ready": True,
            "generated_at": datetime.utcnow().isoformat(),
        }


# Export service instance
usage_metrics_service = UsageMetricsService()


def create_usage_tracking_middleware(
    enabled: bool = True,
    exclude_paths: Optional[List[str]] = None,
    batch_size: int = 100,
):
    """
    Factory function to create usage tracking middleware.

    Args:
        enabled: Enable/disable usage tracking
        exclude_paths: List of paths to exclude from tracking
        batch_size: Record usage every N API calls (reduces DB writes)

    Returns:
        Configured middleware instance
    """

    def middleware(app: ASGIApp) -> UsageTrackingMiddleware:
        return UsageTrackingMiddleware(
            app=app,
            enabled=enabled,
            exclude_paths=exclude_paths,
            batch_size=batch_size,
        )

    return middleware
