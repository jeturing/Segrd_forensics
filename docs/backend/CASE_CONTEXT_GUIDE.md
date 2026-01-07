# Case Context Middleware - User Guide

**Version:** v4.5.0  
**Status:** ✅ Enabled  
**Date:** December 2024

---

## 📋 Overview

The **Case Context Middleware** ensures that all forensic operations are associated with a specific case ID. This improves:

- **Traceability**: All operations linked to investigations
- **Organization**: Evidence properly organized by case
- **Auditing**: Clear audit trail per case
- **Multi-tenancy**: Isolation between different investigations

---

## 🔧 How It Works

The middleware automatically:

1. Intercepts API requests
2. Checks if the endpoint requires a `case_id`
3. Extracts `case_id` from request (header, query, or body)
4. Validates the case ID exists
5. Injects `case_id` into `request.state` for downstream use

---

## 📡 Providing case_id

You can provide the `case_id` in three ways:

### Option 1: HTTP Header (Recommended)

```bash
curl -X POST http://localhost:8080/api/v1/m365/analyze \
  -H "X-Case-ID: IR-2024-001" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"xxx"}'
```

### Option 2: Query Parameter

```bash
curl -X POST "http://localhost:8080/api/v1/m365/analyze?case_id=IR-2024-001" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"xxx"}'
```

### Option 3: Request Body

```bash
curl -X POST http://localhost:8080/api/v1/m365/analyze \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "IR-2024-001",
    "tenant_id": "xxx"
  }'
```

---

## 🚦 Routes That Require case_id

### Forensic Analysis

- `POST /api/v1/m365/analyze` - M365 forensic analysis
- `POST /api/v1/endpoint/scan` - Endpoint scanning
- `POST /api/v1/endpoint/analyze` - Endpoint analysis
- `POST /forensics/m365/analyze` (deprecated)
- `POST /forensics/endpoint/scan` (deprecated)

### Investigations

- `POST /investigation/commands` - Execute investigation commands
- `POST /investigation/execute` - Run investigation
- `GET /investigation/status/{id}` - Check investigation status

### Threat Hunting

- `POST /hunting/execute` - Execute hunting query
- `POST /hunting/batch` - Batch hunting execution
- `POST /hunting/save-custom` - Save custom query

### Timeline

- `POST /timeline/events` - Add timeline events
- `POST /timeline/correlate` - Correlate events
- `POST /timeline/import` - Import timeline
- `GET /timeline/export` - Export timeline

### Reports

- `POST /reports/generate` - Generate report
- `POST /reports/generate-llm` - LLM-enhanced report

### Agents

- `POST /agents/tasks` - Create agent task
- `POST /agents/execute` - Execute on agent

---

## ✅ Routes That DON'T Require case_id

### System

- `GET /health` - Health check
- `GET /docs` - API documentation
- `GET /openapi.json` - OpenAPI spec

### Case Management

- `GET /api/v1/cases` - List all cases
- `POST /api/v1/cases` - Create new case (obviously!)
- `GET /api/v1/cases/{id}` - Get case details

### Configuration

- `GET /tenants` - List tenants
- `GET /llm/models` - List LLM models
- `GET /modules` - List modules

### Hunting Queries (Read-only)

- `GET /hunting/queries` - List available queries
- `GET /hunting/categories` - List categories
- `GET /hunting/stats` - Global stats

---

## 🐍 Python Client Example

```python
import requests

class ForensicsClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def analyze_m365(self, case_id: str, tenant_id: str, scope: list):
        """Run M365 analysis with case context"""
        self.session.headers['X-Case-ID'] = case_id
        
        response = self.session.post(
            f'{self.base_url}/api/v1/m365/analyze',
            json={
                'tenant_id': tenant_id,
                'scope': scope
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
client = ForensicsClient('http://localhost:8080', 'your-api-key')
result = client.analyze_m365(
    case_id='IR-2024-001',
    tenant_id='tenant-guid',
    scope=['sparrow', 'hawk']
)
```

---

## 🔨 JavaScript/TypeScript Example

```javascript
class ForensicsAPI {
  constructor(baseURL, apiKey) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
  }
  
  async analyzeM365(caseId, tenantId, scope) {
    const response = await fetch(`${this.baseURL}/api/v1/m365/analyze`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'X-Case-ID': caseId,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        tenant_id: tenantId,
        scope: scope
      })
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return await response.json();
  }
}

// Usage
const api = new ForensicsAPI('http://localhost:8080', 'your-api-key');
const result = await api.analyzeM365(
  'IR-2024-001',
  'tenant-guid',
  ['sparrow', 'hawk']
);
```

---

## ❌ Error Handling

### Missing case_id

If you forget to provide a `case_id` for a required endpoint:

```json
{
  "error": "case_id_required",
  "message": "This operation requires a case_id. Provide it via X-Case-ID header, case_id query parameter, or in the request body.",
  "path": "/api/v1/m365/analyze",
  "method": "POST"
}
```

**HTTP Status:** `400 Bad Request`

### Invalid case_id Format

```json
{
  "error": "invalid_case_id",
  "message": "case_id must follow format: IR-YYYY-NNN (e.g., IR-2024-001)",
  "provided": "CASE-001"
}
```

### Case Not Found

```json
{
  "error": "case_not_found",
  "message": "Case IR-2024-999 does not exist",
  "case_id": "IR-2024-999"
}
```

---

## 🔧 Troubleshooting

### Issue: "case_id_required" error on GET request

**Solution**: Most GET endpoints don't require `case_id`. Check the endpoint documentation.

### Issue: case_id not being recognized from body

**Solution**: Ensure you're sending `Content-Type: application/json` header.

### Issue: Different case_id in header vs body

**Solution**: The middleware prioritizes header > query > body. Use only one method to avoid confusion.

---

## 🧪 Testing with case_id

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient

def test_m365_analysis_requires_case_id(client: TestClient):
    """Test that M365 analysis requires case_id"""
    response = client.post(
        "/api/v1/m365/analyze",
        json={"tenant_id": "test"},
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 400
    assert "case_id_required" in response.json()["error"]

def test_m365_analysis_with_case_id(client: TestClient):
    """Test M365 analysis with valid case_id"""
    response = client.post(
        "/api/v1/m365/analyze",
        json={"tenant_id": "test"},
        headers={
            "X-API-Key": "test-key",
            "X-Case-ID": "IR-2024-001"
        }
    )
    assert response.status_code in [200, 202]
```

---

## 🔍 Accessing case_id in Endpoints

If you're developing new endpoints:

```python
from fastapi import Request, Depends
from api.middleware.case_context import require_case_id

@router.post("/my-endpoint")
async def my_endpoint(
    request: Request,
    case_id: str = Depends(require_case_id)
):
    # case_id is automatically extracted and validated
    print(f"Processing for case: {case_id}")
    return {"case_id": case_id, "status": "processing"}
```

---

## 📚 Best Practices

1. **Always use X-Case-ID header** - Most reliable method
2. **Create case first** - Use `POST /api/v1/cases` before analysis
3. **Validate case_id format** - Follow `IR-YYYY-NNN` pattern
4. **Keep case_id in session** - Store for multiple operations
5. **Log case_id** - Include in all log messages for traceability

---

## 🔄 Migration from Non-Context Endpoints

If you have existing code without `case_id`:

### Before (will fail now)

```python
response = requests.post(
    'http://localhost:8080/api/v1/m365/analyze',
    json={'tenant_id': 'xxx'},
    headers={'X-API-Key': 'key'}
)
```

### After (with case context)

```python
# Option 1: Create case first
case_response = requests.post(
    'http://localhost:8080/api/v1/cases',
    json={'name': 'Investigation 2024-001'},
    headers={'X-API-Key': 'key'}
)
case_id = case_response.json()['case_id']

# Option 2: Use existing case
case_id = 'IR-2024-001'

# Now run analysis
response = requests.post(
    'http://localhost:8080/api/v1/m365/analyze',
    json={'tenant_id': 'xxx'},
    headers={
        'X-API-Key': 'key',
        'X-Case-ID': case_id  # ← Add this
    }
)
```

---

## 📖 Additional Resources

- [Case Management API](./CASE_MANAGEMENT.md)
- [API Migration Guide](./API_MIGRATION.md)
- [Backend API Reference](./ESPECIFICACION_API.md)

---

**Last Updated:** December 16, 2024  
**Version:** 1.0

