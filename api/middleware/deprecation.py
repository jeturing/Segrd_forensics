"""
API Route Deprecation and Migration Guide

This module provides deprecation warnings for legacy routes
and guides users to the new consolidated API structure.
"""

from fastapi import Request, Response
from fastapi.routing import APIRoute
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class DeprecatedRoute(APIRoute):
    """
    Custom route class that adds deprecation warnings to legacy endpoints
    """
    
    def __init__(
        self,
        path: str,
        endpoint: Callable,
        *,
        deprecated_since: str = "v4.5.0",
        removal_version: str = "v5.0.0",
        new_path: str = None,
        **kwargs
    ):
        self.deprecated_since = deprecated_since
        self.removal_version = removal_version
        self.new_path = new_path
        super().__init__(path, endpoint, **kwargs)
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Log deprecation warning
            logger.warning(
                f"Deprecated endpoint accessed: {request.method} {request.url.path} "
                f"(deprecated since {self.deprecated_since}, "
                f"will be removed in {self.removal_version})"
            )
            
            # Add deprecation header to response
            response = await original_route_handler(request)
            response.headers["X-API-Deprecated"] = "true"
            response.headers["X-API-Deprecated-Since"] = self.deprecated_since
            response.headers["X-API-Removal-Version"] = self.removal_version
            
            if self.new_path:
                response.headers["X-API-New-Path"] = self.new_path
            
            return response
        
        return custom_route_handler


# =============================================================================
# Route Migration Map
# =============================================================================

ROUTE_MIGRATION_MAP = {
    # Legacy routes -> New consolidated routes
    "/cases": "/api/v1/cases",
    "/forensics/case": "/api/v1/cases",
    "/credentials": "/api/v1/credentials",
    "/forensics/credentials": "/api/v1/credentials",
    "/forensics/endpoint": "/api/v1/endpoint",
    "/forensics/m365": "/api/v1/m365",
}


def get_new_route(old_route: str) -> str:
    """Get the new route for a legacy endpoint"""
    return ROUTE_MIGRATION_MAP.get(old_route, old_route)


def log_route_access(path: str, method: str, is_deprecated: bool = False):
    """Log API route access for monitoring"""
    if is_deprecated:
        logger.warning(f"DEPRECATED: {method} {path}")
    else:
        logger.info(f"API: {method} {path}")


# =============================================================================
# Deprecation Notice for Documentation
# =============================================================================

DEPRECATION_NOTICE = """
## 🚨 API Deprecation Notice

The following routes are deprecated and will be removed in v5.0.0:

### Case Management
- ❌ `/cases/*` → ✅ `/api/v1/cases/*`
- ❌ `/forensics/case/*` → ✅ `/api/v1/cases/*`

### Credentials
- ❌ `/credentials/*` → ✅ `/api/v1/credentials/*`
- ❌ `/forensics/credentials/*` → ✅ `/api/v1/credentials/*`

### Endpoint Forensics
- ❌ `/forensics/endpoint/*` → ✅ `/api/v1/endpoint/*`

### M365 Forensics
- ❌ `/forensics/m365/*` → ✅ `/api/v1/m365/*`

### Migration Guide

1. Update your API calls to use the new `/api/v1/*` prefix
2. Check response headers for `X-API-Deprecated` to identify deprecated routes
3. Legacy routes will return a `X-API-New-Path` header with the new endpoint

### Timeline
- **v4.5.0** (Current): Legacy routes deprecated but functional
- **v4.6.0**: Deprecation warnings in responses
- **v5.0.0**: Legacy routes removed

### Example

```python
# OLD (deprecated)
response = requests.get("http://localhost:8080/cases/IR-2024-001")

# NEW (recommended)
response = requests.get("http://localhost:8080/api/v1/cases/IR-2024-001")
```

For questions, see: /docs/backend/API_MIGRATION.md
"""


def generate_deprecation_response(old_path: str, method: str) -> dict:
    """Generate a deprecation notice response"""
    new_path = get_new_route(old_path.split("?")[0])  # Remove query params
    
    return {
        "deprecated": True,
        "message": f"This endpoint ({method} {old_path}) is deprecated",
        "deprecated_since": "v4.5.0",
        "removal_version": "v5.0.0",
        "new_endpoint": new_path,
        "documentation": "/docs#deprecation-notice"
    }
