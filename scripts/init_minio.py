#!/usr/bin/env python3
"""
init_minio.py - Inicializa bucket y estructura de tenants en MinIO

Uso:
    python3 scripts/init_minio.py
    python3 scripts/init_minio.py --create-tenant tenant-acme-corp
"""

import argparse
import io
import sys

from minio import Minio
from minio.error import S3Error
from minio.versioningconfig import VersioningConfig
from minio.commonconfig import ENABLED

# Configuración MinIO
MINIO_ENDPOINT = "10.10.10.5:9000"
MINIO_ACCESS_KEY = "Jeturing"
MINIO_SECRET_KEY = "Prd-11lkm41231jn123j1n2l3"
MINIO_BUCKET = "forensics-evidence"
MINIO_SECURE = False


def get_client() -> Minio:
    """Crea cliente MinIO."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def init_bucket(client: Minio) -> bool:
    """Inicializa el bucket principal con versionado."""
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            print(f"✅ Bucket '{MINIO_BUCKET}' created")
            
            # Habilitar versionado
            client.set_bucket_versioning(MINIO_BUCKET, VersioningConfig(ENABLED))
            print(f"📚 Versioning enabled for '{MINIO_BUCKET}'")
        else:
            print(f"✅ Bucket '{MINIO_BUCKET}' already exists")
        
        return True
        
    except S3Error as e:
        print(f"❌ Error creating bucket: {e}")
        return False


def create_system_structure(client: Minio) -> bool:
    """Crea estructura de carpetas del sistema."""
    system_folders = [
        "_system/templates/",
        "_system/shared-iocs/",
        "_system/backups/",
        "_system/config/",
    ]
    
    try:
        for folder in system_folders:
            client.put_object(
                MINIO_BUCKET,
                f"{folder}.keep",
                io.BytesIO(b""),
                0,
                content_type="application/x-empty"
            )
            print(f"📁 Created: {folder}")
        
        return True
        
    except S3Error as e:
        print(f"❌ Error creating system structure: {e}")
        return False


def create_tenant_structure(client: Minio, tenant_id: str) -> bool:
    """Crea estructura de carpetas para un tenant."""
    folders = [
        f"{tenant_id}/cases/",
        f"{tenant_id}/scans/",
        f"{tenant_id}/exports/",
        f"{tenant_id}/m365_graph/",
        f"{tenant_id}/threat_intel/",
        f"{tenant_id}/pentest/",
        f"{tenant_id}/reports/",
    ]
    
    try:
        for folder in folders:
            client.put_object(
                MINIO_BUCKET,
                f"{folder}.keep",
                io.BytesIO(b""),
                0,
                content_type="application/x-empty"
            )
            print(f"📁 Created: {folder}")
        
        print(f"\n✅ Tenant '{tenant_id}' structure created!")
        return True
        
    except S3Error as e:
        print(f"❌ Error creating tenant structure: {e}")
        return False


def list_tenants(client: Minio) -> list:
    """Lista todos los tenants."""
    try:
        tenants = set()
        objects = client.list_objects(MINIO_BUCKET, prefix="", recursive=False)
        
        for obj in objects:
            if obj.is_dir:
                tenant_id = obj.object_name.rstrip("/")
                if not tenant_id.startswith("_"):
                    tenants.add(tenant_id)
        
        return sorted(list(tenants))
        
    except S3Error as e:
        print(f"❌ Error listing tenants: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Initialize MinIO storage for MCP Forensics")
    parser.add_argument("--create-tenant", type=str, help="Create tenant structure")
    parser.add_argument("--list-tenants", action="store_true", help="List all tenants")
    parser.add_argument("--init-only", action="store_true", help="Only initialize bucket")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MCP Kali Forensics - MinIO Storage Initialization")
    print("=" * 60)
    print(f"Endpoint: {MINIO_ENDPOINT}")
    print(f"Bucket:   {MINIO_BUCKET}")
    print("=" * 60)
    
    client = get_client()
    
    # Test connection
    try:
        client.list_buckets()
        print("✅ Connected to MinIO")
    except Exception as e:
        print(f"❌ Failed to connect to MinIO: {e}")
        sys.exit(1)
    
    if args.list_tenants:
        tenants = list_tenants(client)
        print(f"\n📋 Tenants ({len(tenants)}):")
        for tenant in tenants:
            print(f"   - {tenant}")
        return
    
    if args.create_tenant:
        # Ensure bucket exists first
        if not init_bucket(client):
            sys.exit(1)
        
        if not create_tenant_structure(client, args.create_tenant):
            sys.exit(1)
        return
    
    # Full initialization
    print("\n🚀 Initializing storage...")
    
    if not init_bucket(client):
        sys.exit(1)
    
    if not args.init_only:
        if not create_system_structure(client):
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ MinIO storage initialized successfully!")
    print("=" * 60)
    print(f"   Endpoint API: http://{MINIO_ENDPOINT}")
    print(f"   Console:      http://10.10.10.5:9001")
    print(f"   Bucket:       {MINIO_BUCKET}")
    print("=" * 60)
    print("\nNext steps:")
    print("   Create a tenant:")
    print("   python3 scripts/init_minio.py --create-tenant tenant-acme-corp")


if __name__ == "__main__":
    main()
