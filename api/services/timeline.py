"""
Timeline Service v4.4
======================
Gestión de línea de tiempo de eventos para investigaciones
Completamente orientado a casos con persistencia
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid
import json

from api.services.llm_provider import get_llm_manager

logger = logging.getLogger(__name__)


class TimelineService:
    """Servicio de Timeline de Eventos v4.4"""
    
    def __init__(self):
        self.events: Dict[str, Dict] = {}
        self.correlations: Dict[str, Dict] = {}
        # v4.4: Índice por caso
        self.case_events: Dict[str, List[str]] = {}
        
    async def create_event(
        self,
        event_time: datetime,
        event_type: str,
        title: str,
        case_id: str,  # v4.4: OBLIGATORIO
        **kwargs
    ) -> Dict:
        """
        Crea un nuevo evento en la timeline
        
        Args:
            event_time: Timestamp del evento
            event_type: Tipo (login, file_access, command, network, etc.)
            title: Título descriptivo
            case_id: ID del caso asociado (OBLIGATORIO en v4.4)
            **kwargs: Campos adicionales
            
        Returns:
            Evento creado
        """
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        
        event = {
            "event_id": event_id,
            "event_time": event_time.isoformat(),
            "event_type": event_type,
            "title": title,
            "case_id": case_id,
            "category": kwargs.get("category", "general"),
            "description": kwargs.get("description"),
            "severity": kwargs.get("severity", "info"),
            "source_type": kwargs.get("source_type"),
            "source_id": kwargs.get("source_id"),
            "source_name": kwargs.get("source_name"),
            "target_type": kwargs.get("target_type"),
            "target_id": kwargs.get("target_id"),
            "target_name": kwargs.get("target_name"),
            "source_ip": kwargs.get("source_ip"),
            "destination_ip": kwargs.get("destination_ip"),
            "geo_location": kwargs.get("geo_location", {}),
            "mitre_tactic": kwargs.get("mitre_tactic"),
            "mitre_technique": kwargs.get("mitre_technique"),
            "ioc_refs": kwargs.get("ioc_refs", []),
            "data_source": kwargs.get("data_source"),
            "raw_data": kwargs.get("raw_data", {}),
            "tags": kwargs.get("tags", []),
            "is_suspicious": kwargs.get("is_suspicious", False),
            "is_malicious": kwargs.get("is_malicious", False),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": kwargs.get("created_by")
        }
        
        self.events[event_id] = event
        
        # v4.4: Registrar en índice de caso
        if case_id not in self.case_events:
            self.case_events[case_id] = []
        self.case_events[case_id].append(event_id)
        
        logger.info(f"📅 Evento creado: {event_id} - {title} (caso: {case_id})")
        
        return event
    
    async def get_event(self, event_id: str) -> Optional[Dict]:
        """Obtiene un evento por ID"""
        return self.events.get(event_id)
    
    async def get_events(
        self,
        case_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict]:
        """
        Obtiene eventos filtrados
        
        Args:
            case_id: Filtrar por caso
            start_time: Desde cuando
            end_time: Hasta cuando
            event_type: Tipo de evento
            severity: Severidad mínima
            limit: Máximo de resultados
            
        Returns:
            Lista de eventos ordenados cronológicamente
        """
        events = list(self.events.values())
        
        # Aplicar filtros
        if case_id:
            events = [e for e in events if e.get("case_id") == case_id]
        
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        
        if severity:
            severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
            min_sev = severity_order.get(severity, 0)
            events = [e for e in events if severity_order.get(e.get("severity", "info"), 0) >= min_sev]
        
        if start_time:
            events = [e for e in events if datetime.fromisoformat(e["event_time"]) >= start_time]
        
        if end_time:
            events = [e for e in events if datetime.fromisoformat(e["event_time"]) <= end_time]
        
        # Ordenar por tiempo
        events.sort(key=lambda x: x["event_time"])
        
        return events[:limit]
    
    async def update_event(self, event_id: str, updates: Dict) -> Optional[Dict]:
        """Actualiza un evento"""
        if event_id not in self.events:
            return None
        
        self.events[event_id].update(updates)
        self.events[event_id]["updated_at"] = datetime.utcnow().isoformat()
        
        return self.events[event_id]
    
    async def delete_event(self, event_id: str) -> bool:
        """Elimina un evento"""
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False
    
    async def bulk_import_events(
        self,
        events_data: List[Dict],
        case_id: str,
        data_source: str
    ) -> Dict:
        """
        Importa múltiples eventos de una fuente
        
        Args:
            events_data: Lista de eventos en formato raw
            case_id: ID del caso
            data_source: Fuente de los datos
            
        Returns:
            Resumen de importación
        """
        imported = 0
        errors = 0
        
        for event_data in events_data:
            try:
                event_time = event_data.get("timestamp") or event_data.get("event_time")
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                elif not event_time:
                    event_time = datetime.utcnow()
                
                await self.create_event(
                    event_time=event_time,
                    event_type=event_data.get("type", "unknown"),
                    title=event_data.get("title", "Imported Event"),
                    case_id=case_id,
                    data_source=data_source,
                    raw_data=event_data,
                    **{k: v for k, v in event_data.items() if k not in ["timestamp", "event_time", "type", "title"]}
                )
                imported += 1
            except Exception as e:
                logger.warning(f"Error importando evento: {e}")
                errors += 1
        
        return {
            "imported": imported,
            "errors": errors,
            "total": len(events_data)
        }
    
    # ==================== CORRELACIONES ====================
    
    async def create_correlation(
        self,
        event_ids: List[str],
        name: str,
        case_id: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Crea una correlación entre eventos
        
        Args:
            event_ids: IDs de eventos a correlacionar
            name: Nombre de la correlación
            case_id: ID del caso
            **kwargs: Campos adicionales
            
        Returns:
            Correlación creada
        """
        correlation_id = f"corr_{uuid.uuid4().hex[:10]}"
        
        # Obtener eventos para calcular timeframe
        events = [self.events.get(eid) for eid in event_ids if eid in self.events]
        events = [e for e in events if e]
        
        if not events:
            return {"error": "No valid events found"}
        
        # Calcular timeframe
        times = [datetime.fromisoformat(e["event_time"]) for e in events]
        start_time = min(times)
        end_time = max(times)
        duration = int((end_time - start_time).total_seconds())
        
        correlation = {
            "correlation_id": correlation_id,
            "name": name,
            "description": kwargs.get("description"),
            "case_id": case_id,
            "event_ids": event_ids,
            "event_count": len(events),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "attack_phase": kwargs.get("attack_phase"),
            "severity": kwargs.get("severity", "medium"),
            "confidence_score": kwargs.get("confidence_score", 0.8),
            "correlation_type": kwargs.get("correlation_type", "manual"),
            "is_confirmed": False,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": kwargs.get("created_by")
        }
        
        self.correlations[correlation_id] = correlation
        
        # Actualizar eventos con referencia a correlación
        for event_id in event_ids:
            if event_id in self.events:
                self.events[event_id]["correlation_id"] = correlation_id
        
        logger.info(f"🔗 Correlación creada: {correlation_id} con {len(events)} eventos")
        
        return correlation
    
    async def get_correlation(self, correlation_id: str) -> Optional[Dict]:
        """Obtiene una correlación por ID"""
        corr = self.correlations.get(correlation_id)
        if corr:
            # Incluir eventos
            corr["events"] = [
                self.events.get(eid) for eid in corr.get("event_ids", [])
                if eid in self.events
            ]
        return corr
    
    async def get_correlations(
        self,
        case_id: Optional[str] = None,
        confirmed_only: bool = False
    ) -> List[Dict]:
        """Obtiene correlaciones filtradas"""
        correlations = list(self.correlations.values())
        
        if case_id:
            correlations = [c for c in correlations if c.get("case_id") == case_id]
        
        if confirmed_only:
            correlations = [c for c in correlations if c.get("is_confirmed")]
        
        return correlations
    
    async def auto_correlate(
        self,
        case_id: str,
        time_window_minutes: int = 30
    ) -> List[Dict]:
        """
        Auto-correlaciona eventos de un caso
        
        Busca patrones como:
        - Misma IP en múltiples eventos
        - Mismo usuario con diferentes acciones
        - Secuencias de ataque conocidas
        
        Args:
            case_id: ID del caso
            time_window_minutes: Ventana de tiempo para correlación
            
        Returns:
            Lista de correlaciones creadas
        """
        events = await self.get_events(case_id=case_id)
        if len(events) < 2:
            return []
        
        created_correlations = []
        time_window = timedelta(minutes=time_window_minutes)
        
        # Agrupar por IP
        by_ip = {}
        for event in events:
            ip = event.get("source_ip")
            if ip:
                if ip not in by_ip:
                    by_ip[ip] = []
                by_ip[ip].append(event)
        
        # Crear correlaciones por IP con múltiples eventos
        for ip, ip_events in by_ip.items():
            if len(ip_events) >= 3:
                corr = await self.create_correlation(
                    event_ids=[e["event_id"] for e in ip_events],
                    name=f"Actividad desde IP: {ip}",
                    case_id=case_id,
                    correlation_type="auto",
                    description=f"Múltiples eventos ({len(ip_events)}) desde la misma IP"
                )
                created_correlations.append(corr)
        
        # Agrupar por usuario
        by_user = {}
        for event in events:
            user = event.get("source_name") or event.get("source_id")
            if user:
                if user not in by_user:
                    by_user[user] = []
                by_user[user].append(event)
        
        # Crear correlaciones por usuario con actividad sospechosa
        for user, user_events in by_user.items():
            suspicious = [e for e in user_events if e.get("is_suspicious") or e.get("severity") in ["high", "critical"]]
            if len(suspicious) >= 2:
                corr = await self.create_correlation(
                    event_ids=[e["event_id"] for e in suspicious],
                    name=f"Actividad sospechosa de: {user}",
                    case_id=case_id,
                    correlation_type="auto",
                    severity="high",
                    description=f"Usuario con {len(suspicious)} eventos sospechosos"
                )
                created_correlations.append(corr)
        
        logger.info(f"🔗 Auto-correlación completada: {len(created_correlations)} correlaciones creadas")
        return created_correlations
    
    async def generate_narrative(self, correlation_id: str) -> Dict:
        """
        Genera narrativa del ataque usando LLM
        
        Args:
            correlation_id: ID de la correlación
            
        Returns:
            Narrativa generada
        """
        corr = await self.get_correlation(correlation_id)
        if not corr:
            return {"error": "Correlation not found"}
        
        events = corr.get("events", [])
        if not events:
            return {"error": "No events in correlation"}
        
        try:
            llm_manager = get_llm_manager()
            
            # Preparar datos para LLM
            events_summary = []
            for e in events[:20]:  # Limitar a 20 eventos
                events_summary.append({
                    "time": e.get("event_time"),
                    "type": e.get("event_type"),
                    "title": e.get("title"),
                    "severity": e.get("severity"),
                    "source": e.get("source_name"),
                    "target": e.get("target_name"),
                    "mitre": e.get("mitre_technique")
                })
            
            prompt = f"""Analiza la siguiente secuencia de eventos de seguridad y genera una narrativa del incidente:

Correlación: {corr.get('name')}
Período: {corr.get('start_time')} a {corr.get('end_time')}
Duración: {corr.get('duration_seconds')} segundos
Total eventos: {corr.get('event_count')}

Eventos (ordenados cronológicamente):
{events_summary}

Genera:
1. **Narrativa del incidente**: Describe qué ocurrió como una historia coherente
2. **Fase del ataque**: En qué fase de la kill chain se encuentra
3. **Técnicas MITRE ATT&CK**: Identificadas en la secuencia
4. **Actor probable**: Tipo de amenaza (APT, insider, malware, etc.)
5. **Impacto potencial**: Qué sistemas/datos están en riesgo
6. **Recomendaciones inmediatas**: 3 acciones prioritarias

Responde en español, formato Markdown."""

            result = await llm_manager.generate(
                prompt=prompt,
                system_prompt="Eres un analista senior de respuesta a incidentes con experiencia en threat intelligence.",
                max_tokens=2000,
                temperature=0.4
            )
            
            # Guardar narrativa en correlación
            self.correlations[correlation_id]["llm_narrative"] = result.get("content", "")
            self.correlations[correlation_id]["narrative_generated_at"] = datetime.utcnow().isoformat()
            
            return {
                "correlation_id": correlation_id,
                "narrative": result.get("content", ""),
                "model": result.get("model"),
                "provider": result.get("provider")
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando narrativa: {e}")
            return {"error": str(e)}
    
    async def get_timeline_summary(self, case_id: str) -> Dict:
        """Obtiene resumen de timeline para un caso"""
        events = await self.get_events(case_id=case_id)
        correlations = await self.get_correlations(case_id=case_id)
        
        # Estadísticas
        by_type = {}
        by_severity = {"info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
        suspicious_count = 0
        
        for event in events:
            etype = event.get("event_type", "unknown")
            by_type[etype] = by_type.get(etype, 0) + 1
            
            sev = event.get("severity", "info")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            if event.get("is_suspicious") or event.get("is_malicious"):
                suspicious_count += 1
        
        # Timeframe
        if events:
            times = [datetime.fromisoformat(e["event_time"]) for e in events]
            start = min(times)
            end = max(times)
            duration = (end - start).total_seconds()
        else:
            start = end = None
            duration = 0
        
        return {
            "case_id": case_id,
            "total_events": len(events),
            "total_correlations": len(correlations),
            "confirmed_correlations": len([c for c in correlations if c.get("is_confirmed")]),
            "suspicious_events": suspicious_count,
            "events_by_type": by_type,
            "events_by_severity": by_severity,
            "timeframe": {
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
                "duration_seconds": duration
            }
        }

    # ==================== MÉTODOS ADICIONALES PARA RUTAS ====================

    async def get_stats(self) -> Dict:
        """Obtiene estadísticas globales del servicio"""
        return {
            "total_events": len(self.events),
            "total_correlations": len(self.correlations),
            "cases_tracked": len(set(e.get("case_id") for e in self.events.values() if e.get("case_id")))
        }

    async def get_timeline(
        self,
        case_id: str,
        filters: Dict = None,
        limit: int = 500,
        offset: int = 0
    ) -> Dict:
        """Obtiene timeline con paginación y filtros"""
        events = await self.get_events(
            case_id=case_id,
            start_time=filters.get("start_time") if filters else None,
            end_time=filters.get("end_time") if filters else None,
            event_type=filters.get("event_types", [None])[0] if filters and filters.get("event_types") else None,
            severity=filters.get("severity") if filters else None,
            limit=limit + offset
        )
        
        # Aplicar offset
        paginated = events[offset:offset + limit]
        
        return {
            "total": len(events),
            "events": paginated
        }

    async def add_event(
        self,
        case_id: str,
        event_time: datetime,
        event_type: str,
        source: str,
        title: str,
        description: Optional[str] = None,
        severity: str = "info",
        entities: Dict = None,
        indicators: List[str] = None,
        raw_data: Dict = None,
        correlation_ids: List[str] = None
    ) -> Dict:
        """Agregar evento al timeline (wrapper para create_event)"""
        return await self.create_event(
            event_time=event_time,
            event_type=event_type,
            title=title,
            case_id=case_id,
            description=description,
            severity=severity,
            data_source=source,
            raw_data=raw_data or {},
            ioc_refs=indicators or [],
            tags=correlation_ids or []
        )

    async def bulk_add_events(self, case_id: str, events: List[Dict]) -> Dict:
        """Agregar múltiples eventos"""
        added = 0
        failed = 0
        event_ids = []
        
        for event_data in events:
            try:
                result = await self.add_event(
                    case_id=case_id,
                    event_time=event_data["event_time"],
                    event_type=event_data["event_type"],
                    source=event_data.get("source", "manual"),
                    title=event_data["title"],
                    description=event_data.get("description"),
                    severity=event_data.get("severity", "info"),
                    entities=event_data.get("entities"),
                    indicators=event_data.get("indicators"),
                    raw_data=event_data.get("raw_data"),
                    correlation_ids=event_data.get("correlation_ids")
                )
                event_ids.append(result["event_id"])
                added += 1
            except Exception as e:
                logger.error(f"Error agregando evento: {e}")
                failed += 1
        
        return {"added": added, "failed": failed, "event_ids": event_ids}

    async def update_event(self, event_id: str, updates: Dict) -> bool:
        """Actualizar un evento"""
        if event_id not in self.events:
            return False
        
        self.events[event_id].update(updates)
        self.events[event_id]["updated_at"] = datetime.utcnow().isoformat()
        return True

    async def delete_event(self, event_id: str) -> bool:
        """Eliminar un evento"""
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False

    async def correlate_events(
        self,
        case_id: str,
        event_ids: List[str],
        correlation_name: str,
        correlation_type: str = "manual"
    ) -> Dict:
        """Correlacionar múltiples eventos"""
        correlation_id = f"corr_{uuid.uuid4().hex[:8]}"
        
        correlation = {
            "id": correlation_id,
            "case_id": case_id,
            "name": correlation_name,
            "type": correlation_type,
            "event_ids": event_ids,
            "created_at": datetime.utcnow().isoformat(),
            "is_confirmed": False
        }
        
        self.correlations[correlation_id] = correlation
        
        # Actualizar eventos con el ID de correlación
        for event_id in event_ids:
            if event_id in self.events:
                if "correlation_ids" not in self.events[event_id]:
                    self.events[event_id]["correlation_ids"] = []
                self.events[event_id]["correlation_ids"].append(correlation_id)
        
        return correlation

    async def get_summary(self, case_id: str) -> Dict:
        """Alias para get_timeline_summary"""
        return await self.get_timeline_summary(case_id)

    async def get_graph_data(self, case_id: str, resolution: str = "hour") -> Dict:
        """Obtiene datos para gráfico de timeline"""
        events = await self.get_events(case_id=case_id)
        
        if not events:
            return {"data_points": 0, "series": []}
        
        # Agrupar por intervalo de tiempo
        series_data = {}
        
        for event in events:
            event_time = datetime.fromisoformat(event["event_time"])
            
            if resolution == "minute":
                bucket = event_time.replace(second=0, microsecond=0)
            elif resolution == "hour":
                bucket = event_time.replace(minute=0, second=0, microsecond=0)
            else:  # day
                bucket = event_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            bucket_str = bucket.isoformat()
            event_type = event.get("event_type", "unknown")
            
            if bucket_str not in series_data:
                series_data[bucket_str] = {}
            
            if event_type not in series_data[bucket_str]:
                series_data[bucket_str][event_type] = 0
            
            series_data[bucket_str][event_type] += 1
        
        return {
            "data_points": len(series_data),
            "series": [
                {"timestamp": ts, "counts": counts}
                for ts, counts in sorted(series_data.items())
            ]
        }

    async def import_from_source(self, case_id: str, source: str, data: Dict) -> Dict:
        """Importar eventos desde una fuente específica"""
        event_ids = []
        
        # Mapear según la fuente
        if source == "m365_audit":
            for log in data.get("audit_logs", []):
                event = await self.add_event(
                    case_id=case_id,
                    event_time=datetime.fromisoformat(log.get("CreationTime", datetime.utcnow().isoformat())),
                    event_type=log.get("Operation", "unknown"),
                    source=source,
                    title=f"{log.get('Operation')} - {log.get('UserId', 'Unknown')}",
                    severity="medium",
                    raw_data=log
                )
                event_ids.append(event["event_id"])
        
        elif source == "endpoint_loki":
            # Parsear output de Loki
            loki_output = data.get("loki_output", "")
            for line in loki_output.split("\n"):
                if "[ALERT]" in line or "[WARNING]" in line:
                    event = await self.add_event(
                        case_id=case_id,
                        event_time=datetime.utcnow(),
                        event_type="loki_detection",
                        source=source,
                        title=line[:200],
                        severity="high" if "[ALERT]" in line else "medium",
                        raw_data={"raw_line": line}
                    )
                    event_ids.append(event["event_id"])
        
        return {"count": len(event_ids), "event_ids": event_ids}

    async def export_timeline(self, case_id: str, format: str = "json") -> Dict:
        """Exportar timeline en diferentes formatos"""
        import os
        
        events = await self.get_events(case_id=case_id)
        
        export_dir = f"forensics-evidence/{case_id}/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"timeline_{case_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
        filepath = os.path.join(export_dir, filename)
        
        if format == "json":
            with open(filepath, "w") as f:
                json.dump(events, f, indent=2, default=str)
        elif format == "csv":
            import csv
            if events:
                with open(filepath, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=events[0].keys())
                    writer.writeheader()
                    writer.writerows(events)
        
        return {
            "path": filepath,
            "url": f"/api/downloads/{case_id}/exports/{filename}"
        }


# Singleton
timeline_service = TimelineService()
