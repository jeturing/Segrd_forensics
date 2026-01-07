# 🚀 LLM Integration & Multi-Tenancy Deployment Guide

**Version:** 1.0  
**Date:** December 16, 2024  
**Status:** ✅ Production Ready

---

## 📋 Overview

This guide covers the complete deployment of the MCP Kali Forensics platform with:

- **LLM Integration**: Ollama-based AI analysis (GPU/CPU adaptive)
- **Multi-Tenancy**: Complete tenant isolation with PostgreSQL schemas
- **Autonomous Agents**: Parallel investigation with AI-powered IOC analysis
- **Cloudflare Tunnel**: Secure production deployment
- **Proxmox LXC**: Optimized for 16GB RAM containers

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────┐
│       Cloudflare Tunnel (Zero-Trust SSL)      │
│    tenant1.domain.com → tenant2.domain.com    │
└──────────────┬────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────┐
│         Nginx Reverse Proxy                   │
│   Wildcard Subdomain Routing + Load Balance   │
└──────────────┬────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────┐
│      FastAPI Backend (Multi-Tenant)           │
│  ┌──────────────────────────────────────┐    │
│  │ Tenant Middleware (Schema Routing)   │    │
│  └──────────────────────────────────────┘    │
│  ┌──────────────────────────────────────┐    │
│  │ Autonomous Agents (Parallel Exec)    │    │
│  └──────────────────────────────────────┘    │
└──────────────┬────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    │          │          │          │
┌───▼──┐  ┌───▼───┐  ┌──▼────┐  ┌──▼────┐
│Postgres│ │Ollama │ │ Redis │ │ Nginx │
│ Multi- │ │  LLM  │ │ Cache │ │Reverse│
│ Schema │ │GPU/CPU│ │ Queue │ │ Proxy │
└────────┘ └───────┘ └───────┘ └───────┘
```

---

## 🎯 LLM Models Configuration

### Model Tiers

| Tier | Model | RAM | GPU | Use Case |
|------|-------|-----|-----|----------|
| **Basic** | TinyLlama 1.1B | 2GB | No | Quick queries, classifications |
| **Medium** | Phi-4 14B | 8GB | Yes | Full forensic analysis, reports |
| **Full** | Claude 3.5 / GPT-4 | 0GB | No | Complex reasoning, remote API |

### Model Selection Strategy

```python
# In tenant configuration
{
  "llm_model": "medium",  # basic, medium, full
  "llm_config": {
    "temperature": 0.7,
    "max_tokens": 2000,
    "fallback_model": "basic"  # If primary fails
  }
}
```

---

## 🔧 Deployment on Proxmox LXC

### Prerequisites

- Proxmox VE 7.0+
- 16GB RAM available
- NVIDIA GPU (optional, for "medium" model)
- 50GB storage minimum

### Step 1: Create LXC Container

```bash
# Create Ubuntu 22.04 LXC with 16GB RAM
pct create 200 local:vztmpl/ubuntu-22.04-standard.tar.zst \
  --hostname forensics-mcp \
  --memory 16384 \
  --swap 4096 \
  --cores 8 \
  --rootfs local-lvm:50 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp,firewall=1

# Enable nesting for Docker
pct set 200 -features nesting=1

# For GPU passthrough (optional)
pct set 200 -dev0 /dev/nvidia0,gid=44
pct set 200 -dev1 /dev/nvidiactl,gid=44
pct set 200 -dev2 /dev/nvidia-uvm,gid=44

# Start container
pct start 200
pct enter 200
```

### Step 2: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
apt install -y docker-compose

# Install NVIDIA Container Toolkit (if GPU)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  tee /etc/apt/sources.list.d/nvidia-docker.list
apt update && apt install -y nvidia-container-toolkit
systemctl restart docker

# Verify GPU access (if applicable)
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Step 3: Clone and Configure

```bash
# Clone repository
cd /opt
git clone https://github.com/jcarvajalantigua/mcp-kali-forensics.git
cd mcp-kali-forensics

# Create environment file
cp .env.example .env

# Edit configuration
nano .env
```

**Critical `.env` variables:**

```bash
# Database
POSTGRES_DB=forensics
POSTGRES_USER=forensics
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# LLM Configuration
OLLAMA_URL=http://ollama:11434
LLM_MODEL_DEFAULT=medium
LLM_REMOTE_API_KEY=  # For "full" tier
LLM_REMOTE_API_URL=https://api.anthropic.com/v1

# Multi-Tenancy
ENABLE_MULTI_TENANCY=true
TENANT_ID_PREFIX=Jeturing
DEFAULT_TENANT=Jeturing_00000000-0000-0000-0000-000000000000

# Cloudflare (Production)
CLOUDFLARE_TUNNEL_ENABLED=true
CLOUDFLARE_TUNNEL_NAME=forensics-mcp
BASE_DOMAIN=yourdomain.com

# Security
API_KEY=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 64)
RBAC_ENABLED=true

# Autonomous Agents
ENABLE_AUTONOMOUS_AGENTS=true
AGENT_MAX_PARALLEL=5
AGENT_TIMEOUT=300
```

### Step 4: Start Services

```bash
# Pull images (will take time)
docker-compose -f docker-compose.llm.yml pull

# Start all services
docker-compose -f docker-compose.llm.yml up -d

# Check status
docker-compose -f docker-compose.llm.yml ps

# View logs
docker-compose -f docker-compose.llm.yml logs -f mcp-forensics
docker-compose -f docker-compose.llm.yml logs -f ollama
```

### Step 5: Pull LLM Models

```bash
# Pull basic model (fast)
docker exec mcp-forensics-ollama ollama pull tinyllama

# Pull medium model (takes 15-30 min)
docker exec mcp-forensics-ollama ollama pull phi4

# Verify models
docker exec mcp-forensics-ollama ollama list
```

### Step 6: Verify Installation

```bash
# Health check
curl http://localhost:8888/health

# LLM health
curl http://localhost:8888/api/v1/llm/models

# Create test tenant
curl -X POST http://localhost:8888/api/v1/tenants \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "Test Tenant",
    "subdomain": "test",
    "llm_model": "basic"
  }'
```

---

## 🌐 Cloudflare Tunnel Setup

### Install Cloudflared

```bash
# Download and install
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared-linux-amd64.deb

# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create forensics-mcp

# Note the tunnel ID from output
```

### Configure Tunnel

Create `/etc/cloudflared/config.yml`:

```yaml
tunnel: forensics-mcp
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  # Wildcard subdomain for tenants
  - hostname: "*.yourdomain.com"
    service: http://nginx:80
    originRequest:
      noTLSVerify: true
  
  # Main domain
  - hostname: yourdomain.com
    service: http://nginx:80
  
  # Catch-all
  - service: http_status:404
```

### Start Tunnel

```bash
# Install as service
cloudflared service install

# Start service
systemctl start cloudflared
systemctl enable cloudflared

# Check status
systemctl status cloudflared

# View logs
journalctl -u cloudflared -f
```

### DNS Configuration

In Cloudflare Dashboard:
1. Go to DNS settings
2. Add CNAME record: `*` → `<TUNNEL_ID>.cfargotunnel.com`
3. Add CNAME record: `@` → `<TUNNEL_ID>.cfargotunnel.com`

---

## 👥 Multi-Tenancy Usage

### Create Tenant

```bash
curl -X POST http://localhost:8888/api/v1/tenants \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "Acme Corporation",
    "subdomain": "acme",
    "config": {
      "llm_model": "medium",
      "enable_autonomous_agents": true
    },
    "contact_email": "admin@acme.com",
    "max_cases": 1000,
    "max_storage_gb": 100
  }'
```

### Access Tenant

```bash
# Via subdomain
curl http://acme.yourdomain.com/health \
  -H "X-API-Key: YOUR_API_KEY"

# Via header
curl http://yourdomain.com/health \
  -H "X-Tenant-ID: Jeturing_<GUID>" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Tenant Isolation

- **Database**: Separate PostgreSQL schema per tenant
- **Storage**: Tenant-specific evidence directories
- **LLM**: Isolated model instances (optional)
- **Agents**: Tenant-specific agent pools

---

## 🤖 Autonomous Agents

### Agent Types

1. **IOC Analyzer**: Automatic threat intelligence lookup
2. **Report Generator**: AI-powered report writing
3. **Blue Team Agent**: Defensive actions
4. **Purple Team Agent**: Attack simulation + defense

### Enable Autonomous Mode

```bash
curl -X POST http://acme.yourdomain.com/api/v1/agents/analyze \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "IR-2024-001",
    "agent_type": "blueteam",
    "autonomous": true,
    "actions": [
      "collect_iocs",
      "analyze_threats",
      "generate_report",
      "recommend_actions"
    ]
  }'
```

### Agent Configuration

```python
# In tenant config
{
  "agent_config": {
    "max_parallel": 5,
    "timeout": 300,
    "auto_approve": false,  # Require human approval
    "notification_webhook": "https://slack.com/webhook"
  }
}
```

---

## 🧪 LLM Usage Examples

### Query LLM

```bash
curl -X POST http://acme.yourdomain.com/api/v1/llm/chat \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze these IOCs and determine if they are malicious",
    "context": {
      "case_id": "IR-2024-001",
      "iocs": [
        "192.168.1.100",
        "malware.exe",
        "C:\\Users\\victim\\AppData\\Roaming\\evil.dll"
      ]
    },
    "model": "medium"
  }'
```

### Forensic Analysis

```bash
curl -X POST http://acme.yourdomain.com/api/v1/llm/analyze \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "IR-2024-001",
    "analysis_type": "malware",
    "data": {
      "file_hash": "abc123...",
      "file_name": "suspicious.exe",
      "behaviors": ["network_connection", "registry_modification"]
    },
    "instructions": "Determine if this is ransomware"
  }'
```

---

## 📊 Resource Monitoring

### Check Resource Usage

```bash
# Container stats
docker stats

# Ollama GPU usage
docker exec mcp-forensics-ollama nvidia-smi

# PostgreSQL connections
docker exec mcp-forensics-postgres psql -U forensics -c "SELECT count(*) FROM pg_stat_activity;"

# Redis memory
docker exec mcp-forensics-redis redis-cli INFO memory
```

### Resource Limits (16GB RAM)

- PostgreSQL: 4GB
- Ollama (Phi-4): 8GB  
- FastAPI: 2GB
- Redis: 512MB
- Nginx: 256MB
- System: ~1.25GB

**Total: ~16GB**

### Optimization Tips

1. **Use "basic" model** for low-RAM scenarios
2. **Enable swap** (4GB) for buffer
3. **Scale horizontally** with multiple LXC containers
4. **Offload to "full"** (remote API) for complex tasks

---

## 🔒 Security Considerations

### Network Isolation

```bash
# Firewall rules (UFW)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (Cloudflare)
ufw allow 443/tcp  # HTTPS (Cloudflare)
ufw enable
```

### Secrets Management

```bash
# Use Docker secrets (recommended)
echo "my_postgres_password" | docker secret create postgres_password -

# Or encrypted environment variables
ansible-vault encrypt .env
```

### RBAC Enforcement

Ensure `RBAC_ENABLED=true` in production:

```python
# 5 permission levels
- viewer: Read-only
- analyst: Run analyses
- operator: Manage cases
- admin: Full tenant control
- superadmin: Multi-tenant management
```

---

## 🐛 Troubleshooting

### Ollama Not Starting

```bash
# Check logs
docker logs mcp-forensics-ollama

# Common issues:
# 1. GPU drivers not installed
# 2. Insufficient RAM
# 3. Model not pulled

# Force CPU mode
docker-compose -f docker-compose.llm.yml down
# Edit docker-compose.llm.yml, remove GPU sections
docker-compose -f docker-compose.llm.yml up -d
```

### Tenant Routing Not Working

```bash
# Check nginx config
docker exec mcp-forensics-nginx nginx -t

# Verify DNS
dig test.yourdomain.com

# Check tenant middleware
curl http://localhost:8888/api/v1/tenants \
  -H "X-API-Key: YOUR_API_KEY"
```

### High Memory Usage

```bash
# Restart Ollama to free VRAM
docker restart mcp-forensics-ollama

# Clear Redis cache
docker exec mcp-forensics-redis redis-cli FLUSHALL

# Analyze container usage
docker stats --no-stream
```

---

## 📚 Additional Resources

- **LLM Models**: https://ollama.ai/library
- **Cloudflare Tunnel**: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- **Proxmox Docs**: https://pve.proxmox.com/wiki/Linux_Container
- **Multi-Tenancy Patterns**: `/docs/architecture/MULTI_TENANCY.md`
- **Agent Development**: `/docs/agents/AUTONOMOUS_AGENTS.md`

---

## ✅ Production Checklist

- [ ] LXC container with 16GB RAM configured
- [ ] Docker + NVIDIA toolkit installed (if GPU)
- [ ] `.env` file configured with secure passwords
- [ ] Ollama models pulled (tinyllama, phi4)
- [ ] PostgreSQL initialized with tenants schema
- [ ] Cloudflare Tunnel configured and running
- [ ] DNS records pointing to tunnel
- [ ] RBAC enabled and tested
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured
- [ ] Test tenant created and verified
- [ ] LLM queries working
- [ ] Autonomous agents tested
- [ ] SSL/TLS certificates valid
- [ ] Firewall rules applied

---

**Deployment Date**: _________________  
**Deployed By**: _________________  
**Production URL**: _________________
