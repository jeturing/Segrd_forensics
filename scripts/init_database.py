#!/usr/bin/env python3
"""
Script de Inicialización de Base de Datos v4.6
===============================================
Crea las tablas necesarias y el usuario Global Admin (Pluton_JE).

Uso:
    python scripts/init_database.py
    
    # Forzar recreación
    python scripts/init_database.py --reset
    
    # Usar PostgreSQL de Docker
    python scripts/init_database.py --docker
"""

import sys
import os
import argparse

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime


def get_database_url(use_docker=False):
    """Obtener URL de BD sincrónica."""
    if use_docker:
        # Conexión directa al PostgreSQL en Docker
        password = os.getenv("DB_PASSWORD", "change-me-please")
        return f"postgresql://forensics:{password}@localhost:5432/forensics"
    
    db_url = os.getenv("DATABASE_URL", "")
    
    # Convertir asyncpg a psycopg2 para operaciones sincrónicas
    if "asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Si no hay URL, usar SQLite
    if not db_url:
        db_url = "sqlite:///./forensics.db"
    
    return db_url


def main():
    parser = argparse.ArgumentParser(description="Inicializar base de datos")
    parser.add_argument("--reset", action="store_true", help="Eliminar y recrear tablas")
    parser.add_argument("--docker", action="store_true", help="Usar PostgreSQL de Docker")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🗄️  INICIALIZACIÓN DE BASE DE DATOS v4.6")
    print("=" * 60)
    
    db_url = get_database_url(use_docker=args.docker)
    display_url = db_url.split('@')[-1] if '@' in db_url else db_url
    print(f"\n📡 Conectando a: {display_url}")
    
    try:
        # Crear engine sincrónico
        if db_url.startswith("sqlite"):
            engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(db_url)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Verificar conexión
        session.execute(text("SELECT 1"))
        print("✅ Conexión exitosa")
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("\n💡 Intenta con --docker para usar PostgreSQL de Docker")
        sys.exit(1)
    
    # Importar modelos
    print("\n📦 Cargando modelos...")
    
    try:
        from api.database import Base
        from api.models.user import User, Role, UserSession, UserAuditLog
        from api.models.tenant import Tenant
        from api.models.case import Case
        print("   ✅ Modelos cargados")
    except Exception as e:
        print(f"   ⚠️ Error cargando algunos modelos: {e}")
        from api.database import Base
    
    # Reset si se solicita
    if args.reset:
        print("\n🗑️  Eliminando tablas existentes...")
        Base.metadata.drop_all(engine)
        print("   ✅ Tablas eliminadas")
    
    # Crear tablas
    print("\n🔨 Creando tablas...")
    Base.metadata.create_all(engine)
    print("   ✅ Tablas creadas")
    
    # Listar tablas creadas
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n📋 Tablas en la BD ({len(tables)}):")
    for table in sorted(tables)[:20]:  # Solo primeras 20
        print(f"   • {table}")
    if len(tables) > 20:
        print(f"   ... y {len(tables) - 20} más")
    
    # Verificar si existe el tenant jeturing
    print("\n🏢 Verificando tenant 'jeturing'...")
    result = session.execute(text("SELECT id FROM tenants WHERE tenant_id = 'jeturing'")).fetchone()
    
    if not result:
        print("   Creando tenant jeturing...")
        tenant_uuid = str(uuid.uuid4())
        
        # Generar schema_name único
        schema_name = f"tenant_jeturing_{tenant_uuid[:8]}"
        
        session.execute(text("""
            INSERT INTO tenants (
                id, tenant_id, name, subdomain, schema_name, 
                is_active, created_at, max_users, max_cases, max_storage_gb
            )
            VALUES (
                :id, 'jeturing', 'Jeturing Labs', 'jeturing', :schema_name,
                true, :now, 100, 10000, 500
            )
        """), {
            "id": tenant_uuid, 
            "schema_name": schema_name,
            "now": datetime.utcnow()
        })
        session.commit()
        print("   ✅ Tenant 'jeturing' creado")
        tenant_id = tenant_uuid
    else:
        tenant_id = str(result[0])
        print("   ✅ Tenant 'jeturing' ya existe")
    
    # Verificar/crear usuario Pluton_JE
    print("\n👑 Verificando usuario 'Pluton_JE'...")
    result = session.execute(text("SELECT id FROM users WHERE username = 'Pluton_JE'")).fetchone()
    
    if not result:
        print("   Creando usuario Pluton_JE...")
        import bcrypt
        
        # Contraseña por defecto (CAMBIAR EN PRODUCCIÓN)
        default_password = "Pluton_JE_2025!"
        hashed = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()
        
        user_id = str(uuid.uuid4())
        
        # Crear usuario SIN tenant_id (se asocia via user_tenants)
        session.execute(text("""
            INSERT INTO users (
                id, username, email, password_hash, full_name,
                is_active, is_global_admin, created_at
            ) VALUES (
                :id, 'Pluton_JE', 'pluton_je@jeturing.com', :password_hash,
                'Pluton JE - Global Admin', true, true, :now
            )
        """), {
            "id": user_id,
            "password_hash": hashed,
            "now": datetime.utcnow()
        })
        session.commit()
        
        print("   ✅ Usuario 'Pluton_JE' creado")
        print(f"\n   📧 Email: pluton_je@jeturing.com")
        print(f"   👤 Usuario: Pluton_JE")
        print(f"   🔐 Password: {default_password}")
        print("   ⚠️  ¡CAMBIAR EN PRODUCCIÓN!")
    else:
        user_id = str(result[0])
        print("   ✅ Usuario 'Pluton_JE' ya existe")
        print("\n   ℹ️  Credenciales actuales:")
        print("      👤 Usuario: Pluton_JE")
        print("      🔐 Password: Pluton_JE_2025! (si no se cambió)")
    
    # Asociar usuario al tenant si no está
    print("\n🔗 Verificando asociación usuario-tenant...")
    
    # Obtener IDs correctos
    user_result = session.execute(text("SELECT id FROM users WHERE username = 'Pluton_JE'")).fetchone()
    tenant_result = session.execute(text("SELECT id FROM tenants WHERE tenant_id = 'jeturing'")).fetchone()
    
    if user_result and tenant_result:
        user_uuid = str(user_result[0])
        tenant_uuid = str(tenant_result[0])
        
        result = session.execute(text("""
            SELECT 1 FROM user_tenants 
            WHERE user_id = :user_id AND tenant_id = :tenant_id
        """), {"user_id": user_uuid, "tenant_id": tenant_uuid}).fetchone()
        
        if not result:
            session.execute(text("""
                INSERT INTO user_tenants (user_id, tenant_id, created_at)
                VALUES (:user_id, :tenant_id, :now)
            """), {
                "user_id": user_uuid,
                "tenant_id": tenant_uuid,
                "now": datetime.utcnow()
            })
            session.commit()
            print("   ✅ Usuario asociado al tenant")
        else:
            print("   ✅ Asociación ya existe")
    
    session.close()
    
    print("\n" + "=" * 60)
    print("✅ INICIALIZACIÓN COMPLETADA")
    print("=" * 60)
    print("\n🚀 Credenciales de acceso:")
    print("   ┌─────────────────────────────────────┐")
    print("   │  👤 Usuario:  Pluton_JE             │")
    print("   │  🔐 Password: Pluton_JE_2025!       │")
    print("   │  🏢 Tenant:   jeturing (automático) │")
    print("   └─────────────────────────────────────┘")
    print("\n⚠️  El campo 'Tenant ID' en login es opcional.")
    print("   Se detecta automáticamente si el usuario tiene un solo tenant.\n")


if __name__ == "__main__":
    main()
