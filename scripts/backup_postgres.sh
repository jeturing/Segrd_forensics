#!/bin/bash

# PostgreSQL Backup Script for MCP Kali Forensics
# Automatically backs up the PostgreSQL database

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/mcp-forensics}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/forensics_backup_$TIMESTAMP.sql"

# PostgreSQL Connection (from environment or defaults)
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-forensics}"
PGUSER="${PGUSER:-forensics}"
PGPASSWORD="${PGPASSWORD:-}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting PostgreSQL backup..."
echo "📍 Database: $PGDATABASE@$PGHOST:$PGPORT"
echo "💾 Backup file: $BACKUP_FILE"

# Perform backup
if PGPASSWORD="$PGPASSWORD" pg_dump \
    -h "$PGHOST" \
    -p "$PGPORT" \
    -U "$PGUSER" \
    -d "$PGDATABASE" \
    -F c \
    -f "$BACKUP_FILE"; then
    
    echo "✅ Backup completed successfully"
    
    # Compress backup
    echo "🗜️ Compressing backup..."
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    # Get file size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "📦 Backup size: $SIZE"
    
    # Clean old backups
    echo "🧹 Cleaning backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "forensics_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
    
    # Count remaining backups
    COUNT=$(find "$BACKUP_DIR" -name "forensics_backup_*.sql.gz" -type f | wc -l)
    echo "📊 Total backups: $COUNT"
    
    echo "✅ Backup process completed"
    echo "💾 Backup location: $BACKUP_FILE"
    
    # Optional: Upload to S3 or other cloud storage
    # aws s3 cp "$BACKUP_FILE" "s3://your-bucket/backups/"
    
else
    echo "❌ Backup failed!"
    exit 1
fi
