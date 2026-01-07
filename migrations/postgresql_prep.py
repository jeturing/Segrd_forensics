"""
MCP Kali Forensics - PostgreSQL Migration Preparation v4.4.1
Plan de migración SQLite → PostgreSQL

Este módulo prepara la transición a PostgreSQL sin romper la compatibilidad actual.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.dialects import postgresql
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# MIGRACIÓN A POSTGRESQL - ESPECIFICACIÓN v4.4.1
# =============================================================================
"""
🎯 OBJETIVOS DE LA MIGRACIÓN:

1. JSONB para campos complejos:
   - findings: dict → JSONB
   - logs: List[dict] → JSONB
   - metadata: dict → JSONB
   - evidence_files: List[str] → JSONB array

2. Índices por case_id:
   - Todas las tablas forenses indexadas por case_id
   - Índices compuestos case_id + created_at para timeline

3. Particionamiento por fecha:
   - forensic_analyses particionada por mes
   - logs particionados por semana
   - evidence por mes

4. Extensiones PostgreSQL requeridas:
   - pg_trgm: búsqueda full-text
   - btree_gin: índices compuestos
   - uuid-ossp: generación de UUIDs

TIMELINE:
- v4.4.1: Preparación (este archivo)
- v4.5.0: Dual-write SQLite + PostgreSQL
- v4.6.0: Migración completa a PostgreSQL
"""


# =============================================================================
# SCHEMA POSTGRESQL (DDL)
# =============================================================================

POSTGRESQL_SCHEMA = """
-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- ============================================================================
-- TABLA: forensic_analyses
-- ============================================================================
CREATE TABLE IF NOT EXISTS forensic_analyses (
    id VARCHAR(20) PRIMARY KEY,  -- FA-YYYY-XXXXX
    case_id VARCHAR(20) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'queued',
    
    -- JSONB para datos complejos
    findings JSONB DEFAULT '{}',
    logs JSONB DEFAULT '[]',
    evidence_files JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_case FOREIGN KEY (case_id) 
        REFERENCES cases(id) ON DELETE CASCADE
) PARTITION BY RANGE (created_at);

-- Particiones por mes (crear automáticamente con pg_partman o manualmente)
CREATE TABLE forensic_analyses_2025_01 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
    
CREATE TABLE forensic_analyses_2025_02 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Índices optimizados
CREATE INDEX idx_fa_case_id ON forensic_analyses(case_id);
CREATE INDEX idx_fa_case_created ON forensic_analyses(case_id, created_at DESC);
CREATE INDEX idx_fa_status ON forensic_analyses(status);
CREATE INDEX idx_fa_tool ON forensic_analyses(tool_name);
CREATE INDEX idx_fa_findings_gin ON forensic_analyses USING gin(findings);
CREATE INDEX idx_fa_metadata_gin ON forensic_analyses USING gin(metadata);


-- ============================================================================
-- TABLA: analysis_logs (logs de streaming separados)
-- ============================================================================
CREATE TABLE IF NOT EXISTS analysis_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id VARCHAR(20) NOT NULL,
    case_id VARCHAR(20) NOT NULL,
    
    -- Log entry
    level VARCHAR(10) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    
    -- Timestamp preciso
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- FK
    CONSTRAINT fk_analysis FOREIGN KEY (analysis_id)
        REFERENCES forensic_analyses(id) ON DELETE CASCADE
) PARTITION BY RANGE (timestamp);

-- Particiones por semana
CREATE TABLE analysis_logs_2025_w01 PARTITION OF analysis_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-01-08');

-- Índices para streaming rápido
CREATE INDEX idx_logs_analysis ON analysis_logs(analysis_id, timestamp DESC);
CREATE INDEX idx_logs_case ON analysis_logs(case_id, timestamp DESC);
CREATE INDEX idx_logs_level ON analysis_logs(level);


-- ============================================================================
-- TABLA: cases (actualizada)
-- ============================================================================
CREATE TABLE IF NOT EXISTS cases (
    id VARCHAR(20) PRIMARY KEY,  -- IR-YYYY-NNN
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'open',
    priority VARCHAR(10) DEFAULT 'medium',
    
    -- JSONB
    metadata JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    assignees JSONB DEFAULT '[]',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_created ON cases(created_at DESC);
CREATE INDEX idx_cases_tags_gin ON cases USING gin(tags);


-- ============================================================================
-- TABLA: processes (gestión de procesos persistentes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS processes (
    id VARCHAR(50) PRIMARY KEY,  -- PROC-{tool}-{uuid}
    case_id VARCHAR(20) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    
    -- Configuración
    config JSONB DEFAULT '{}',
    
    -- Resultado
    result JSONB,
    error TEXT,
    exit_code INTEGER,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_proc_case ON processes(case_id);
CREATE INDEX idx_proc_status ON processes(status);


-- ============================================================================
-- TABLA: iocs (Indicators of Compromise)
-- ============================================================================
CREATE TABLE IF NOT EXISTS iocs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(20),
    
    -- IOC data
    type VARCHAR(50) NOT NULL,  -- ip, domain, hash, email, etc.
    value TEXT NOT NULL,
    confidence SMALLINT DEFAULT 50,  -- 0-100
    severity VARCHAR(10) DEFAULT 'medium',
    
    -- Context
    source VARCHAR(100),
    description TEXT,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    -- Related entities
    related_iocs JSONB DEFAULT '[]',
    
    -- Timestamps
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ioc_case ON iocs(case_id);
CREATE INDEX idx_ioc_type ON iocs(type);
CREATE INDEX idx_ioc_value ON iocs(value);
CREATE INDEX idx_ioc_value_trgm ON iocs USING gin(value gin_trgm_ops);
CREATE INDEX idx_ioc_tags_gin ON iocs USING gin(tags);


-- ============================================================================
-- TABLA: timeline_events (eventos unificados)
-- ============================================================================
CREATE TABLE IF NOT EXISTS timeline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(20) NOT NULL,
    
    -- Evento
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    severity VARCHAR(10) DEFAULT 'info',
    
    -- Origen
    source VARCHAR(100),
    source_id VARCHAR(100),
    
    -- Datos
    data JSONB DEFAULT '{}',
    artifacts JSONB DEFAULT '[]',
    
    -- Tiempo del evento (puede ser diferente al created_at)
    event_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (event_time);

CREATE INDEX idx_timeline_case ON timeline_events(case_id, event_time DESC);
CREATE INDEX idx_timeline_type ON timeline_events(event_type);
CREATE INDEX idx_timeline_severity ON timeline_events(severity);
CREATE INDEX idx_timeline_data_gin ON timeline_events USING gin(data);


-- ============================================================================
-- VISTAS MATERIALIZADAS (para dashboards)
-- ============================================================================

-- Resumen de casos
CREATE MATERIALIZED VIEW mv_case_summary AS
SELECT 
    c.id,
    c.name,
    c.status,
    c.priority,
    COUNT(DISTINCT fa.id) as analysis_count,
    COUNT(DISTINCT i.id) as ioc_count,
    COUNT(DISTINCT te.id) as event_count,
    MAX(fa.completed_at) as last_analysis,
    c.created_at
FROM cases c
LEFT JOIN forensic_analyses fa ON fa.case_id = c.id
LEFT JOIN iocs i ON i.case_id = c.id
LEFT JOIN timeline_events te ON te.case_id = c.id
GROUP BY c.id;

CREATE UNIQUE INDEX idx_mv_case_summary ON mv_case_summary(id);

-- Refrescar periódicamente
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_case_summary;


-- ============================================================================
-- FUNCIONES ÚTILES
-- ============================================================================

-- Función para generar ID de análisis
CREATE OR REPLACE FUNCTION generate_analysis_id() 
RETURNS VARCHAR(20) AS $$
DECLARE
    year_str VARCHAR(4);
    next_seq INTEGER;
    result VARCHAR(20);
BEGIN
    year_str := EXTRACT(YEAR FROM NOW())::VARCHAR;
    
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(id FROM 9 FOR 5) AS INTEGER)
    ), 0) + 1 INTO next_seq
    FROM forensic_analyses
    WHERE id LIKE 'FA-' || year_str || '-%';
    
    result := 'FA-' || year_str || '-' || LPAD(next_seq::VARCHAR, 5, '0');
    RETURN result;
END;
$$ LANGUAGE plpgsql;


-- Función para agregar log de análisis
CREATE OR REPLACE FUNCTION add_analysis_log(
    p_analysis_id VARCHAR(20),
    p_level VARCHAR(10),
    p_message TEXT,
    p_context JSONB DEFAULT '{}'
) RETURNS UUID AS $$
DECLARE
    v_case_id VARCHAR(20);
    v_log_id UUID;
BEGIN
    SELECT case_id INTO v_case_id
    FROM forensic_analyses
    WHERE id = p_analysis_id;
    
    INSERT INTO analysis_logs(analysis_id, case_id, level, message, context)
    VALUES (p_analysis_id, v_case_id, p_level, p_message, p_context)
    RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;
"""


# =============================================================================
# UTILIDADES DE MIGRACIÓN
# =============================================================================

class PostgreSQLMigrationPrep:
    """
    Preparador de migración SQLite → PostgreSQL
    
    Uso:
        prep = PostgreSQLMigrationPrep(sqlite_url, postgres_url)
        await prep.validate_schemas()
        await prep.generate_migration_script()
    """
    
    def __init__(
        self,
        sqlite_url: str = "sqlite:///./forensics.db",
        postgres_url: Optional[str] = None
    ):
        self.sqlite_url = sqlite_url
        self.postgres_url = postgres_url
        self.sqlite_engine = create_engine(sqlite_url)
    
    def get_sqlite_tables(self) -> List[str]:
        """Obtener lista de tablas en SQLite"""
        with self.sqlite_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            return [row[0] for row in result if not row[0].startswith('sqlite_')]
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Obtener schema de una tabla SQLite"""
        with self.sqlite_engine.connect() as conn:
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = []
            for row in result:
                columns.append({
                    'cid': row[0],
                    'name': row[1],
                    'type': row[2],
                    'notnull': bool(row[3]),
                    'default': row[4],
                    'pk': bool(row[5])
                })
            return {'table': table_name, 'columns': columns}
    
    def generate_migration_plan(self) -> Dict[str, Any]:
        """Generar plan de migración"""
        tables = self.get_sqlite_tables()
        plan = {
            'source': 'sqlite',
            'target': 'postgresql',
            'tables': {},
            'requires_jsonb_conversion': [],
            'requires_index_creation': [],
            'requires_partitioning': []
        }
        
        # Tablas que necesitan JSONB
        jsonb_tables = ['forensic_analyses', 'cases', 'iocs', 'processes']
        
        # Tablas que necesitan particionamiento
        partitioned_tables = ['forensic_analyses', 'analysis_logs', 'timeline_events']
        
        for table in tables:
            schema = self.get_table_schema(table)
            plan['tables'][table] = schema
            
            if table in jsonb_tables:
                plan['requires_jsonb_conversion'].append(table)
            
            if table in partitioned_tables:
                plan['requires_partitioning'].append(table)
            
            # Todas las tablas con case_id necesitan índice
            if any(col['name'] == 'case_id' for col in schema['columns']):
                plan['requires_index_creation'].append(table)
        
        return plan
    
    def export_data_to_json(self, output_dir: str = "./migration_data"):
        """
        Exportar datos de SQLite a JSON para migración
        
        Útil para migrar datos sin necesidad de conexión directa
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        tables = self.get_sqlite_tables()
        for table in tables:
            with self.sqlite_engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                rows = [dict(row._mapping) for row in result]
                
                output_file = os.path.join(output_dir, f"{table}.json")
                with open(output_file, 'w') as f:
                    json.dump(rows, f, indent=2, default=str)
                
                logger.info(f"📦 Exportado {table}: {len(rows)} registros")
        
        return output_dir


# =============================================================================
# DUAL-WRITE MIXIN (para v4.5.0)
# =============================================================================

class DualWriteMixin:
    """
    Mixin para escribir simultáneamente en SQLite y PostgreSQL
    
    Usar durante la fase de transición para asegurar consistencia.
    
    Uso:
        class ForensicAnalysisService(DualWriteMixin):
            async def create_analysis(self, data):
                # Escribe en ambas BDs
                await self.dual_write('forensic_analyses', data)
    """
    
    async def dual_write(
        self,
        table: str,
        data: Dict[str, Any],
        sqlite_engine=None,
        postgres_engine=None
    ):
        """
        Escribir en SQLite y PostgreSQL simultáneamente
        
        En caso de error en PostgreSQL, el log se registra pero
        SQLite sigue siendo la fuente de verdad.
        """
        # SQLite siempre primero (fuente de verdad durante migración)
        if sqlite_engine:
            try:
                # Insert en SQLite
                pass  # Implementar según ORM/SQL directo
            except Exception as e:
                logger.error(f"❌ Error SQLite write: {e}")
                raise
        
        # PostgreSQL como réplica
        if postgres_engine:
            try:
                # Insert en PostgreSQL (convertir a JSONB donde aplique)
                pass  # Implementar según ORM/SQL directo
            except Exception as e:
                logger.warning(f"⚠️ Error PostgreSQL write (non-fatal): {e}")
                # No raise - SQLite es fuente de verdad


# =============================================================================
# CONFIGURACIÓN PARA DOCKER
# =============================================================================

DOCKER_POSTGRES_CONFIG = """
# docker-compose.postgres.yml
# Agregar al docker-compose.yml existente

services:
  postgres:
    image: postgres:16-alpine
    container_name: mcp-postgres
    environment:
      POSTGRES_USER: forensics
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: forensics
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U forensics"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mcp-network

volumes:
  postgres_data:
"""
