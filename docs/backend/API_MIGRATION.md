# API Migration Guide - v4.5 to v5.0

**Status:** 🟡 In Progress  
**Effective Date:** December 2024  
**Completion Target:** v5.0.0 (Q1 2025)

---

## 📋 Overview

This guide helps you migrate from legacy API routes to the new consolidated `/api/v1/*` structure.

### Why Consolidate?

- **Consistency**: All API endpoints under `/api/v1/` prefix
- **Versioning**: Explicit API version in URL
- **Future-proof**: Easy to introduce v2, v3, etc.
- **Standards**: Follows RESTful API best practices

---

## 🔄 Route Changes

### Case Management

| Old Route (Deprecated) | New Route (Recommended) |
|------------------------|-------------------------|
| `POST /cases` | `POST /api/v1/cases` |
| `GET /cases/{id}` | `GET /api/v1/cases/{id}` |
| `POST /forensics/case` | `POST /api/v1/cases` |
| `POST /api/cases` | `POST /api/v1/cases` |

### Credentials

| Old Route (Deprecated) | New Route (Recommended) |
|------------------------|-------------------------|
| `POST /credentials/check` | `POST /api/v1/credentials/check` |
| `POST /forensics/credentials/check` | `POST /api/v1/credentials/check` |

### M365 Forensics

| Old Route (Deprecated) | New Route (Recommended) |
|------------------------|-------------------------|
| `POST /forensics/m365/analyze` | `POST /api/v1/m365/analyze` |
| `GET /forensics/m365/status/{id}` | `GET /api/v1/m365/status/{id}` |

### Endpoint Forensics

| Old Route (Deprecated) | New Route (Recommended) |
|------------------------|-------------------------|
| `POST /forensics/endpoint/scan` | `POST /api/v1/endpoint/scan` |
| `GET /forensics/endpoint/results/{id}` | `GET /api/v1/endpoint/results/{id}` |

---

## 🔧 Migration Steps

### 1. Identify Usage

Search your codebase for deprecated routes:

```bash
# Find all API calls
grep -r "/cases" --include="*.js" --include="*.py" --include="*.ts"
grep -r "/forensics/" --include="*.js" --include="*.py" --include="*.ts"
grep -r "/credentials" --include="*.js" --include="*.py" --include="*.ts"
```

### 2. Update API Calls

#### Python Example

```python
# Before (deprecated)
response = requests.post(
    "http://localhost:8080/cases",
    json={"name": "Investigation 001"},
    headers={"X-API-Key": api_key}
)

# After (recommended)
response = requests.post(
    "http://localhost:8080/api/v1/cases",
    json={"name": "Investigation 001"},
    headers={"X-API-Key": api_key}
)
```

#### JavaScript/TypeScript Example

```javascript
// Before (deprecated)
const response = await fetch('http://localhost:8080/cases', {
  method: 'POST',
  headers: {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ name: 'Investigation 001' })
});

// After (recommended)
const response = await fetch('http://localhost:8080/api/v1/cases', {
  method: 'POST',
  headers: {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ name: 'Investigation 001' })
});
```

#### cURL Example

```bash
# Before (deprecated)
curl -X POST http://localhost:8080/cases \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"Investigation 001"}'

# After (recommended)
curl -X POST http://localhost:8080/api/v1/cases \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"Investigation 001"}'
```

### 3. Test Updated Calls

Run your test suite to ensure all API calls work:

```bash
pytest tests/ -v -k "test_api"
npm test -- --grep "API"
```

### 4. Monitor Deprecation Warnings

Check response headers for deprecation notices:

```python
response = requests.get("http://localhost:8080/cases/IR-001")
print(response.headers.get('X-API-Deprecated'))  # "true" if deprecated
print(response.headers.get('X-API-New-Path'))    # New recommended path
```

---

## ⏱️ Timeline

| Version | Date | Status |
|---------|------|--------|
| **v4.5.0** | Dec 2024 | ✅ New `/api/v1/*` routes available |
| **v4.5.0** | Dec 2024 | 🟡 Legacy routes marked deprecated |
| **v4.6.0** | Jan 2025 | ⚠️ Deprecation warnings in responses |
| **v4.7.0** | Feb 2025 | ⚠️ Legacy routes log warnings |
| **v5.0.0** | Mar 2025 | ❌ Legacy routes removed |

---

## 🔍 Detecting Deprecated Routes

### Check Response Headers

Deprecated routes return special headers:

```http
HTTP/1.1 200 OK
X-API-Deprecated: true
X-API-Deprecated-Since: v4.5.0
X-API-Removal-Version: v5.0.0
X-API-New-Path: /api/v1/cases
```

### Check Server Logs

Look for deprecation warnings in server logs:

```bash
tail -f logs/mcp-forensics.log | grep "DEPRECATED"
```

### Using the Deprecation Checker

Run the automated checker:

```bash
python scripts/check_deprecated_routes.py --config .env
```

---

## 📝 Configuration Updates

### Update Environment Variables

No configuration changes needed - all routes work with existing settings.

### Update Frontend Configuration

Update base URLs in your frontend:

```javascript
// src/config/api.js
export const API_BASE_URL = '/api/v1';  // Changed from '/'

// Usage
const response = await fetch(`${API_BASE_URL}/cases/${caseId}`);
```

---

## 🆘 Troubleshooting

### Issue: "Route not found" after migration

**Solution**: Ensure you've updated **all** occurrences of the old route.

### Issue: CORS errors with new routes

**Solution**: Update CORS configuration to allow `/api/v1/*` paths.

### Issue: Authentication failures

**Solution**: Ensure `X-API-Key` header is still included in requests.

---

## 📚 Additional Resources

- [API Documentation](/docs)
- [Swagger UI](http://localhost:8080/docs)
- [OpenAPI Spec](http://localhost:8080/openapi.json)
- [GitHub Issues](https://github.com/jcarvajalantigua/mcp-kali-forensics/issues)

---

## ✅ Migration Checklist

- [ ] Identified all deprecated route usage
- [ ] Updated API calls to use `/api/v1/*` prefix
- [ ] Updated frontend configuration
- [ ] Updated documentation
- [ ] Ran tests to verify changes
- [ ] Monitored for deprecation warnings
- [ ] Removed deprecated code before v5.0.0

---

**Questions?** Create an issue on GitHub or contact the development team.

**Last Updated:** December 16, 2024  
**Version:** 1.0
