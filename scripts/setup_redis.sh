#!/bin/bash
# =============================================================================
# 🚀 Redis Installation & Configuration Script
# Instala Redis para cache de Threat Intelligence
# =============================================================================

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                   📦 REDIS CACHE SETUP                                ║"
echo "║                    MCP Kali Forensics                                 ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script requires sudo privileges"
    echo "   Re-running with sudo..."
    sudo "$0" "$@"
    exit
fi

# =============================================================================
# 1. Install Redis Server
# =============================================================================

echo "📦 Installing Redis Server..."
apt-get update -qq
apt-get install -y redis-server redis-tools

# Check installation
if command -v redis-server &> /dev/null; then
    echo "✅ Redis server installed: $(redis-server --version)"
else
    echo "❌ Redis installation failed"
    exit 1
fi

# =============================================================================
# 2. Configure Redis
# =============================================================================

echo ""
echo "⚙️  Configuring Redis..."

# Backup original config
if [ ! -f /etc/redis/redis.conf.backup ]; then
    cp /etc/redis/redis.conf /etc/redis/redis.conf.backup
    echo "   Backup created: /etc/redis/redis.conf.backup"
fi

# Configure Redis for local development
cat > /etc/redis/redis.conf.mcp << 'EOF'
# Redis Configuration for MCP Kali Forensics
# Optimized for Threat Intelligence caching

# Network
bind 127.0.0.1
port 6379
protected-mode yes

# General
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log

# Performance
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Memory Management
maxmemory 512mb
maxmemory-policy allkeys-lru  # Evict least recently used keys

# Snapshotting
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Slow Log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Latency monitoring
latency-monitor-threshold 100
EOF

# Apply configuration
cp /etc/redis/redis.conf.mcp /etc/redis/redis.conf
echo "✅ Redis configuration applied"

# =============================================================================
# 3. Start Redis Service
# =============================================================================

echo ""
echo "🚀 Starting Redis service..."

systemctl enable redis-server
systemctl restart redis-server
sleep 2

# Check if Redis is running
if systemctl is-active --quiet redis-server; then
    echo "✅ Redis is running"
else
    echo "❌ Redis failed to start"
    systemctl status redis-server
    exit 1
fi

# Test connection
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis connection test: OK"
else
    echo "❌ Redis connection test failed"
    exit 1
fi

# =============================================================================
# 4. Install Python Redis Client
# =============================================================================

echo ""
echo "🐍 Installing Python Redis client..."

# Detect if in virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "   Using virtual environment: $VIRTUAL_ENV"
    pip install redis[hiredis] --quiet
else
    echo "   Installing globally (consider using venv)"
    pip3 install redis[hiredis] --quiet
fi

# Verify installation
if python3 -c "import redis" 2>/dev/null; then
    echo "✅ Python redis module installed"
else
    echo "❌ Python redis module installation failed"
    exit 1
fi

# =============================================================================
# 5. Display Status
# =============================================================================

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                   ✅ REDIS SETUP COMPLETE                             ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Redis Status:"
echo "   Service: $(systemctl is-active redis-server)"
echo "   Memory: $(redis-cli info memory | grep used_memory_human | cut -d: -f2)"
echo "   Keys: $(redis-cli dbsize | cut -d' ' -f2)"
echo "   Port: 6379"
echo ""
echo "🔧 Useful Commands:"
echo "   Check status:  systemctl status redis-server"
echo "   View logs:     tail -f /var/log/redis/redis-server.log"
echo "   CLI access:    redis-cli"
echo "   Monitor:       redis-cli monitor"
echo "   Flush cache:   redis-cli FLUSHDB"
echo ""
echo "📝 Next Steps:"
echo "   1. Set REDIS_ENABLED=true in .env"
echo "   2. Restart backend: pkill -f uvicorn && uvicorn api.main:app --reload"
echo "   3. Check cache stats: curl http://localhost:8888/api/threat-intel/cache/stats"
echo ""
