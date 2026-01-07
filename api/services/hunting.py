"""
Threat Hunting Service v4.4
============================
Ejecuta queries de hunting contra múltiples fuentes de datos
Completamente orientado a casos con persistencia y tracking
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
import json

from api.services.llm_provider import get_llm_manager
from core import process_manager, ProcessType

logger = logging.getLogger(__name__)


# ==================== QUERY LIBRARY ====================

HUNTING_QUERIES = {
    "suspicious_sign_ins": {
        "name": "Inicios de sesión sospechosos",
        "description": "Detecta inicios de sesión desde ubicaciones inusuales o con patrones anómalos",
        "category": "initial_access",
        "severity": "high",
        "mitre": ["T1078", "T1133"],
        "query_type": "kql",
        "query": """
SigninLogs
| where TimeGenerated > ago(7d)
| where RiskState == "atRisk" or RiskLevelDuringSignIn in ("high", "medium")
| project TimeGenerated, UserPrincipalName, IPAddress, Location, DeviceDetail, RiskState
| order by TimeGenerated desc
"""
    },
    "suspicious_mailbox_rules": {
        "name": "Reglas de buzón sospechosas",
        "description": "Detecta creación de reglas que reenvían o eliminan correos",
        "category": "persistence",
        "severity": "critical",
        "mitre": ["T1114.003", "T1564.008"],
        "query_type": "kql",
        "query": """
OfficeActivity
| where Operation in ("New-InboxRule", "Set-InboxRule")
| where Parameters contains "ForwardTo" or Parameters contains "DeleteMessage"
| project TimeGenerated, UserId, Operation, Parameters, ClientIP
"""
    },
    "mass_download": {
        "name": "Descarga masiva de archivos",
        "description": "Detecta descargas masivas que podrían indicar exfiltración",
        "category": "exfiltration",
        "severity": "high",
        "mitre": ["T1530", "T1567"],
        "query_type": "kql",
        "query": """
OfficeActivity
| where Operation == "FileDownloaded"
| summarize DownloadCount=count() by UserId, bin(TimeGenerated, 1h)
| where DownloadCount > 50
"""
    },
    "oauth_consent_grants": {
        "name": "Grants de OAuth sospechosos",
        "description": "Detecta consentimientos de aplicaciones OAuth potencialmente maliciosas",
        "category": "credential_access",
        "severity": "critical",
        "mitre": ["T1550.001", "T1528"],
        "query_type": "kql",
        "query": """
AuditLogs
| where OperationName == "Consent to application"
| project TimeGenerated, InitiatedBy, TargetResources
| where TargetResources contains "Mail.Read" or TargetResources contains "Files.ReadWrite.All"
"""
    },
    "lateral_movement_rdp": {
        "name": "Movimiento lateral via RDP",
        "description": "Detecta conexiones RDP internas inusuales",
        "category": "lateral_movement",
        "severity": "high",
        "mitre": ["T1021.001"],
        "query_type": "osquery",
        "query": """
SELECT pid, name, cmdline, path
FROM processes
WHERE name LIKE '%rdp%' OR cmdline LIKE '%mstsc%'
"""
    },
    "persistence_registry": {
        "name": "Persistencia en Registry",
        "description": "Detecta modificaciones de registry para persistencia",
        "category": "persistence",
        "severity": "medium",
        "mitre": ["T1547.001"],
        "query_type": "osquery",
        "query": """
SELECT * FROM registry
WHERE path LIKE 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run%'
OR path LIKE 'HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run%'
"""
    },
    "suspicious_powershell": {
        "name": "PowerShell sospechoso",
        "description": "Detecta comandos PowerShell potencialmente maliciosos",
        "category": "execution",
        "severity": "high",
        "mitre": ["T1059.001"],
        "query_type": "sigma",
        "query": """
title: Suspicious PowerShell Execution
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        CommandLine|contains:
            - '-EncodedCommand'
            - '-enc'
            - 'IEX'
            - 'Invoke-Expression'
            - 'downloadstring'
    condition: selection
"""
    }
}


class ThreatHuntingService:
    """Servicio de Threat Hunting v4.4 - Orientado a casos"""
    
    def __init__(self):
        self.queries = HUNTING_QUERIES.copy()
        self.results_cache: Dict[str, Any] = {}
        # v4.4: Cache por caso
        self.case_results: Dict[str, List[str]] = {}  # case_id -> [result_ids]
        
    async def get_queries(self, category: Optional[str] = None) -> List[Dict]:
        """Obtiene queries disponibles"""
        queries = []
        for query_id, query_data in self.queries.items():
            if category and query_data.get('category') != category:
                continue
            queries.append({
                "id": query_id,
                **query_data
            })
        return queries
    
    async def get_query(self, query_id: str) -> Optional[Dict]:
        """Obtiene una query específica"""
        if query_id in self.queries:
            return {"id": query_id, **self.queries[query_id]}
        return None
    
    async def execute_hunt(
        self,
        query_id: str,
        case_id: str,  # v4.4: OBLIGATORIO
        tenant_id: Optional[str] = None,
        time_range: str = "7d",
        parameters: Optional[Dict] = None,
        executed_by: Optional[str] = None
    ) -> Dict:
        """
        Ejecuta una query de hunting vinculada a un caso
        
        Args:
            query_id: ID de la query a ejecutar
            case_id: ID del caso (OBLIGATORIO en v4.4)
            tenant_id: Tenant objetivo (opcional)
            time_range: Rango de tiempo (1d, 7d, 30d, etc.)
            parameters: Parámetros adicionales para la query
            executed_by: Usuario que ejecuta
            
        Returns:
            Resultados del hunt vinculados al caso
        """
        result_id = f"hunt_{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow()
        
        query = await self.get_query(query_id)
        if not query:
            return {
                "result_id": result_id,
                "case_id": case_id,
                "status": "error",
                "error": f"Query not found: {query_id}"
            }
        
        # v4.4: Crear proceso trackeable
        process = process_manager.create_process(
            case_id=case_id,
            process_type=ProcessType.HUNTING,
            name=f"Hunt: {query['name']}",
            input_data={"query_id": query_id, "time_range": time_range},
            created_by=executed_by
        )
        
        logger.info(f"🎯 Ejecutando hunt: {query['name']} (ID: {query_id}) para caso {case_id}")
        
        try:
            process.start()
            process.update_progress(10, "Preparando query")
            
            # Simular ejecución según tipo de query
            query_type = query.get('query_type', 'kql')
            
            process.update_progress(30, f"Ejecutando {query_type}")
            
            if query_type == 'kql':
                results = await self._execute_kql_hunt(query, tenant_id, time_range)
            elif query_type == 'osquery':
                results = await self._execute_osquery_hunt(query, parameters)
            elif query_type == 'sigma':
                results = await self._execute_sigma_hunt(query, parameters)
            else:
                results = []
            
            process.update_progress(60, "Procesando resultados")
            
            # Calcular duración
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Analizar resultados con LLM si hay hits
            llm_analysis = None
            if results:
                process.update_progress(75, "Analizando con IA")
                llm_analysis = await self._analyze_with_llm(query, results, case_id)
            
            process.update_progress(90, "Finalizando")
            
            # Construir resultado
            result = {
                "result_id": result_id,
                "process_id": process.process_id,
                "case_id": case_id,  # v4.4: siempre incluido
                "query_id": query_id,
                "query_name": query['name'],
                "status": "completed",
                "execution_time": start_time.isoformat(),
                "duration_ms": duration_ms,
                "time_range": time_range,
                "total_hits": len(results),
                "results": results[:100],  # Limitar a 100 resultados
                "severity": query.get('severity', 'medium'),
                "mitre_techniques": query.get('mitre', []),
                "llm_analysis": llm_analysis,
                "executed_by": executed_by
            }
            
            # Cache result
            self.results_cache[result_id] = result
            
            # v4.4: Registrar en índice por caso
            if case_id not in self.case_results:
                self.case_results[case_id] = []
            self.case_results[case_id].append(result_id)
            
            # v4.4: Marcar proceso completado
            process.complete({"result_id": result_id, "hits": len(results)})
            
            logger.info(f"✅ Hunt completado: {result_id} - {len(results)} hits para caso {case_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando hunt {query_id}: {e}")
            process.fail(str(e))
            return {
                "result_id": result_id,
                "case_id": case_id,
                "process_id": process.process_id,
                "query_id": query_id,
                "status": "failed",
                "error": str(e),
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }
    
    async def _execute_kql_hunt(
        self,
        query: Dict,
        tenant_id: Optional[str],
        time_range: str
    ) -> List[Dict]:
        """Ejecuta query KQL contra Microsoft Sentinel/M365"""
        # En producción, esto conectaría con Azure Log Analytics
        # Por ahora, retornamos datos simulados basados en la query
        
        await asyncio.sleep(0.5)  # Simular latencia de API
        
        # Generar datos de ejemplo según el tipo de hunt
        category = query.get('category', 'general')
        
        if category == 'initial_access':
            return [
                {
                    "timestamp": "2025-12-07T10:30:00Z",
                    "user": "admin@contoso.com",
                    "ip_address": "185.234.67.89",
                    "location": "Russia",
                    "risk_level": "high",
                    "device": "Unknown",
                    "status": "Success"
                },
                {
                    "timestamp": "2025-12-07T08:15:00Z",
                    "user": "finance@contoso.com",
                    "ip_address": "103.45.67.123",
                    "location": "China",
                    "risk_level": "medium",
                    "device": "Windows 10",
                    "status": "Success"
                }
            ]
        elif category == 'persistence':
            return [
                {
                    "timestamp": "2025-12-06T23:45:00Z",
                    "user": "compromised@contoso.com",
                    "operation": "New-InboxRule",
                    "rule_name": "Security Update",
                    "action": "ForwardTo: external@attacker.com",
                    "client_ip": "185.234.67.89"
                }
            ]
        elif category == 'exfiltration':
            return [
                {
                    "timestamp": "2025-12-07T02:30:00Z",
                    "user": "employee@contoso.com",
                    "files_downloaded": 847,
                    "total_size_mb": 2340,
                    "client_ip": "192.168.1.100"
                }
            ]
        
        return []
    
    async def _execute_osquery_hunt(
        self,
        query: Dict,
        parameters: Optional[Dict]
    ) -> List[Dict]:
        """Ejecuta query OSQuery contra endpoints"""
        await asyncio.sleep(0.3)
        
        # Datos simulados
        category = query.get('category', 'general')
        
        if category == 'persistence':
            return [
                {
                    "path": "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                    "name": "WindowsUpdate",
                    "data": "C:\\Users\\Public\\update.exe -silent",
                    "type": "REG_SZ",
                    "mtime": "2025-12-05T14:30:00Z"
                }
            ]
        elif category == 'lateral_movement':
            return [
                {
                    "pid": 4532,
                    "name": "mstsc.exe",
                    "cmdline": "mstsc.exe /v:192.168.1.50",
                    "path": "C:\\Windows\\System32\\mstsc.exe",
                    "username": "admin"
                }
            ]
        
        return []
    
    async def _execute_sigma_hunt(
        self,
        query: Dict,
        parameters: Optional[Dict]
    ) -> List[Dict]:
        """Ejecuta regla Sigma contra logs"""
        await asyncio.sleep(0.4)
        
        # Datos simulados
        return [
            {
                "timestamp": "2025-12-07T05:20:00Z",
                "process_name": "powershell.exe",
                "command_line": "powershell.exe -EncodedCommand SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYw...",
                "parent_process": "cmd.exe",
                "user": "SYSTEM",
                "host": "WORKSTATION-01"
            }
        ]
    
    async def _analyze_with_llm(
        self,
        query: Dict,
        results: List[Dict],
        case_id: str
    ) -> Optional[Dict]:
        """Analiza resultados con LLM en contexto del caso"""
        try:
            llm_manager = get_llm_manager()
            
            prompt = f"""Analiza los siguientes resultados de threat hunting:

**CONTEXTO DEL CASO:** {case_id}

Query: {query['name']}
Categoría: {query.get('category', 'general')}
Técnicas MITRE: {', '.join(query.get('mitre', []))}
Severidad base: {query.get('severity', 'medium')}

Resultados encontrados ({len(results)} hits):
{json.dumps(results[:10], indent=2, default=str)}

Como analista forense trabajando en el caso {case_id}, proporciona:
1. Evaluación de riesgo (critical/high/medium/low)
2. Resumen ejecutivo de los hallazgos
3. IOCs identificados (IPs, hashes, dominios, emails)
4. Recomendaciones de remediación inmediata
5. Siguiente paso de investigación para este caso
6. Eventos sugeridos para agregar al timeline

Responde en formato JSON estructurado."""

            result = await llm_manager.generate(
                prompt=prompt,
                system_prompt="Eres un analista de seguridad experto en threat hunting y respuesta a incidentes. Trabajas en el contexto de un caso forense específico.",
                max_tokens=1500,
                temperature=0.3
            )
            
            return {
                "analysis": result.get("content", ""),
                "model": result.get("model"),
                "provider": result.get("provider"),
                "case_id": case_id,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error en análisis LLM: {e}")
            return None
    
    async def create_case_from_hunt(
        self,
        result_id: str,
        title: Optional[str] = None,
        assignee: Optional[str] = None
    ) -> Dict:
        """Crea un caso a partir de resultados de hunting"""
        if result_id not in self.results_cache:
            return {"error": "Result not found"}
        
        result = self.results_cache[result_id]
        case_id = f"HUNT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        case = {
            "case_id": case_id,
            "title": title or f"Hunt: {result.get('query_name', 'Unknown')}",
            "source": "threat_hunting",
            "source_id": result_id,
            "severity": result.get('severity', 'medium'),
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "assignee": assignee,
            "metadata": {
                "query_id": result.get('query_id'),
                "hits": result.get('total_hits', 0),
                "mitre_techniques": result.get('mitre_techniques', [])
            }
        }
        
        logger.info(f"📋 Caso creado desde hunt: {case_id}")
        return case
    
    async def get_result(self, result_id: str) -> Optional[Dict]:
        """Obtiene resultado de hunt por ID"""
        return self.results_cache.get(result_id)
    
    async def get_categories(self) -> List[Dict]:
        """Obtiene categorías de hunting disponibles"""
        categories = {}
        for query_id, query_data in self.queries.items():
            cat = query_data.get('category', 'general')
            if cat not in categories:
                categories[cat] = {
                    "id": cat,
                    "name": cat.replace('_', ' ').title(),
                    "query_count": 0
                }
            categories[cat]["query_count"] += 1
        
        return list(categories.values())

    async def get_case_results(
        self,
        case_id: str,
        limit: int = 50,
        severity_filter: Optional[str] = None
    ) -> List[Dict]:
        """Obtiene resultados de hunting para un caso"""
        results = []
        for result_id, result in self.results_cache.items():
            if result.get("case_id") == case_id:
                if severity_filter and result.get("severity") != severity_filter:
                    continue
                results.append(result)
        
        # Ordenar por tiempo y limitar
        results.sort(key=lambda x: x.get("execution_time", ""), reverse=True)
        return results[:limit]

    async def get_hunt_result(self, case_id: str, hunt_id: str) -> Optional[Dict]:
        """Obtiene resultado específico de un hunt"""
        result = self.results_cache.get(hunt_id)
        if result and result.get("case_id") == case_id:
            return result
        return None

    async def save_custom_query(
        self,
        query_id: str,
        name: str,
        description: str,
        query_type: str,
        query: str,
        category: str,
        severity: str,
        mitre: Optional[List[str]] = None,
        data_sources: Optional[List[str]] = None
    ) -> Dict:
        """Guarda una query personalizada"""
        self.queries[query_id] = {
            "name": name,
            "description": description,
            "query_type": query_type,
            "query": query,
            "category": category,
            "severity": severity,
            "mitre": mitre or [],
            "data_sources": data_sources or [],
            "custom": True,
            "created_at": datetime.utcnow().isoformat()
        }
        logger.info(f"💾 Query personalizada guardada: {query_id}")
        return self.queries[query_id]

    async def delete_hunt_result(self, case_id: str, hunt_id: str) -> bool:
        """Elimina resultado de un hunt"""
        if hunt_id in self.results_cache:
            if self.results_cache[hunt_id].get("case_id") == case_id:
                del self.results_cache[hunt_id]
                # v4.4: Actualizar índice de caso
                if case_id in self.case_results:
                    if hunt_id in self.case_results[case_id]:
                        self.case_results[case_id].remove(hunt_id)
                return True
        return False

    async def get_stats(self, case_id: Optional[str] = None) -> Dict:
        """
        Obtiene estadísticas de hunting
        v4.4: Soporta filtro por caso
        """
        if case_id:
            result_ids = self.case_results.get(case_id, [])
            results = [self.results_cache[rid] for rid in result_ids if rid in self.results_cache]
        else:
            results = list(self.results_cache.values())
        
        # Calcular estadísticas
        total_hunts = len(results)
        total_hits = sum(r.get("total_hits", 0) for r in results)
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        category_counts = {}
        technique_counts = {}
        
        for r in results:
            sev = r.get("severity", "medium")
            if sev in severity_counts:
                severity_counts[sev] += 1
            
            # Contar por query para categorías
            query = self.queries.get(r.get("query_id", ""))
            if query:
                cat = query.get("category", "general")
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # Contar técnicas MITRE
            for tech in r.get("mitre_techniques", []):
                technique_counts[tech] = technique_counts.get(tech, 0) + 1
        
        return {
            "total_hunts": total_hunts,
            "total_hits": total_hits,
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "top_techniques": dict(sorted(technique_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "case_id": case_id
        }

    async def batch_execute(
        self,
        query_ids: List[str],
        case_id: str,
        tenant_id: Optional[str] = None,
        time_range: str = "7d",
        executed_by: Optional[str] = None
    ) -> Dict:
        """
        Ejecuta múltiples queries de hunting en batch
        v4.4: Tracking completo por caso
        """
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        results = []
        errors = []
        
        logger.info(f"🎯 Iniciando batch hunt: {len(query_ids)} queries para caso {case_id}")
        
        for query_id in query_ids:
            try:
                result = await self.execute_hunt(
                    query_id=query_id,
                    case_id=case_id,
                    tenant_id=tenant_id,
                    time_range=time_range,
                    executed_by=executed_by
                )
                results.append(result)
            except Exception as e:
                errors.append({
                    "query_id": query_id,
                    "error": str(e)
                })
        
        return {
            "batch_id": batch_id,
            "case_id": case_id,
            "total_queries": len(query_ids),
            "successful": len(results),
            "failed": len(errors),
            "total_hits": sum(r.get("total_hits", 0) for r in results),
            "results": results,
            "errors": errors
        }

    async def delete_custom_query(self, query_id: str) -> bool:
        """Elimina una query personalizada"""
        if query_id in self.queries and self.queries[query_id].get("custom", False):
            del self.queries[query_id]
            logger.info(f"🗑️ Query personalizada eliminada: {query_id}")
            return True
        return False


# Singleton
hunting_service = ThreatHuntingService()
