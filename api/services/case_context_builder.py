"""
Case Context Builder Service
===========================
Construye el contexto enriquecido para el análisis LLM de un caso.
Agrega información de:
- Metadatos del caso
- Timeline de eventos
- Topología del grafo de ataque
- Hallazgos de herramientas
"""

import logging
import json

from api.services.cases import get_case
from api.services.timeline import TimelineService
from api.services.graph_builder import GraphBuilderService

logger = logging.getLogger(__name__)

class CaseContextBuilder:
    """
    Construye un contexto enriquecido para el análisis LLM de un caso.
    """

    def __init__(self):
        self.timeline_service = TimelineService()
        self.graph_service = GraphBuilderService()

    async def build_context(self, case_id: str, max_tokens: int = 8000) -> str:
        """
        Construye el contexto completo del caso para el LLM.
        
        Args:
            case_id: ID del caso
            max_tokens: Límite aproximado de tokens (usado para truncar caracteres)
            
        Returns:
            String con el contexto formateado
        """
        try:
            # 1. Obtener metadatos del caso
            case_data = await get_case(case_id)
            if not case_data:
                logger.warning(f"Case {case_id} not found for context building")
                return f"Case {case_id} not found."

            # 2. Obtener timeline
            # Intentamos obtener eventos, manejando posibles errores si el servicio no está inicializado
            try:
                timeline_events = await self.timeline_service.get_events(case_id=case_id, limit=50)
            except Exception as e:
                logger.warning(f"Could not fetch timeline for context: {e}")
                timeline_events = []
            
            # 3. Obtener grafo
            try:
                graph_data = await self.graph_service.get_case_graph(case_id)
                # Convertir modelo Pydantic a dict si es necesario
                if hasattr(graph_data, 'dict'):
                    graph_data = graph_data.dict()
                elif hasattr(graph_data, 'model_dump'):
                    graph_data = graph_data.model_dump()
            except Exception as e:
                logger.warning(f"Could not fetch graph for context: {e}")
                graph_data = {"nodes": [], "edges": []}

            # 4. Formatear contexto
            context_parts = []
            
            # --- HEADER ---
            context_parts.append(f"CASE ID: {case_id}")
            context_parts.append(f"TYPE: {case_data.get('type', 'Unknown')}")
            context_parts.append(f"STATUS: {case_data.get('status', 'Unknown')}")
            context_parts.append(f"DESCRIPTION: {case_data.get('description', 'No description')}")
            context_parts.append("-" * 40)

            # --- TIMELINE ---
            context_parts.append("TIMELINE (Recent Events):")
            if timeline_events:
                for evt in timeline_events:
                    # Format: [Time] [Type] Title (Severity)
                    ts = evt.get('event_time', '')
                    etype = evt.get('event_type', 'event')
                    title = evt.get('title', '')
                    sev = evt.get('severity', 'info')
                    context_parts.append(f"[{ts}] [{etype}] {title} ({sev})")
            else:
                context_parts.append("No timeline events found.")
            context_parts.append("-" * 40)

            # --- ATTACK GRAPH ---
            context_parts.append("ATTACK GRAPH TOPOLOGY:")
            nodes = graph_data.get('nodes', [])
            edges = graph_data.get('edges', [])
            
            context_parts.append(f"Nodes ({len(nodes)}):")
            # Priorizar nodos con severidad alta
            sorted_nodes = sorted(nodes, key=lambda x: 1 if x.get('severity') in ['critical', 'high'] else 0, reverse=True)
            
            for node in sorted_nodes[:30]: # Limit nodes
                lbl = node.get('label', 'Unknown')
                ntype = node.get('type', 'unknown')
                sev = node.get('severity', 'none')
                context_parts.append(f"- {lbl} ({ntype}) [Severity: {sev}]")
            if len(nodes) > 30:
                context_parts.append(f"... and {len(nodes) - 30} more nodes.")

            context_parts.append(f"Relationships ({len(edges)}):")
            for edge in edges[:30]: # Limit edges
                src = edge.get('source', '')
                tgt = edge.get('target', '')
                rel = edge.get('relation', 'related_to')
                context_parts.append(f"- {src} --[{rel}]--> {tgt}")
            if len(edges) > 30:
                context_parts.append(f"... and {len(edges) - 30} more edges.")
            context_parts.append("-" * 40)

            # --- FINDINGS ---
            context_parts.append("KEY FINDINGS / RESULTS:")
            results = case_data.get('results', {})
            if results:
                # Convertir a string y truncar si es muy largo
                results_str = json.dumps(results, indent=2)
                if len(results_str) > 2000:
                    results_str = results_str[:2000] + "\n... [Truncated]"
                context_parts.append(results_str)
            else:
                context_parts.append("No specific findings recorded yet.")

            full_context = "\n".join(context_parts)
            
            # Truncado simple basado en caracteres (aprox 4 chars por token)
            max_chars = max_tokens * 4
            if len(full_context) > max_chars:
                full_context = full_context[:max_chars] + "\n...[CONTEXT TRUNCATED DUE TO LENGTH]..."

            return full_context
            
        except Exception as e:
            logger.error(f"Error building case context: {e}", exc_info=True)
            return f"Error building context for case {case_id}: {str(e)}"
