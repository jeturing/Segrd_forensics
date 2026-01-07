# Evidence Management API Documentation

## Overview

The Evidence Management system allows users to upload, manage, and track forensic evidence from external tools including Axion Forensic, Autopsy, and other open-source forensic tools. All evidence is tracked with complete chain of custody and command traceability.

## Key Features

- ✅ **External Evidence Upload**: Upload evidence from any forensic tool
- ✅ **Integrity Verification**: Automatic MD5, SHA1, and SHA256 hashing
- ✅ **Flexible Associations**: Link evidence to cases, agents, users, or events
- ✅ **Command Traceability**: Complete logging of all forensic tool executions
- ✅ **Chain of Custody**: Automatic custody chain tracking
- ✅ **API Usage Tracking**: Billing-ready usage metrics
- ✅ **Multi-Tenant Support**: Isolated evidence per tenant

## Database Schema

### Evidence Tables

#### `evidence_sources`
Tracks external forensic tools that generated evidence.

```sql
CREATE TABLE evidence_sources (
    id INTEGER PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    tool_version VARCHAR(50),
    tool_vendor VARCHAR(100),
    tool_category VARCHAR(50),  -- disk_forensics, memory_forensics, etc.
    tool_type VARCHAR(50),      -- commercial, open_source, custom
    supported_formats JSON,
    created_at DATETIME
);
```

#### `external_evidences`
Stores uploaded evidence files and metadata.

```sql
CREATE TABLE external_evidences (
    id VARCHAR(50) PRIMARY KEY,  -- EVD-YYYY-XXXXX
    name VARCHAR(500) NOT NULL,
    evidence_type VARCHAR(50) NOT NULL,
    source_tool_id INTEGER,
    file_path VARCHAR(1024),
    file_size BIGINT,
    file_hash_md5 VARCHAR(32),
    file_hash_sha1 VARCHAR(40),
    file_hash_sha256 VARCHAR(64),
    collected_by VARCHAR(100),
    custody_chain JSON,
    integrity_verified BOOLEAN,
    tags JSON,
    uploaded_at DATETIME,
    FOREIGN KEY (source_tool_id) REFERENCES evidence_sources(id)
);
```

#### `evidence_associations`
Links evidence to cases, agents, users, or events.

```sql
CREATE TABLE evidence_associations (
    id INTEGER PRIMARY KEY,
    evidence_id VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- case, agent, user, event
    entity_id VARCHAR(100) NOT NULL,
    association_type VARCHAR(50),       -- primary, secondary, reference
    relevance VARCHAR(20),              -- critical, high, medium, low
    created_at DATETIME,
    FOREIGN KEY (evidence_id) REFERENCES external_evidences(id)
);
```

#### `command_logs`
Complete traceability of all forensic tool executions.

```sql
CREATE TABLE command_logs (
    id VARCHAR(50) PRIMARY KEY,  -- CMD-YYYY-XXXXXXXX
    command TEXT NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    case_id VARCHAR(50),
    evidence_id VARCHAR(50),
    executed_by VARCHAR(100),
    status VARCHAR(30),  -- pending, running, completed, failed
    exit_code INTEGER,
    duration_seconds INTEGER,
    started_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (evidence_id) REFERENCES external_evidences(id)
);
```

### Billing Tables

#### `api_usage`
Tracks API usage for billing integration.

```sql
CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY,
    tenant_id VARCHAR(100),
    user_id VARCHAR(100),
    method VARCHAR(10),
    path VARCHAR(500),
    endpoint VARCHAR(200),
    status_code INTEGER,
    response_time_ms INTEGER,
    usage_category VARCHAR(50),  -- compute, storage, api_call
    billable_units FLOAT,
    timestamp DATETIME
);
```

## API Endpoints

### Evidence Upload

#### POST `/api/v1/evidence-management/upload`

Upload a single evidence file.

**Request:**
```http
POST /api/v1/evidence-management/upload
Content-Type: multipart/form-data
X-API-Key: your-api-key

{
    "file": <binary>,
    "name": "Disk Image from Investigation",
    "evidence_type": "disk_image",
    "description": "E01 image from suspect laptop",
    "source_tool_name": "Autopsy",
    "collected_by": "analyst@company.com",
    "tags": ["malware", "exfiltration"]
}
```

**Response:**
```json
{
    "success": true,
    "evidence_id": "EVD-2024-A1B2C",
    "file_name": "suspect_laptop.e01",
    "file_size": 104857600,
    "sha256": "abc123def456...",
    "message": "Evidence uploaded successfully"
}
```

#### POST `/api/v1/evidence-management/bulk-upload`

Upload multiple evidence files at once.

**Request:**
```http
POST /api/v1/evidence-management/bulk-upload
Content-Type: multipart/form-data
X-API-Key: your-api-key

{
    "files": [<binary1>, <binary2>, ...],
    "case_id": "CASE-2024-001",
    "evidence_type": "timeline",
    "source_tool_name": "Plaso"
}
```

**Response:**
```json
{
    "total_files": 5,
    "successful": 5,
    "failed": 0,
    "results": [
        {
            "success": true,
            "file_name": "timeline1.csv",
            "evidence_id": "EVD-2024-X1Y2Z"
        }
    ]
}
```

### Evidence Retrieval

#### GET `/api/v1/evidence-management/`

List all evidence with optional filters.

**Query Parameters:**
- `evidence_type` (optional): Filter by type
- `source_tool_name` (optional): Filter by source tool
- `tags` (optional): Comma-separated tags
- `limit` (default: 50, max: 200)
- `offset` (default: 0)

**Response:**
```json
{
    "total": 42,
    "limit": 50,
    "offset": 0,
    "evidences": [
        {
            "id": "EVD-2024-A1B2C",
            "name": "Memory Dump",
            "evidence_type": "memory_dump",
            "file_size": 8589934592,
            "sha256": "abc123...",
            "collected_by": "analyst@company.com",
            "uploaded_at": "2024-12-16T08:00:00Z"
        }
    ]
}
```

#### GET `/api/v1/evidence-management/{evidence_id}`

Get detailed information about specific evidence.

**Response:**
```json
{
    "evidence": {
        "id": "EVD-2024-A1B2C",
        "name": "Memory Dump",
        "evidence_type": "memory_dump",
        "file_name": "memory.dmp",
        "file_size": 8589934592,
        "sha256": "abc123...",
        "collected_by": "analyst@company.com",
        "integrity_verified": true,
        "tags": ["malware", "rootkit"]
    },
    "associations": [
        {
            "entity_type": "case",
            "entity_id": "CASE-2024-001",
            "relevance": "critical"
        }
    ],
    "commands_executed": 5,
    "custody_chain": [
        {
            "action": "uploaded",
            "by": "analyst@company.com",
            "at": "2024-12-16T08:00:00Z"
        }
    ]
}
```

#### GET `/api/v1/evidence-management/{evidence_id}/download`

Download evidence file.

**Response:** Binary file download

#### GET `/api/v1/evidence-management/{evidence_id}/verify`

Verify evidence integrity by recalculating hash.

**Response:**
```json
{
    "verified": true,
    "message": "Evidence integrity verified successfully"
}
```

### Evidence Associations

#### POST `/api/v1/evidence-management/{evidence_id}/associate`

Associate evidence with a case, agent, user, or event.

**Request:**
```json
{
    "entity_type": "case",
    "entity_id": "CASE-2024-001",
    "association_type": "primary",
    "relevance": "high",
    "notes": "Critical evidence for timeline reconstruction"
}
```

**Response:**
```json
{
    "success": true,
    "association_id": 123,
    "message": "Evidence associated with case:CASE-2024-001"
}
```

#### GET `/api/v1/evidence-management/associations/{entity_type}/{entity_id}`

Get all evidence associated with an entity.

**Example:**
```http
GET /api/v1/evidence-management/associations/case/CASE-2024-001
```

**Response:**
```json
{
    "entity_type": "case",
    "entity_id": "CASE-2024-001",
    "total_evidence": 15,
    "evidences": [...]
}
```

### Command Logs

#### GET `/api/v1/evidence-management/{evidence_id}/commands`

Get all commands executed on evidence.

**Response:**
```json
{
    "evidence_id": "EVD-2024-A1B2C",
    "total_commands": 3,
    "commands": [
        {
            "id": "CMD-2024-ABC123",
            "tool": "volatility",
            "command": "volatility -f memory.dmp windows.pslist",
            "status": "completed",
            "duration_seconds": 45,
            "executed_by": "analyst@company.com"
        }
    ]
}
```

#### GET `/api/v1/evidence-management/case/{case_id}/commands`

Get all commands for a case (essential for traceability).

**Response:**
```json
{
    "case_id": "CASE-2024-001",
    "total_commands": 23,
    "commands": [...]
}
```

### Statistics

#### GET `/api/v1/evidence-management/stats/overview`

Get overview statistics about evidence storage.

**Response:**
```json
{
    "total_evidence": 142,
    "total_size_gb": 512.5,
    "total_commands": 456,
    "total_sources": 8,
    "evidence_by_type": [
        {"type": "disk_image", "count": 45},
        {"type": "memory_dump", "count": 23}
    ],
    "top_tools": [
        {"tool": "Autopsy", "count": 50},
        {"tool": "Volatility", "count": 30}
    ]
}
```

## Billing API

### Usage Tracking

#### GET `/api/v1/billing/usage/summary`

Get usage summary for billing period.

**Query Parameters:**
- `tenant_id` (optional): Filter by tenant
- `user_id` (optional): Filter by user
- `days` (default: 30): Days to look back

**Response:**
```json
{
    "total_api_calls": 1250,
    "total_billable_units": 45.2,
    "usage_by_category": [
        {
            "category": "compute",
            "calls": 800,
            "billable_units": 800.0
        },
        {
            "category": "storage",
            "calls": 200,
            "billable_units": 12.5
        }
    ],
    "top_endpoints": [
        {"endpoint": "/api/v1/m365/analyze", "calls": 400}
    ]
}
```

#### GET `/api/v1/billing/usage/export/{tenant_id}/{year}/{month}`

Export usage for billing platform integration.

**Example:**
```http
GET /api/v1/billing/usage/export/tenant-001/2024/12
```

**Response:**
```json
{
    "tenant_id": "tenant-001",
    "billing_period": "2024-12",
    "usage_summary": {...},
    "invoice_ready": true,
    "generated_at": "2024-12-16T08:00:00Z"
}
```

#### GET `/api/v1/billing/usage/rate-limits/{tenant_id}`

Get current rate limit status.

**Response:**
```json
{
    "tenant_id": "tenant-001",
    "hourly": {
        "used": 45,
        "limit": 1000,
        "remaining": 955,
        "percentage": 4.5
    },
    "daily": {
        "used": 823,
        "limit": 10000,
        "remaining": 9177,
        "percentage": 8.23
    },
    "monthly": {
        "used": 15420,
        "limit": 100000,
        "remaining": 84580,
        "percentage": 15.42
    }
}
```

## Integration Examples

### Python Client Example

```python
import requests

API_BASE = "https://forensics-api.company.com"
API_KEY = "your-api-key"

# Upload evidence
with open("evidence.e01", "rb") as f:
    response = requests.post(
        f"{API_BASE}/api/v1/evidence-management/upload",
        headers={"X-API-Key": API_KEY},
        files={"file": f},
        data={
            "name": "Suspect Laptop Disk Image",
            "evidence_type": "disk_image",
            "source_tool_name": "FTK Imager",
            "collected_by": "analyst@company.com"
        }
    )
    evidence_id = response.json()["evidence_id"]

# Associate with case
requests.post(
    f"{API_BASE}/api/v1/evidence-management/{evidence_id}/associate",
    headers={"X-API-Key": API_KEY},
    json={
        "entity_type": "case",
        "entity_id": "CASE-2024-001",
        "relevance": "critical"
    }
)
```

### Command Logging Example

```python
from api.services.command_logger import log_command_execution

@log_command_execution("volatility", "3.0")
async def analyze_memory(case_id: str, memory_file: str):
    # Your analysis code here
    results = await run_volatility_analysis(memory_file)
    return results

# Command will be automatically logged with:
# - Full command string
# - Start/end timestamps
# - Exit code
# - Output summary
# - Duration
```

## Security Considerations

### Authentication
All endpoints require API key authentication via `X-API-Key` header.

### Tenant Isolation
Evidence is isolated by tenant. Set `X-Tenant-ID` header for multi-tenant environments.

### Data Integrity
- All files are hashed (MD5, SHA1, SHA256) on upload
- Integrity can be verified at any time
- Chain of custody is maintained automatically

### Rate Limiting
API usage is tracked and rate limits are enforced per tenant:
- Hourly limit: 1,000 calls
- Daily limit: 10,000 calls
- Monthly limit: 100,000 calls

### Audit Trail
All operations are logged including:
- Who uploaded evidence
- Who accessed evidence
- All commands executed
- All associations created

## Best Practices

### Evidence Naming
Use descriptive names that include:
- Source system
- Date collected
- Type of evidence
Example: "Laptop-ABC123_2024-12-16_MemoryDump"

### Tagging Strategy
Use consistent tags across cases:
- Incident type: `malware`, `phishing`, `data_breach`
- Analysis stage: `raw`, `analyzed`, `processed`
- Priority: `critical`, `high`, `medium`, `low`

### Chain of Custody
Always include:
- Who collected the evidence
- When it was collected
- Where it was collected from
- Collection method used

### Command Logging
For manual commands, log immediately after execution:
```python
with get_db_context() as db:
    CommandLogger.log_command(
        db=db,
        command="dd if=/dev/sda1 of=disk_image.raw bs=4M",
        tool_name="dd",
        case_id="CASE-2024-001",
        executed_by="analyst@company.com"
    )
```

## Troubleshooting

### Upload Failures
- Check file size limits (default: no limit, but check storage capacity)
- Verify API key permissions
- Ensure Content-Type is multipart/form-data

### Integrity Verification Failures
- File may have been modified after upload
- Check file permissions
- Verify file path exists

### Association Errors
- Ensure entity (case/agent/user) exists before associating
- Verify entity_type is valid: case, agent, user, event, investigation

## Support

For issues or questions:
- GitHub Issues: https://github.com/jcarvajalantigua/mcp-kali-forensics/issues
- Documentation: https://github.com/jcarvajalantigua/mcp-kali-forensics/docs
