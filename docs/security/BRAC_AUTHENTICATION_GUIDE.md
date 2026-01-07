# BRAC Authentication System - Complete Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [User Management](#user-management)
6. [Tenant Management](#tenant-management)
7. [API Reference](#api-reference)
8. [Security Features](#security-features)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The BRAC (Base Roles and Claims) authentication system provides enterprise-grade authentication and authorization for MCP Kali Forensics with multi-tenant support.

### Key Features

- ✅ JWT-based authentication (access + refresh tokens)
- ✅ Bcrypt password hashing
- ✅ Multi-tenant user management
- ✅ Role-based permissions (RBAC integration)
- ✅ Session tracking and management
- ✅ Audit logging for security events
- ✅ Account lockout after failed login attempts
- ✅ SQLite and PostgreSQL support

### Default Roles

| Role | Permissions | Description |
|------|-------------|-------------|
| **viewer** | READ | Read-only access to cases and reports |
| **analyst** | READ, WRITE, RUN_TOOLS, VIEW_LOGS | Standard forensic analyst |
| **senior_analyst** | READ, WRITE, DELETE, RUN_TOOLS, MANAGE_AGENTS, VIEW_LOGS, EXPORT, PENTEST | Advanced analyst with full capabilities |
| **admin** | ALL | Full system administrator |

### Global Tenant: jeturing

The system includes a global master tenant named **"jeturing"** for system-level administration. The initial admin user is **Pluton_JE**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   BRAC Authentication Flow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Client                                                         │
│     │                                                            │
│     ├── POST /api/auth/login                                    │
│     │   { username, password }                                  │
│     │                                                            │
│     ▼                                                            │
│   AuthService                                                    │
│     ├── Validate credentials                                     │
│     ├── Check account status (active, locked)                   │
│     ├── Verify password (bcrypt)                                │
│     ├── Generate JWT tokens                                      │
│     └── Create session                                           │
│     │                                                            │
│     ▼                                                            │
│   Response                                                       │
│     ├── access_token (1 hour)                                   │
│     ├── refresh_token (30 days)                                 │
│     └── user profile                                            │
│     │                                                            │
│     ▼                                                            │
│   Subsequent Requests                                            │
│     ├── Authorization: Bearer <access_token>                    │
│     ├── RBAC Middleware validates token                         │
│     ├── Check permissions for route                             │
│     └── Allow or Deny                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_global_admin BOOLEAN DEFAULT FALSE,
    failed_login_attempts INTEGER DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    permissions JSON,
    is_system BOOLEAN DEFAULT FALSE
);

-- User-Tenant association
CREATE TABLE user_tenants (
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- User-Role association
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    tenant_id UUID REFERENCES tenants(id) NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Audit logs
CREATE TABLE user_audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    action VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    details JSON,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Installation

### Prerequisites

- Python 3.8+
- SQLite or PostgreSQL
- All requirements installed: `pip install -r requirements.txt`

### Quick Start

Run the interactive installer:

```bash
python3 scripts/install_brac.py
```

The installer will:
1. Check prerequisites
2. Initialize database schema
3. Create default roles (viewer, analyst, senior_analyst, admin)
4. Create global tenant "jeturing"
5. Create admin user "Pluton_JE" with a random deployment key
6. Configure JWT secret key in `.env`

### Sample Output

```
======================================================================
🎉 BRAC AUTHENTICATION SYSTEM INITIALIZED SUCCESSFULLY!
======================================================================

📋 Global Tenant: jeturing
   Tenant ID: jeturing

👤 Admin User: Pluton_JE
   Email: pluton@jeturing.local

🔑 DEPLOYMENT KEY (SAVE THIS - WON'T BE SHOWN AGAIN):

   4hLReeBSGrGz2ZZnu8VZrMqDbrxa0UoZAnyE_GE2ob8

⚠️  Use this key for first login:
   Username: Pluton_JE
   Password: 4hLReeBSGrGz2ZZnu8VZrMqDbrxa0UoZAnyE_GE2ob8
```

**Important:** Save the deployment key - it won't be shown again!

### Manual Installation

If you prefer manual setup:

```python
from api.services.init_brac import init_brac_system

result = init_brac_system()
print(result['deployment_key'])
```

---

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# JWT Secret (auto-generated by installer)
JWT_SECRET_KEY=your-secret-key-here

# Database (auto-detected)
DATABASE_URL=sqlite:///./forensics.db
# OR
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/forensics

# RBAC (already configured)
RBAC_ENABLED=true
RBAC_DEFAULT_ROLE=analyst
```

### Token Configuration

Edit `api/services/auth.py` to customize:

```python
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60   # 1 hour
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30     # 30 days
```

### Password Policies

Edit `api/services/auth.py`:

```python
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_MINUTES = 30
```

---

## User Management

### First Login

Use the deployment key shown during installation:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "Pluton_JE",
    "password": "YOUR_DEPLOYMENT_KEY_HERE"
  }'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "username": "Pluton_JE",
    "email": "pluton@jeturing.local",
    "is_global_admin": true,
    "roles": ["admin"]
  }
}
```

### Change Password

After first login, change your password:

```bash
curl -X PUT http://localhost:8000/api/auth/me/password \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "YOUR_DEPLOYMENT_KEY",
    "new_password": "new_secure_password_123"
  }'
```

### Create New Users (Admin Only)

```bash
curl -X POST http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst1",
    "email": "analyst1@company.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "roles": ["analyst"]
  }'
```

### Assign Roles to Users

```bash
curl -X POST http://localhost:8000/api/auth/roles/assign \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "uuid-of-user",
    "role_name": "senior_analyst",
    "tenant_id": "optional-tenant-id"
  }'
```

### List All Users

```bash
curl http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Deactivate User Account

```bash
curl -X PUT http://localhost:8000/api/auth/users/{user_id}/deactivate \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Tenant Management

### Associate User with Tenant

Users can be associated with multiple tenants:

```python
from api.database import SessionLocal
from api.models.user import User
from api.models.tenant import Tenant

db = SessionLocal()

user = db.query(User).filter(User.username == "analyst1").first()
tenant = db.query(Tenant).filter(Tenant.name == "customer_org").first()

user.tenants.append(tenant)
db.commit()
```

### Tenant-Specific Login

When logging in, optionally specify a tenant:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst1",
    "password": "password123",
    "tenant_id": "customer_tenant_id"
  }'
```

This scopes the JWT token to that specific tenant.

---

## API Reference

### Authentication Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/api/auth/login` | POST | No | Login with username/password |
| `/api/auth/register` | POST | No | Register new user (if enabled) |
| `/api/auth/refresh` | POST | No | Refresh access token |
| `/api/auth/logout` | POST | Yes | Invalidate current session |
| `/api/auth/me` | GET | Yes | Get current user info |
| `/api/auth/me/password` | PUT | Yes | Change password |
| `/api/auth/sessions` | GET | Yes | List active sessions |
| `/api/auth/sessions/{id}` | DELETE | Yes | Revoke specific session |

### Admin Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/api/auth/users` | GET | Admin | List all users |
| `/api/auth/users` | POST | Admin | Create new user |
| `/api/auth/users/{id}` | GET | Admin | Get user details |
| `/api/auth/users/{id}/activate` | PUT | Admin | Activate user |
| `/api/auth/users/{id}/deactivate` | PUT | Admin | Deactivate user |
| `/api/auth/roles` | GET | Admin | List all roles |
| `/api/auth/roles/assign` | POST | Admin | Assign role to user |

### Request/Response Examples

#### Login Request

```json
POST /api/auth/login
{
  "username": "analyst1",
  "password": "SecurePass123!",
  "tenant_id": "optional_tenant_id"
}
```

#### Login Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "analyst1",
    "email": "analyst1@company.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_global_admin": false,
    "roles": [
      {
        "id": "role-uuid",
        "name": "analyst"
      }
    ],
    "tenants": [
      {
        "id": "tenant-uuid",
        "name": "customer_org"
      }
    ]
  }
}
```

---

## Security Features

### Password Security

- ✅ Minimum 8 characters required
- ✅ Bcrypt hashing with random salt
- ✅ Password change forces session invalidation
- ✅ Password history tracking (password_changed_at)

### Account Protection

- ✅ **Auto-lockout**: 5 failed login attempts locks account for 30 minutes
- ✅ **Session expiration**: Access tokens expire after 1 hour
- ✅ **Refresh token rotation**: Can be configured for enhanced security
- ✅ **IP tracking**: All sessions tracked with IP address
- ✅ **User agent logging**: Device/browser information captured

### Audit Logging

All authentication events are logged:

```python
# Logged events
- login_success
- login_failed
- password_changed
- account_locked
- account_unlocked
- session_created
- session_revoked
- permission_denied
```

Query audit logs:

```python
from api.models.user import UserAuditLog

logs = db.query(UserAuditLog).filter(
    UserAuditLog.user_id == user_id,
    UserAuditLog.event_type == "login_failed"
).order_by(UserAuditLog.created_at.desc()).all()
```

### JWT Token Structure

Access tokens include:

```json
{
  "sub": "user_id",
  "username": "analyst1",
  "email": "analyst1@company.com",
  "is_global_admin": false,
  "tenant_id": "optional_tenant_id",
  "roles": ["analyst"],
  "permissions": ["mcp:read", "mcp:write", "mcp:run-tools"],
  "exp": 1234567890,
  "iat": 1234564290,
  "type": "access"
}
```

---

## Troubleshooting

### Common Issues

#### 1. "Invalid or expired token"

**Cause**: Access token has expired (1 hour lifetime)  
**Solution**: Use refresh token to get a new access token:

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

#### 2. "Account is locked"

**Cause**: 5 failed login attempts  
**Solution**: Wait 30 minutes or have an admin unlock:

```bash
curl -X PUT http://localhost:8000/api/auth/users/{user_id}/activate \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

#### 3. "User already exists"

**Cause**: Username or email is already registered  
**Solution**: Use a different username/email or contact admin

#### 4. "Insufficient permissions"

**Cause**: User role doesn't have required permissions  
**Solution**: Admin must assign appropriate role:

```bash
curl -X POST http://localhost:8000/api/auth/roles/assign \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"user_id": "...", "role_name": "analyst"}'
```

### Debugging

Enable debug logging:

```python
# In api/config.py
DEBUG = True

# Check logs
tail -f logs/mcp-forensics.log | grep -E "(login|auth|token)"
```

### Reset Admin Password

If you lose the admin password:

```python
python3 << EOF
from api.database import SessionLocal
from api.models.user import User

db = SessionLocal()
admin = db.query(User).filter(User.username == "Pluton_JE").first()
admin.set_password("new_password_here")
db.commit()
print("Password reset successfully")
EOF
```

### Check User Status

```python
python3 << EOF
from api.database import SessionLocal
from api.models.user import User

db = SessionLocal()
user = db.query(User).filter(User.username == "analyst1").first()

print(f"Active: {user.is_active}")
print(f"Locked: {user.is_locked}")
print(f"Failed attempts: {user.failed_login_attempts}")
print(f"Last login: {user.last_login}")
EOF
```

---

## Best Practices

### Security

1. **Rotate JWT secret regularly** - Update `JWT_SECRET_KEY` periodically
2. **Use HTTPS in production** - Never send tokens over HTTP
3. **Implement token rotation** - Rotate refresh tokens on use
4. **Monitor audit logs** - Review authentication events daily
5. **Strong passwords** - Enforce password complexity policies

### User Management

1. **Principle of least privilege** - Assign minimum required role
2. **Regular audits** - Review user permissions quarterly
3. **Deactivate unused accounts** - Clean up inactive users
4. **Multi-factor authentication** - Consider adding MFA (future enhancement)

### Operations

1. **Backup deployment keys** - Store in secure location
2. **Document role assignments** - Maintain role matrix
3. **Test authentication flows** - Verify login/logout regularly
4. **Monitor failed logins** - Alert on suspicious activity

---

## Future Enhancements

Planned features:

- [ ] Multi-factor authentication (MFA)
- [ ] OAuth2/OIDC integration
- [ ] Password complexity rules (uppercase, numbers, symbols)
- [ ] Password expiration policies
- [ ] User invitation system with email verification
- [ ] API key management for programmatic access
- [ ] Web-based onboarding wizard
- [ ] Role hierarchy and inheritance
- [ ] Tenant-scoped API keys

---

## Support

For issues or questions:

- **Documentation**: `/docs` endpoint
- **API Explorer**: `http://localhost:8000/docs`
- **Logs**: `logs/mcp-forensics.log`
- **GitHub Issues**: https://github.com/jcarvajalantigua/mcp-kali-forensics/issues

---

**Last Updated**: 2025-12-16  
**Version**: 4.5.0  
**Status**: ✅ Production Ready
