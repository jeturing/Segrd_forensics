# BRAC Installation Quick Start

## ⚡ Quick Installation (3 Minutes)

### Step 1: Install Dependencies

```bash
cd /path/to/mcp-kali-forensics
pip install -r requirements.txt
```

### Step 2: Run Interactive Installer

```bash
python3 scripts/install_brac.py
```

The installer will prompt you to confirm, then:
- ✅ Initialize database schema
- ✅ Create 4 default roles (viewer, analyst, senior_analyst, admin)
- ✅ Create global tenant "jeturing"
- ✅ Create admin user "Pluton_JE"
- ✅ Generate random deployment key
- ✅ Configure JWT secret

### Step 3: Save Deployment Key

**IMPORTANT**: The installer displays a deployment key like:

```
🔑 DEPLOYMENT KEY (SAVE THIS - WON'T BE SHOWN AGAIN):

   4hLReeBSGrGz2ZZnu8VZrMqDbrxa0UoZAnyE_GE2ob8

⚠️  Use this key for first login:
   Username: Pluton_JE
   Password: 4hLReeBSGrGz2ZZnu8VZrMqDbrxa0UoZAnyE_GE2ob8
```

**Save this key immediately!** It's also saved to `.deployment_key` (file is gitignored).

### Step 4: Start Server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: First Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "Pluton_JE",
    "password": "YOUR_DEPLOYMENT_KEY_HERE"
  }'
```

Or visit: http://localhost:8000/docs and use the interactive API explorer.

### Step 6: Change Password (RECOMMENDED)

```bash
curl -X PUT http://localhost:8000/api/auth/me/password \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "YOUR_DEPLOYMENT_KEY",
    "new_password": "NewSecurePassword123!"
  }'
```

---

## 🎯 Post-Installation Tasks

### Create Additional Users

```bash
# As Pluton_JE (admin), create new users
curl -X POST http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst1",
    "email": "analyst1@company.com",
    "password": "TempPassword123!",
    "full_name": "Jane Doe",
    "roles": ["analyst"]
  }'
```

### Onboard New Tenants

```bash
# Create tenant for customer organization
curl -X POST http://localhost:8000/tenants/onboard \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "tenant_id": "acme-tenant-uuid",
    "client_id": "azure-app-client-id",
    "client_secret": "azure-app-secret"
  }'
```

### Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Check auth status
curl http://localhost:8000/api/auth/roles \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## 🔧 Configuration Options

### Environment Variables

Edit `.env`:

```bash
# JWT Configuration
JWT_SECRET_KEY=auto-generated-by-installer

# Database (SQLite by default)
DATABASE_URL=sqlite:///./forensics.db

# Enable RBAC
RBAC_ENABLED=true
RBAC_DEFAULT_ROLE=analyst

# Optional: Switch to PostgreSQL
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/forensics
```

### User Configurable in .env

According to requirements, you should be able to change the admin username in `.env`:

Add to `.env`:

```bash
# BRAC Initial Admin User
BRAC_ADMIN_USERNAME=Pluton_JE
BRAC_ADMIN_EMAIL=pluton@jeturing.local
```

Then update `api/services/init_brac.py` to read from settings.

---

## 📚 Next Steps

1. **Read Full Documentation**: [BRAC_AUTHENTICATION_GUIDE.md](./BRAC_AUTHENTICATION_GUIDE.md)
2. **API Explorer**: http://localhost:8000/docs
3. **Create Users**: Use `/api/auth/users` endpoint
4. **Onboard Tenants**: Use `/tenants/onboard` endpoint
5. **Deploy Agents**: The Pluton_JE user can deploy other agents/tenants

---

## 🚨 Troubleshooting

### Installer Fails

```bash
# Check prerequisites
python3 --version  # Must be 3.8+
pip list | grep -E "(sqlalchemy|fastapi|pyjwt|bcrypt)"

# Re-run with verbose output
python3 scripts/install_brac.py 2>&1 | tee install.log
```

### Lost Deployment Key

```bash
# Check saved file
cat .deployment_key

# Or reset password manually
python3 << EOF
from api.database import SessionLocal
from api.models.user import User

db = SessionLocal()
admin = db.query(User).filter(User.username == "Pluton_JE").first()
admin.set_password("new_password_here")
admin.is_locked = False
admin.failed_login_attempts = 0
db.commit()
print("✅ Password reset")
EOF
```

### Database Already Initialized

If you see "Admin user already exists":

```bash
# This is normal - the installer is idempotent
# Your existing admin user was preserved
# No deployment key will be shown (use existing password)
```

---

## 🔐 Security Notes

### Production Deployment

1. **Change default admin password immediately**
2. **Use HTTPS** - Never send tokens over HTTP
3. **Rotate JWT secret** - Update `JWT_SECRET_KEY` periodically
4. **Enable database encryption** - For PostgreSQL production
5. **Monitor audit logs** - Check `user_audit_logs` table daily

### Backup Critical Data

```bash
# Backup deployment key
cp .deployment_key ~/secure-backup/

# Backup database (SQLite)
cp forensics.db ~/secure-backup/forensics-$(date +%Y%m%d).db

# Backup .env
cp .env ~/secure-backup/.env.backup
```

---

## 📞 Support

- **Full Guide**: [BRAC_AUTHENTICATION_GUIDE.md](./BRAC_AUTHENTICATION_GUIDE.md)
- **API Docs**: http://localhost:8000/docs
- **Issues**: https://github.com/jcarvajalantigua/mcp-kali-forensics/issues

---

**Installation Time**: ~3 minutes  
**Difficulty**: Easy ⭐  
**Version**: 4.5.0  
**Status**: ✅ Production Ready
