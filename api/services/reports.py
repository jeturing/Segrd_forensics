"""
Reports Service v4.4 - Generación de Reportes PDF
===================================================
Genera reportes técnicos, ejecutivos y de evidencia
Completamente orientado a casos con IA contextual
"""

import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid
import json

from api.services.llm_provider import get_llm_manager
from api.services.report_generator import report_generator
from api.config import settings

logger = logging.getLogger(__name__)


# ==================== TEMPLATES ====================

REPORT_TEMPLATES = {
    "technical": {
        "name": "Reporte Técnico",
        "sections": [
            "executive_summary",
            "scope",
            "methodology",
            "findings",
            "iocs",
            "timeline",
            "recommendations",
            "appendix"
        ],
        "classification": "CONFIDENTIAL"
    },
    "executive": {
        "name": "Reporte Ejecutivo",
        "sections": [
            "executive_summary",
            "impact_assessment",
            "risk_level",
            "key_findings",
            "business_impact",
            "recommendations",
            "next_steps"
        ],
        "classification": "INTERNAL"
    },
    "evidence": {
        "name": "Reporte de Evidencia",
        "sections": [
            "case_info",
            "evidence_chain",
            "artifacts",
            "timeline",
            "iocs",
            "raw_logs"
        ],
        "classification": "RESTRICTED"
    },
    "incident": {
        "name": "Reporte de Incidente",
        "sections": [
            "incident_summary",
            "detection",
            "containment",
            "eradication",
            "recovery",
            "lessons_learned",
            "recommendations"
        ],
        "classification": "CONFIDENTIAL"
    }
}

SUPPORTED_LANGUAGES = ["es", "en", "zh-CN", "zh-HK"]

SUMMARY_TEMPLATES = {
    "en": "Automated report built from {total_items} evidence artifacts. Risk score {risk_score}/100 ({risk_label}). OAuth apps: {oauth_total} total, {oauth_global} with tenant-wide consent. Users analyzed: {users_count}. Timeline events processed: {events_count}.",
    "es": "Reporte automático generado desde {total_items} artefactos de evidencia. Puntaje de riesgo {risk_score}/100 ({risk_label}). Apps OAuth: {oauth_total} en total, {oauth_global} con consentimiento global. Usuarios analizados: {users_count}. Eventos en línea de tiempo: {events_count}.",
    "zh-CN": "自动化报告基于 {total_items} 个证据项。风险分数 {risk_score}/100（{risk_label}）。OAuth 应用：{oauth_total} 个，其中 {oauth_global} 个具有租户范围授权。已分析用户 {users_count} 个，时间线事件 {events_count} 条。",
    "zh-HK": "自動化報告基於 {total_items} 個證據項。風險分數 {risk_score}/100（{risk_label}）。OAuth 應用：共 {oauth_total} 個，其中 {oauth_global} 個具備租戶層級授權。已分析用戶 {users_count} 個，時間線事件 {events_count} 條。"
}

RECOMMENDATION_SETS = {
    "en": [
        "Review and revoke OAuth apps with tenant-wide or legacy scopes (AllPrincipals/EWS).",
        "Validate consent history for users flagged as risky and force password reset if needed.",
        "Preserve raw evidence at {case_path} and export audit logs to immutable storage.",
        "Enable conditional access and app consent policies to block unverified publishers."
    ],
    "es": [
        "Revisar y revocar apps OAuth con consentimiento global o scopes heredados (AllPrincipals/EWS).",
        "Validar historial de consentimiento para usuarios marcados como riesgosos y forzar cambio de credenciales.",
        "Preservar evidencia raw en {case_path} y exportar logs de auditoría a almacenamiento inmutable.",
        "Habilitar acceso condicional y políticas de consentimiento para bloquear publishers no verificados."
    ],
    "zh-CN": [
        "审查并撤销具有租户级授权或旧版范围（AllPrincipals/EWS）的 OAuth 应用。",
        "检查被标记为高风险的用户同意历史，必要时强制重置凭据。",
        "在 {case_path} 保留原始证据并将审计日志导出到不可变存储。",
        "启用条件访问和应用同意策略以阻止未验证的发布者。"
    ],
    "zh-HK": [
        "審查並撤銷具有租戶層級授權或舊版範圍（AllPrincipals/EWS）的 OAuth 應用。",
        "檢查被標記為高風險的使用者同意歷史，必要時強制重設憑證。",
        "在 {case_path} 保留原始證據，並將稽核日誌匯出至不可變儲存。",
        "啟用條件式存取與應用同意政策以阻擋未驗證的發布者。"
    ]
}


class ReportsService:
    """Servicio de Generación de Reportes v4.4"""
    
    def __init__(self):
        self.reports: Dict[str, Dict] = {}
        self.templates = REPORT_TEMPLATES.copy()
        self.reports_dir = Path(settings.EVIDENCE_DIR) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        # v4.4: Índice por caso
        self.case_reports: Dict[str, List[str]] = {}
        # Directorios candidatos para evidencia (soporte demo y real)
        self.evidence_paths = [
            settings.EVIDENCE_DIR,
            settings.PROJECT_ROOT / "forensics-evidence",
            Path.cwd() / "forensics-evidence"
        ]
        
    async def create_report(
        self,
        title: str,
        report_type: str = "technical",
        case_id: str = None,  # v4.4: Debería ser obligatorio
        **kwargs
    ) -> Dict:
        """
        Crea un nuevo reporte
        
        Args:
            title: Título del reporte
            report_type: Tipo (technical, executive, evidence, incident)
            case_id: ID del caso asociado (OBLIGATORIO en v4.4)
            **kwargs: Campos adicionales
            
        Returns:
            Reporte creado
        """
        if not case_id:
            logger.warning("⚠️ Creando reporte sin case_id - esto será obligatorio en v4.5")
        
        report_id = f"RPT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        template = self.templates.get(report_type, self.templates["technical"])
        
        report = {
            "report_id": report_id,
            "title": title,
            "subtitle": kwargs.get("subtitle"),
            "report_type": report_type,
            "template_name": template["name"],
            "case_id": case_id,
            "investigation_id": kwargs.get("investigation_id"),
            "tenant_id": kwargs.get("tenant_id"),
            "status": "draft",
            "version": 1,
            "classification": kwargs.get("classification", template["classification"]),
            "sections": [],
            "findings": kwargs.get("findings", []),
            "recommendations": kwargs.get("recommendations", []),
            "iocs_included": kwargs.get("iocs", []),
            "executive_summary": kwargs.get("executive_summary"),
            "severity_assessment": kwargs.get("severity"),
            "mitre_techniques": kwargs.get("mitre", []),
            "affected_assets": kwargs.get("assets", []),
            "pdf_path": None,
            "pdf_generated_at": None,
            "llm_generated": False,
            "created_by": kwargs.get("created_by"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.reports[report_id] = report
        
        # v4.4: Registrar en índice de caso
        if case_id:
            if case_id not in self.case_reports:
                self.case_reports[case_id] = []
            self.case_reports[case_id].append(report_id)
        
        logger.info(f"📄 Reporte creado: {report_id} - {title} (caso: {case_id})")
        
        return report
    
    async def get_report(self, report_id: str) -> Optional[Dict]:
        """Obtiene un reporte por ID"""
        return self.reports.get(report_id)
    
    async def list_reports(
        self,
        case_id: Optional[str] = None,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Lista reportes con filtros"""
        reports = list(self.reports.values())
        
        if case_id:
            reports = [r for r in reports if r.get("case_id") == case_id]
        
        if report_type:
            reports = [r for r in reports if r.get("report_type") == report_type]
        
        if status:
            reports = [r for r in reports if r.get("status") == status]
        
        # Ordenar por fecha de creación (más reciente primero)
        reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return reports[:limit]
    
    async def update_report(self, report_id: str, updates: Dict) -> Optional[Dict]:
        """Actualiza un reporte"""
        if report_id not in self.reports:
            return None
        
        # No permitir modificar ciertos campos
        protected = ["report_id", "created_at", "created_by"]
        for field in protected:
            updates.pop(field, None)
        
        self.reports[report_id].update(updates)
        self.reports[report_id]["updated_at"] = datetime.utcnow().isoformat()
        
        return self.reports[report_id]
    
    async def delete_report(self, report_id: str) -> bool:
        """Elimina un reporte"""
        if report_id in self.reports:
            del self.reports[report_id]
            return True
        return False
    
    async def add_section(
        self,
        report_id: str,
        section_type: str,
        title: str,
        content: str,
        order: Optional[int] = None
    ) -> Optional[Dict]:
        """Agrega una sección al reporte"""
        if report_id not in self.reports:
            return None
        
        report = self.reports[report_id]
        sections = report.get("sections", [])
        
        section = {
            "id": f"sec_{uuid.uuid4().hex[:8]}",
            "type": section_type,
            "title": title,
            "content": content,
            "order": order if order is not None else len(sections),
            "created_at": datetime.utcnow().isoformat()
        }
        
        sections.append(section)
        sections.sort(key=lambda x: x.get("order", 0))
        
        report["sections"] = sections
        report["updated_at"] = datetime.utcnow().isoformat()
        
        return section
    
    async def generate_with_llm(
        self,
        report_id: str,
        case_data: Dict,
        sections_to_generate: Optional[List[str]] = None
    ) -> Dict:
        """
        Genera contenido del reporte usando LLM
        
        Args:
            report_id: ID del reporte
            case_data: Datos del caso para generar contenido
            sections_to_generate: Secciones específicas a generar
            
        Returns:
            Resultado de generación
        """
        if report_id not in self.reports:
            return {"error": "Report not found"}
        
        report = self.reports[report_id]
        template = self.templates.get(report.get("report_type"), self.templates["technical"])
        
        sections = sections_to_generate or template["sections"]
        generated_sections = []
        
        try:
            llm_manager = get_llm_manager()
            
            for section_type in sections:
                prompt = self._build_section_prompt(section_type, case_data, report)
                
                result = await llm_manager.generate(
                    prompt=prompt,
                    system_prompt="Eres un analista de seguridad senior redactando un reporte forense profesional. Usa formato Markdown. Sé conciso pero completo.",
                    max_tokens=1500,
                    temperature=0.4
                )
                
                if result.get("success"):
                    section = await self.add_section(
                        report_id=report_id,
                        section_type=section_type,
                        title=self._section_title(section_type),
                        content=result.get("content", "")
                    )
                    generated_sections.append(section_type)
            
            # Marcar como generado por LLM
            self.reports[report_id]["llm_generated"] = True
            self.reports[report_id]["llm_sections"] = generated_sections
            self.reports[report_id]["updated_at"] = datetime.utcnow().isoformat()
            
            return {
                "report_id": report_id,
                "sections_generated": generated_sections,
                "total": len(generated_sections)
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte con LLM: {e}")
            return {"error": str(e)}
    
    def _build_section_prompt(
        self,
        section_type: str,
        case_data: Dict,
        report: Dict
    ) -> str:
        """Construye prompt para una sección específica"""
        
        base_context = f"""
Caso: {case_data.get('case_id', 'N/A')}
Título: {report.get('title', 'N/A')}
Tipo: {report.get('report_type', 'technical')}
Severidad: {case_data.get('severity', 'N/A')}
Hallazgos: {json.dumps(case_data.get('findings', [])[:5], default=str)}
IOCs: {json.dumps(case_data.get('iocs', [])[:10], default=str)}
"""
        
        prompts = {
            "executive_summary": f"""
{base_context}

Genera un RESUMEN EJECUTIVO profesional que incluya:
- Descripción breve del incidente (2-3 oraciones)
- Impacto principal identificado
- Estado actual de la investigación
- Acciones críticas tomadas o pendientes

Máximo 300 palabras. Lenguaje claro para audiencia no técnica.""",

            "findings": f"""
{base_context}

Genera la sección de HALLAZGOS PRINCIPALES que incluya:
- Lista numerada de hallazgos clave
- Para cada hallazgo: descripción, evidencia, severidad
- Relación entre hallazgos si existe

Formato profesional con viñetas.""",

            "recommendations": f"""
{base_context}

Genera RECOMENDACIONES priorizadas:
1. Acciones inmediatas (24-48 horas)
2. Acciones a corto plazo (1-2 semanas)
3. Mejoras a largo plazo (1-3 meses)

Cada recomendación debe ser específica y accionable.""",

            "iocs": f"""
{base_context}

Genera la sección de INDICADORES DE COMPROMISO (IOCs) con:
- Tabla de IOCs organizados por tipo (IP, hash, domain, email)
- Contexto de cada IOC
- Recomendaciones de bloqueo

Formato tabla Markdown.""",

            "timeline": f"""
{base_context}

Genera una LÍNEA DE TIEMPO del incidente:
- Eventos clave en orden cronológico
- Formato: [FECHA/HORA] - Evento - Actor - Impacto
- Incluir gaps de tiempo significativos

Formato tabla Markdown.""",

            "methodology": f"""
{base_context}

Describe la METODOLOGÍA de investigación utilizada:
- Herramientas empleadas
- Fuentes de datos analizadas
- Técnicas de análisis
- Limitaciones del análisis""",

            "impact_assessment": f"""
{base_context}

Genera EVALUACIÓN DE IMPACTO:
- Impacto técnico (sistemas afectados)
- Impacto operacional (procesos afectados)
- Impacto financiero (estimado si es posible)
- Impacto reputacional (potencial)
- Impacto regulatorio (compliance)"""
        }
        
        return prompts.get(section_type, f"{base_context}\n\nGenera contenido para la sección: {section_type}")
    
    def _section_title(self, section_type: str) -> str:
        """Obtiene título legible de una sección"""
        titles = {
            "executive_summary": "Resumen Ejecutivo",
            "scope": "Alcance de la Investigación",
            "methodology": "Metodología",
            "findings": "Hallazgos Principales",
            "iocs": "Indicadores de Compromiso (IOCs)",
            "timeline": "Línea de Tiempo",
            "recommendations": "Recomendaciones",
            "appendix": "Anexos",
            "impact_assessment": "Evaluación de Impacto",
            "risk_level": "Nivel de Riesgo",
            "key_findings": "Hallazgos Clave",
            "business_impact": "Impacto en el Negocio",
            "next_steps": "Próximos Pasos",
            "case_info": "Información del Caso",
            "evidence_chain": "Cadena de Custodia",
            "artifacts": "Artefactos",
            "raw_logs": "Logs en Crudo",
            "incident_summary": "Resumen del Incidente",
            "detection": "Detección",
            "containment": "Contención",
            "eradication": "Erradicación",
            "recovery": "Recuperación",
            "lessons_learned": "Lecciones Aprendidas"
        }
        return titles.get(section_type, section_type.replace("_", " ").title())
    
    async def generate_pdf(self, report_id: str) -> Dict:
        """
        Genera PDF del reporte
        
        Args:
            report_id: ID del reporte
            
        Returns:
            Información del PDF generado
        """
        if report_id not in self.reports:
            return {"error": "Report not found"}
        
        report = self.reports[report_id]
        
        try:
            # Construir HTML
            html_content = self._build_html(report)
            
            # Guardar HTML
            html_path = self.reports_dir / f"{report_id}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Intentar generar PDF con weasyprint
            pdf_path = self.reports_dir / f"{report_id}.pdf"
            
            try:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(str(pdf_path))
                pdf_size = pdf_path.stat().st_size
            except ImportError:
                # Si weasyprint no está disponible, solo HTML
                logger.warning("⚠️ weasyprint no disponible, solo se genera HTML")
                pdf_path = None
                pdf_size = 0
            
            # Actualizar reporte
            report["html_path"] = str(html_path)
            report["pdf_path"] = str(pdf_path) if pdf_path else None
            report["pdf_size_bytes"] = pdf_size
            report["pdf_generated_at"] = datetime.utcnow().isoformat()
            report["status"] = "generated"
            report["updated_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"📄 PDF generado: {pdf_path or html_path}")
            
            return {
                "report_id": report_id,
                "pdf_path": str(pdf_path) if pdf_path else None,
                "html_path": str(html_path),
                "size_bytes": pdf_size,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando PDF: {e}")
            return {"error": str(e)}
    
    def _build_html(self, report: Dict) -> str:
        """Construye HTML del reporte"""
        
        sections_html = ""
        for section in report.get("sections", []):
            sections_html += f"""
            <section class="report-section">
                <h2>{section.get('title', 'Sección')}</h2>
                <div class="section-content">
                    {self._markdown_to_html(section.get('content', ''))}
                </div>
            </section>
            """
        
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{report.get('title', 'Reporte')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px;
        }}
        .header {{
            border-bottom: 3px solid #1a365d;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #1a365d;
            margin-bottom: 5px;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        .meta {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .meta-item {{
            display: inline-block;
            margin-right: 30px;
        }}
        .classification {{
            background: #dc2626;
            color: white;
            padding: 5px 15px;
            border-radius: 3px;
            font-weight: bold;
            float: right;
        }}
        .report-section {{
            margin-bottom: 30px;
            page-break-inside: avoid;
        }}
        .report-section h2 {{
            color: #1a365d;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background: #1a365d;
            color: white;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        .severity-critical {{ color: #dc2626; font-weight: bold; }}
        .severity-high {{ color: #ea580c; font-weight: bold; }}
        .severity-medium {{ color: #ca8a04; }}
        .severity-low {{ color: #16a34a; }}
        code {{
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }}
        pre {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <span class="classification">{report.get('classification', 'INTERNAL')}</span>
        <h1>{report.get('title', 'Reporte de Incidente')}</h1>
        <div class="subtitle">{report.get('subtitle', '')}</div>
    </div>
    
    <div class="meta">
        <span class="meta-item"><strong>ID:</strong> {report.get('report_id')}</span>
        <span class="meta-item"><strong>Caso:</strong> {report.get('case_id', 'N/A')}</span>
        <span class="meta-item"><strong>Tipo:</strong> {report.get('template_name', 'Técnico')}</span>
        <span class="meta-item"><strong>Fecha:</strong> {datetime.utcnow().strftime('%Y-%m-%d')}</span>
        <span class="meta-item"><strong>Versión:</strong> {report.get('version', 1)}</span>
    </div>
    
    {sections_html}
    
    <div class="footer">
        <p>Generado por Jeturing MCP Forensics v4.3</p>
        <p>Documento {report.get('classification', 'INTERNAL')} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
</body>
</html>
"""
        return html
    
    def _markdown_to_html(self, md_content: str) -> str:
        """Convierte Markdown básico a HTML"""
        import re
        
        if not md_content:
            return ""
        
        html = md_content
        
        # Headers
        html = re.sub(r'^### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Code blocks
        html = re.sub(r'```(\w+)?\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
        
        # Paragraphs
        html = re.sub(r'\n\n', '</p><p>', html)
        html = f'<p>{html}</p>'
        
        # Clean up
        html = html.replace('<p></p>', '')
        
        return html

    def _resolve_case_path(self, case_id: str) -> Optional[Path]:
        """Localiza la carpeta de evidencia para un caso (soporta demo y real)"""
        for base in self.evidence_paths:
            candidate = Path(base) / case_id
            if candidate.exists():
                return candidate
        return None

    def _load_json_file(self, path: Path) -> Any:
        """Carga un archivo JSON con manejo de errores silencioso"""
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo leer {path}: {e}")
            return None

    def _derive_risk_level(self, risk_score: Optional[int], findings: int) -> str:
        """Calcula nivel de riesgo combinado por score y hallazgos"""
        score = risk_score or 0
        if score >= 80 or findings > 10:
            return "critical"
        if score >= 60 or findings > 5:
            return "high"
        if score >= 30 or findings > 2:
            return "medium"
        return "low"

    def _localize_text(self, template_map: Dict[str, str], language: str, **kwargs) -> str:
        """Renderiza texto en el idioma solicitado con fallback a inglés"""
        lang = language if language in template_map else "en"
        template = template_map.get(lang) or template_map.get("en", "")
        try:
            return template.format(**kwargs)
        except Exception:
            # Fallback seguro en caso de claves faltantes
            return template_map.get("en", template).format(**kwargs)

    def _build_recommendations(self, language: str, case_path: Path) -> List[str]:
        """Genera recomendaciones localizadas"""
        recs = RECOMMENDATION_SETS.get(language) or RECOMMENDATION_SETS["en"]
        return [rec.format(case_path=str(case_path)) for rec in recs]

    def _collect_evidence_snapshot(self, case_id: str) -> Dict:
        """Carga evidencias crudas desde disco para un caso"""
        base = self._resolve_case_path(case_id)
        if not base:
            raise FileNotFoundError(f"No evidence folder found for case {case_id}")
        
        graph_path = base / "m365_graph"

        def _load_list(name: str) -> List[Any]:
            data = self._load_json_file(graph_path / f"{name}.json")
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "value" in data:
                value = data.get("value", [])
                return value if isinstance(value, list) else []
            return []

        return {
            "case_path": base,
            "graph_path": graph_path,
            "summary": self._load_json_file(graph_path / "investigation_summary.json") or {},
            "risky_signins": _load_list("risky_signins"),
            "risky_users": _load_list("risky_users"),
            "signin_logs": _load_list("signin_logs"),
            "audit_logs": _load_list("audit_logs"),
            "oauth_consents": _load_list("oauth_consents"),
            "users": _load_list("users_analysis"),
            "inbox_rules": _load_list("inbox_rules")
        }

    def _build_timeline(self, snapshot: Dict) -> List[Dict]:
        """Construye timeline consolidado a partir de evidencias"""
        events = []
        for signin in snapshot.get("risky_signins", []):
            ts = signin.get("createdDateTime") or signin.get("eventDateTime") or signin.get("timestamp")
            events.append({
                "timestamp": ts or datetime.utcnow().isoformat(),
                "description": f"Risky sign-in {signin.get('userPrincipalName', 'unknown')} from {signin.get('ipAddress', 'unknown')}",
                "severity": signin.get("riskLevelDuringSignIn") or signin.get("riskLevel") or "medium"
            })

        for audit in snapshot.get("audit_logs", []):
            ts = audit.get("activityDateTime") or audit.get("CreationTime") or audit.get("timestamp")
            desc = audit.get("activityDisplayName") or audit.get("operationType") or audit.get("Operation") or "Audit event"
            events.append({
                "timestamp": ts or datetime.utcnow().isoformat(),
                "description": desc,
                "severity": audit.get("severity") or "low"
            })

        summary = snapshot.get("summary", {})
        started = summary.get("started_at")
        completed = summary.get("completed_at")
        if started:
            events.append({"timestamp": started, "description": "Investigación iniciada", "severity": "info"})
        if completed:
            events.append({"timestamp": completed, "description": "Investigación completada", "severity": "info"})

        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return events[:50]

    def _build_findings(self, snapshot: Dict, summary_block: Dict) -> List[Dict]:
        """Extrae hallazgos técnicos relevantes"""
        findings: List[Dict] = []
        completed_at = snapshot.get("summary", {}).get("completed_at") or datetime.utcnow().isoformat()

        # Hallazgos por apps riesgosas en el resumen
        for app in summary_block.get("risky_apps", []):
            findings.append({
                "title": f"OAuth app con riesgo: {app}",
                "description": "Aplicación marcada como riesgosa en el resumen de investigación",
                "severity": "high",
                "timestamp": completed_at
            })

        # Hallazgos de consentimientos OAuth sospechosos
        oauth_entries = snapshot.get("oauth_consents", [])
        suspicious_oauth = []
        for app in oauth_entries:
            scope_text = app.get("scope", "") or ""
            consent = app.get("consentType", "Principal")
            is_global = consent == "AllPrincipals"
            legacy_scope = "EWS.AccessAsUser.All" in scope_text or "offline_access" in scope_text
            if is_global or legacy_scope:
                suspicious_oauth.append((app, "high"))
            elif scope_text:
                suspicious_oauth.append((app, "medium"))

        for app, sev in suspicious_oauth[:10]:
            findings.append({
                "title": f"Consentimiento OAuth: {app.get('appDisplayName', 'App desconocida')}",
                "description": f"{app.get('consentType', 'Principal')} • Scopes: {app.get('scope', 'N/A')}",
                "severity": sev,
                "timestamp": completed_at
            })

        # Usuarios marcados como riesgosos
        for user in snapshot.get("risky_users", [])[:5]:
            findings.append({
                "title": f"Usuario riesgoso: {user.get('userPrincipalName', user.get('principalName', 'desconocido'))}",
                "description": user.get("riskDetail") or user.get("riskState") or "Marcado como riesgoso por el proveedor de identidad",
                "severity": user.get("riskLevel", "medium"),
                "timestamp": user.get("riskLastUpdatedDateTime") or completed_at
            })

        # Intentos de inicio de sesión riesgosos
        for signin in snapshot.get("risky_signins", [])[:5]:
            findings.append({
                "title": f"Inicio de sesión riesgoso para {signin.get('userPrincipalName', 'usuario')}",
                "description": f"IP {signin.get('ipAddress', 'N/A')} • Detalle: {signin.get('riskDetail', 'riesgo detectado')}",
                "severity": signin.get("riskLevelDuringSignIn", "medium"),
                "timestamp": signin.get("createdDateTime") or signin.get("timestamp") or completed_at
            })

        return findings

    def _build_iocs(self, snapshot: Dict) -> List[Dict]:
        """Crea lista de IOCs extraídos de evidencia (IPs principalmente)"""
        iocs = []
        seen = set()
        for source in ["risky_signins", "signin_logs"]:
            for entry in snapshot.get(source, []):
                ip = entry.get("ipAddress") or entry.get("clientIpAddress")
                if ip and ip not in seen:
                    seen.add(ip)
                    iocs.append({
                        "type": "ip",
                        "value": ip,
                        "severity": entry.get("riskLevelDuringSignIn") or entry.get("riskLevel") or "medium",
                        "source": source
                    })
        return iocs[:25]

    async def _build_case_dataset(self, case_id: str, language: str) -> Dict:
        """Prepara dataset estructurado desde evidencias para el generador multi-idioma"""
        snapshot = self._collect_evidence_snapshot(case_id)
        summary_data = snapshot.get("summary", {})
        summary_block = summary_data.get("summary", summary_data.get("summary_data", {}))

        risk_score = summary_block.get("risk_score") or summary_data.get("risk_score") or 0
        oauth_entries = snapshot.get("oauth_consents", [])
        oauth_global = len([app for app in oauth_entries if app.get("consentType") == "AllPrincipals"])

        evidence_counts = {
            "oauth": len(oauth_entries),
            "risky_signins": len(snapshot.get("risky_signins", [])),
            "risky_users": len(snapshot.get("risky_users", [])),
            "signin_logs": len(snapshot.get("signin_logs", [])),
            "audit_logs": len(snapshot.get("audit_logs", []))
        }
        total_items = sum(evidence_counts.values()) or len(oauth_entries) or 1

        timeline = self._build_timeline(snapshot)
        findings = self._build_findings(snapshot, summary_block)
        iocs = self._build_iocs(snapshot)
        risk_level = self._derive_risk_level(risk_score, len(findings))
        risk_label = report_generator.translate(risk_level if risk_level in ["critical", "high", "medium", "low"] else "medium", language)

        summary_text = self._localize_text(
            SUMMARY_TEMPLATES,
            language,
            total_items=total_items,
            risk_score=risk_score,
            risk_label=risk_label,
            oauth_total=evidence_counts["oauth"],
            oauth_global=oauth_global,
            users_count=len(snapshot.get("users", [])),
            events_count=len(timeline)
        )

        recommendations = self._build_recommendations(language, snapshot["case_path"])

        return {
            "case_id": case_id,
            "summary": summary_text,
            "findings": findings,
            "iocs": iocs,
            "timeline": timeline,
            "recommendations": recommendations,
            "tools_used": ["M365 Graph", "Evidence Parser"],
            "risk_level": risk_level,
            "analyst": "MCP Auto Reporter",
            "m365_results": summary_block,
            "metadata": {
                "evidence_counts": evidence_counts,
                "oauth_global": oauth_global,
                "evidence_path": str(snapshot["case_path"])
            }
        }

    async def _generate_file_from_dataset(
        self,
        report_id: str,
        case_id: str,
        report_type: str,
        format: str,
        language: str,
        dataset: Dict
    ) -> Dict:
        """Usa el generador multi-idioma para producir el archivo final"""
        generator_format = "markdown" if format == "md" else format
        generated = await report_generator.generate_investigation_report(
            investigation_id=case_id,
            investigation_data=dataset,
            language=language,
            format=generator_format
        )

        source_path = Path(generated["file_path"])
        target_dir = self.reports_dir / case_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # Si falló PDF, respetar la extensión real para no confundir al usuario
        output_ext = source_path.suffix.lstrip(".") or generator_format
        target_path = target_dir / f"{report_type}_{report_id}_{language}.{output_ext}"
        shutil.copy(source_path, target_path)

        return {
            "path": target_path,
            "size": target_path.stat().st_size if target_path.exists() else generated.get("file_size_bytes", 0),
            "format": output_ext
        }
    
    async def _enrich_with_llm(self, dataset: Dict, language: str) -> Dict:
        """
        v4.6: Enriquece el dataset con análisis LLM (Purple Team)
        Si el LLM falla, retorna el dataset original sin modificar
        """
        try:
            llm_manager = get_llm_manager()
            if not llm_manager:
                logger.warning("⚠️ LLM Manager no disponible")
                return dataset
            
            enriched = dataset.copy()
            
            # Enriquecer resumen con análisis de contexto
            if dataset.get("findings"):
                findings_text = "\n".join([
                    f"- {f.get('title', 'Sin título')}: {f.get('description', '')}" 
                    for f in dataset.get("findings", [])[:10]
                ])
                
                prompt = f"""Analiza los siguientes hallazgos de seguridad y proporciona un análisis ejecutivo breve (máximo 3 párrafos) en {'español' if language == 'es' else 'inglés'}:

{findings_text}

Incluye:
1. Nivel de riesgo general
2. Impacto potencial en el negocio
3. Acciones inmediatas recomendadas"""

                try:
                    analysis = await llm_manager.generate_text(prompt, max_tokens=500)
                    if analysis:
                        enriched["llm_analysis"] = analysis
                        enriched["summary"] = f"{dataset.get('summary', '')}\n\n**Análisis Purple Team:**\n{analysis}"
                        logger.info("🧠 Análisis LLM agregado al reporte")
                except Exception as gen_err:
                    logger.warning(f"⚠️ Error generando análisis: {gen_err}")
            
            # Enriquecer recomendaciones
            if dataset.get("iocs"):
                ioc_count = len(dataset.get("iocs", []))
                ioc_types = set([ioc.get("type", "unknown") for ioc in dataset.get("iocs", [])])
                
                # Añadir recomendación basada en IOCs
                if ioc_count > 0:
                    ioc_recommendation = {
                        "es": f"Se identificaron {ioc_count} indicadores de compromiso ({', '.join(ioc_types)}). Se recomienda bloquear estos IOCs en los sistemas de seguridad perimetral.",
                        "en": f"Identified {ioc_count} indicators of compromise ({', '.join(ioc_types)}). Recommend blocking these IOCs in perimeter security systems."
                    }
                    current_recs = enriched.get("recommendations", [])
                    if isinstance(current_recs, list):
                        current_recs.append(ioc_recommendation.get(language, ioc_recommendation["en"]))
                        enriched["recommendations"] = current_recs
            
            enriched["llm_enriched"] = True
            return enriched
            
        except Exception as e:
            logger.error(f"❌ Error en enriquecimiento LLM: {e}")
            return dataset
    
    async def get_templates(self, report_type: Optional[str] = None) -> List[Dict]:
        """Obtiene plantillas disponibles (con filtro opcional)"""
        templates = self.templates.items()
        if report_type:
            templates = [(tid, tdata) for tid, tdata in templates if tdata.get("report_type", tid) == report_type]

        return [
            {
                "id": tid,
                "name": tdata["name"],
                "sections": tdata["sections"],
                "classification": tdata["classification"]
            }
            for tid, tdata in templates
        ]
    
    async def get_report_stats(self) -> Dict:
        """Obtiene estadísticas de reportes"""
        reports = list(self.reports.values())
        
        by_type = {}
        by_status = {}
        
        for r in reports:
            rtype = r.get("report_type", "unknown")
            by_type[rtype] = by_type.get(rtype, 0) + 1
            
            status = r.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_reports": len(reports),
            "by_type": by_type,
            "by_status": by_status,
            "llm_generated": len([r for r in reports if r.get("llm_generated")]),
            "pdf_generated": len([r for r in reports if r.get("pdf_path")])
        }

    # ==================== MÉTODOS ADICIONALES PARA RUTAS ====================

    async def get_stats(self) -> Dict:
        """Alias para get_report_stats"""
        return await self.get_report_stats()

    async def create_report_record(
        self,
        report_id: str,
        case_id: str,
        report_type: str,
        format: str,
        title: Optional[str] = None,
        language: str = "es",
        options: Dict = None,
        parent_report_id: Optional[str] = None,
        auto_ingest: bool = False
    ) -> Dict:
        """Crea un registro de reporte (antes de generación)"""
        report = {
            "report_id": report_id,
            "case_id": case_id,
            "report_type": report_type,
            "format": format,
            "language": language if language in SUPPORTED_LANGUAGES else "en",
            "title": title or f"{report_type.title()} Report - {case_id}",
            "status": "pending",
            "options": options or {},
            "auto_ingest": auto_ingest,
            "parent_report_id": parent_report_id,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "file_path": None,
            "file_size": None,
            "error": None
        }
        
        self.reports[report_id] = report
        return report

    async def generate_report(
        self,
        report_id: str,
        case_id: str,
        report_type: str,
        format: str = "pdf",
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
        exclude_sections: Optional[List[str]] = None,
        options: Dict = None,
        use_llm: bool = True,
        include_raw: bool = False,
        language: str = "es",
        auto_ingest: bool = False
    ) -> Dict:
        """Genera un reporte completo con progreso en tiempo real"""
        try:
            options = options or {}
            target_language = language if language in SUPPORTED_LANGUAGES else "en"
            auto_mode = auto_ingest or options.get("auto_ingest") or self.reports.get(report_id, {}).get("auto_ingest")

            # Helper para actualizar progreso
            def update_progress(progress: int, step: str):
                if report_id in self.reports:
                    self.reports[report_id]["progress"] = progress
                    self.reports[report_id]["current_step"] = step

            # v4.6: Verificar disponibilidad de LLM
            llm_available = False
            llm_mode = "template"
            if use_llm:
                try:
                    llm_manager = get_llm_manager()
                    llm_available = await llm_manager.is_available() if hasattr(llm_manager, 'is_available') else False
                    if llm_available:
                        llm_mode = "llm_enriched"
                        logger.info("🧠 LLM disponible - Enriqueciendo reporte con agentes Purple Team")
                    else:
                        logger.warning("⚠️ LLM no disponible - Usando template sin enriquecimiento")
                except Exception as llm_err:
                    logger.warning(f"⚠️ Error verificando LLM: {llm_err} - Usando fallback template")
                    llm_available = False

            # Actualizar estado inicial
            if report_id in self.reports:
                self.reports[report_id]["status"] = "generating"
                self.reports[report_id]["started_at"] = datetime.utcnow().isoformat()
                self.reports[report_id]["language"] = target_language
                self.reports[report_id]["auto_ingest"] = auto_mode
                self.reports[report_id]["format"] = format
                self.reports[report_id]["llm_mode"] = llm_mode
                update_progress(5, f"Iniciando generación ({llm_mode})...")

            # Generación automática basada en evidencia
            if auto_mode:
                update_progress(10, "Recopilando datos del caso...")
                dataset = await self._build_case_dataset(case_id, target_language)
                
                # v4.6: Si LLM está disponible, enriquecer el dataset
                if llm_available and use_llm:
                    try:
                        update_progress(30, "🧠 Purple Team analizando hallazgos...")
                        dataset = await self._enrich_with_llm(dataset, target_language)
                        update_progress(40, "Generando archivo enriquecido...")
                    except Exception as llm_err:
                        logger.warning(f"⚠️ Error en enriquecimiento LLM: {llm_err} - Continuando con template")
                        update_progress(40, "Generando archivo (fallback template)...")
                else:
                    update_progress(40, "Generando archivo desde template...")
                
                generated = await self._generate_file_from_dataset(
                    report_id=report_id,
                    case_id=case_id,
                    report_type=report_type,
                    format=format,
                    language=target_language,
                    dataset=dataset
                )

                update_progress(90, "Finalizando...")
                if report_id in self.reports:
                    self.reports[report_id]["status"] = "completed"
                    self.reports[report_id]["completed_at"] = datetime.utcnow().isoformat()
                    self.reports[report_id]["file_path"] = str(generated["path"])
                    self.reports[report_id]["file_size"] = generated["size"]
                    self.reports[report_id]["format"] = generated["format"]
                    self.reports[report_id]["llm_generated"] = False
                    update_progress(100, "Completado")

                logger.info(f"📄 Reporte auto-generado: {report_id} -> {generated['path']}")
                return self.reports.get(report_id, generated)
            
            # Obtener template
            update_progress(10, "Cargando plantilla...")
            template = self.templates.get(report_type, self.templates["technical"])
            
            # Filtrar secciones
            sections = template["sections"].copy()
            if include_sections:
                sections = [s for s in sections if s in include_sections]
            if exclude_sections:
                sections = [s for s in sections if s not in exclude_sections]
            
            # Generar contenido para cada sección con progreso
            content = {}
            total_sections = len(sections)
            for idx, section in enumerate(sections):
                progress = 15 + int((idx / total_sections) * 60)  # 15-75%
                update_progress(progress, f"Generando sección: {section}...")
                content[section] = await self._generate_section_content(
                    section, case_id, use_llm
                )
            
            # Generar archivo
            update_progress(80, "Creando archivo...")
            report_dir = self.reports_dir / case_id
            report_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{report_type}_{report_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
            file_path = report_dir / filename
            
            update_progress(85, f"Generando {format.upper()}...")
            if format == "pdf":
                await self._generate_pdf(str(file_path), title or f"Report {report_id}", content, template)
            elif format == "html":
                html = await self._generate_html(title or f"Report {report_id}", content, template)
                with open(file_path, "w") as f:
                    f.write(html)
            elif format == "json":
                with open(file_path, "w") as f:
                    json.dump({"title": title, "content": content}, f, indent=2, default=str)
            elif format in ["md", "markdown"]:
                with open(file_path, "w") as f:
                    f.write(f"# {title or report_type.title()} ({case_id})\n\n")
                    for section_name, section_content in content.items():
                        f.write(f"## {section_name}\n")
                        f.write(section_content.get("content", ""))
                        f.write("\n\n")
            else:
                with open(file_path, "w") as f:
                    json.dump({"title": title, "content": content}, f, indent=2, default=str)
            
            # Actualizar registro final
            update_progress(95, "Finalizando...")
            if report_id in self.reports:
                self.reports[report_id]["status"] = "completed"
                self.reports[report_id]["completed_at"] = datetime.utcnow().isoformat()
                self.reports[report_id]["file_path"] = str(file_path)
                self.reports[report_id]["file_size"] = file_path.stat().st_size if file_path.exists() else 0
                self.reports[report_id]["language"] = target_language
                self.reports[report_id]["auto_ingest"] = False
                update_progress(100, "Completado")
            
            logger.info(f"📄 Reporte generado: {report_id} -> {file_path}")
            return self.reports.get(report_id, {})
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte {report_id}: {e}")
            if report_id in self.reports:
                self.reports[report_id]["status"] = "failed"
                self.reports[report_id]["error"] = str(e)
            return {"error": str(e)}

    async def _generate_section_content(self, section: str, case_id: str, use_llm: bool) -> Dict:
        """Genera contenido para una sección específica"""
        # Contenido placeholder - en producción se obtendría del caso
        return {
            "title": section.replace("_", " ").title(),
            "content": f"Contenido de la sección {section} para el caso {case_id}",
            "generated_at": datetime.utcnow().isoformat()
        }

    async def get_case_reports(
        self,
        case_id: str,
        filters: Dict = None,
        limit: int = 20
    ) -> List[Dict]:
        """Obtiene reportes de un caso"""
        reports = []
        for report in self.reports.values():
            if report.get("case_id") == case_id:
                if filters:
                    if filters.get("report_type") and report.get("report_type") != filters["report_type"]:
                        continue
                    if filters.get("status") and report.get("status") != filters["status"]:
                        continue
                reports.append(report)
        
        # Ordenar por fecha y limitar
        reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return reports[:limit]

    async def get_report_status(self, report_id: str) -> Optional[Dict]:
        """Obtiene estado de generación de un reporte"""
        report = self.reports.get(report_id)
        if not report:
            return None
        
        status = report.get("status", "pending")
        progress = report.get("progress", 0)
        current_step = report.get("current_step", "Iniciando...")
        
        # Calcular progreso basado en status si no hay progress explícito
        if progress == 0:
            if status == "completed":
                progress = 100
                current_step = "Completado"
            elif status == "generating":
                progress = 50
                current_step = "Generando contenido..."
            elif status == "failed":
                progress = 0
                current_step = "Error en generación"
        
        return {
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "started_at": report.get("started_at"),
            "completed_at": report.get("completed_at"),
            "estimated_completion": report.get("estimated_completion"),
            "file_path": report.get("file_path") if status == "completed" else None,
            "download_url": f"/reports/{report_id}/download" if status == "completed" else None,
            "share_url": f"/reports/{report_id}/share" if status == "completed" else None
        }

    async def get_template(self, template_id: str) -> Optional[Dict]:
        """Obtiene un template específico"""
        if template_id in self.templates:
            return {
                "id": template_id,
                **self.templates[template_id]
            }
        return None

    async def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        report_type: str,
        sections: List[Dict],
        header_template: Optional[str] = None,
        footer_template: Optional[str] = None,
        css_styles: Optional[str] = None
    ) -> Dict:
        """Crea un template personalizado"""
        template = {
            "name": name,
            "description": description,
            "report_type": report_type,
            "sections": [s.get("id", s) if isinstance(s, dict) else s for s in sections],
            "classification": "CUSTOM",
            "header_template": header_template,
            "footer_template": footer_template,
            "css_styles": css_styles,
            "custom": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.templates[template_id] = template
        return template

    async def delete_template(self, template_id: str) -> bool:
        """Elimina un template personalizado"""
        if template_id in self.templates:
            if self.templates[template_id].get("custom"):
                del self.templates[template_id]
                return True
        return False

    async def regenerate_report(
        self,
        original_report_id: str,
        new_report_id: str,
        format: Optional[str] = None,
        options: Dict = None
    ) -> Dict:
        """Regenera un reporte existente"""
        original = self.reports.get(original_report_id)
        if not original:
            return {"error": "Original report not found"}
        
        return await self.generate_report(
            report_id=new_report_id,
            case_id=original["case_id"],
            report_type=original["report_type"],
            format=format or original["format"],
            title=original.get("title"),
            options={**original.get("options", {}), **(options or {})},
            language=original.get("language", "es"),
            auto_ingest=original.get("auto_ingest", False)
        )

    async def generate_preview(
        self,
        case_id: str,
        report_type: str,
        include_sections: Optional[List[str]] = None,
        exclude_sections: Optional[List[str]] = None
    ) -> Dict:
        """Genera preview de un reporte con HTML completo y estilizado"""
        template = self.templates.get(report_type, self.templates["technical"])
        
        sections = template["sections"].copy()
        if include_sections:
            sections = [s for s in sections if s in include_sections]
        if exclude_sections:
            sections = [s for s in sections if s not in exclude_sections]
        
        # Obtener datos del caso
        case_data = await self._get_case_data(case_id)
        
        # Generar contenido para cada sección
        section_contents = {}
        for section in sections:
            section_contents[section] = await self._generate_section_preview(section, case_data, report_type)
        
        # Generar HTML completo con estilos
        html = self._build_preview_html(
            template_name=template['name'],
            case_id=case_id,
            case_data=case_data,
            sections=sections,
            section_contents=section_contents
        )
        
        return {
            "html": html,
            "sections": sections,
            "estimated_pages": max(1, len(sections) * 2)
        }
    
    async def _get_case_data(self, case_id: str) -> Dict:
        """Obtiene datos del caso para el preview"""
        # Importar aquí para evitar circular imports
        from api.database import get_db_context
        from sqlalchemy import text
        
        case_data = {
            "case_id": case_id,
            "title": "Investigación Forense",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "classification": "Confidencial",
            "priority": "medium",
            "type": "forensic",
            "description": "",
            "iocs": [],
            "timeline_events": [],
            "evidence_files": [],
            "findings": []
        }
        
        try:
            with get_db_context() as db:
                # Primero intentar tabla cases
                result = db.execute(text("""
                    SELECT case_id, title, description, status, priority, 
                           threat_type, created_at, updated_at
                    FROM cases 
                    WHERE case_id = :case_id
                """), {"case_id": case_id})
                row = result.fetchone()
                
                if row:
                    case_data.update({
                        "case_id": row[0],
                        "title": row[1] or "Investigación Forense",
                        "description": row[2] or "",
                        "status": row[3] or "active",
                        "priority": row[4] or "medium",
                        "type": row[5] or "forensic",
                        "created_at": row[6],
                        "updated_at": row[7]
                    })
                else:
                    # Fallback a tabla investigations
                    result = db.execute(text("""
                        SELECT id, title, description, status, severity, 
                               investigation_type, created_at, updated_at
                        FROM investigations 
                        WHERE id = :case_id
                    """), {"case_id": case_id})
                    row = result.fetchone()
                    if row:
                        case_data.update({
                            "case_id": row[0],
                            "title": row[1] or "Investigación Forense",
                            "description": row[2] or "",
                            "status": row[3] or "active",
                            "priority": row[4] or "medium",
                            "type": row[5] or "forensic",
                            "created_at": row[6],
                            "updated_at": row[7]
                        })
                
                # Obtener IOCs
                result = db.execute(text("""
                    SELECT id, ioc_type, value, severity, source, description
                    FROM iocs WHERE case_id = :case_id LIMIT 20
                """), {"case_id": case_id})
                case_data["iocs"] = [
                    {
                        "id": r[0], "type": r[1], "value": r[2], 
                        "threat_level": r[3], "source": r[4], "description": r[5]
                    } for r in result.fetchall()
                ]
                
                # Obtener eventos de timeline (usar investigation_timeline)
                result = db.execute(text("""
                    SELECT id, timestamp, event_type, title, description, source
                    FROM investigation_timeline WHERE investigation_id = :case_id 
                    ORDER BY timestamp DESC LIMIT 20
                """), {"case_id": case_id})
                case_data["timeline_events"] = [
                    {
                        "id": r[0], "timestamp": r[1], "type": r[2], 
                        "title": r[3], "description": r[4], "source": r[5]
                    } for r in result.fetchall()
                ]
        except Exception as e:
            logger.warning(f"Error getting case data for preview: {e}")
        
        return case_data
    
    async def _generate_section_preview(self, section: str, case_data: Dict, report_type: str) -> str:
        """Genera contenido preview para una sección específica"""
        case_id = case_data.get("case_id", "N/A")
        title = case_data.get("title", "Investigación")
        
        section_generators = {
            "executive_summary": lambda: f"""
                <p><strong>Caso:</strong> {case_id}</p>
                <p><strong>Clasificación:</strong> {case_data.get('classification', 'Confidencial')}</p>
                <p><strong>Estado:</strong> {case_data.get('status', 'En progreso')}</p>
                <p>Este reporte presenta los hallazgos de la investigación forense "{title}". 
                   Se han identificado {len(case_data.get('iocs', []))} indicadores de compromiso 
                   y {len(case_data.get('timeline_events', []))} eventos en la línea de tiempo.</p>
            """,
            "impact_assessment": lambda: f"""
                <p><strong>Prioridad:</strong> {case_data.get('priority', 'Media').capitalize()}</p>
                <p><strong>Tipo de Incidente:</strong> {case_data.get('type', 'Forense').capitalize()}</p>
                <p>El impacto de este incidente se evalúa considerando los activos comprometidos,
                   la exposición de datos sensibles y el tiempo de permanencia del atacante.</p>
                <ul>
                    <li>IOCs identificados: {len(case_data.get('iocs', []))}</li>
                    <li>Eventos en timeline: {len(case_data.get('timeline_events', []))}</li>
                </ul>
            """,
            "risk_level": lambda: f"""
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="width:100px;height:30px;background:linear-gradient(to right,#22c55e,#eab308,#f97316,#ef4444);border-radius:4px;"></div>
                    <span style="font-weight:bold;">Nivel de Riesgo: {case_data.get('priority', 'Medio').upper()}</span>
                </div>
                <p style="margin-top:10px;">La evaluación de riesgo se basa en la severidad de los IOCs detectados
                   y el potencial impacto en la organización.</p>
            """,
            "key_findings": lambda: self._generate_findings_preview(case_data),
            "business_impact": lambda: """
                <p><strong>Impacto Operacional:</strong> Se recomienda evaluar la continuidad de operaciones.</p>
                <p><strong>Impacto Financiero:</strong> Pendiente de cuantificación.</p>
                <p><strong>Impacto Reputacional:</strong> Depende de la naturaleza de los datos expuestos.</p>
            """,
            "recommendations": lambda: """
                <ol>
                    <li>Implementar controles de acceso adicionales</li>
                    <li>Revisar y actualizar políticas de seguridad</li>
                    <li>Monitoreo continuo de los IOCs identificados</li>
                    <li>Capacitación en seguridad para el personal</li>
                    <li>Revisión de logs y eventos de auditoría</li>
                </ol>
            """,
            "next_steps": lambda: """
                <ul>
                    <li>✅ Contención del incidente</li>
                    <li>🔄 Erradicación de amenazas</li>
                    <li>⏳ Recuperación de sistemas</li>
                    <li>⏳ Lecciones aprendidas</li>
                </ul>
            """,
            "scope": lambda: f"""
                <p><strong>Período de análisis:</strong> Últimos 30 días</p>
                <p><strong>Sistemas analizados:</strong> {case_data.get('description', 'Sistemas afectados')}</p>
                <p><strong>Evidencia recolectada:</strong> {len(case_data.get('evidence_files', []))} archivos</p>
            """,
            "methodology": lambda: """
                <p>La investigación sigue las siguientes fases del proceso forense:</p>
                <ol>
                    <li><strong>Identificación:</strong> Detección de indicios de compromiso</li>
                    <li><strong>Preservación:</strong> Recolección y cadena de custodia</li>
                    <li><strong>Análisis:</strong> Examen de evidencias</li>
                    <li><strong>Documentación:</strong> Registro de hallazgos</li>
                    <li><strong>Presentación:</strong> Elaboración de reportes</li>
                </ol>
            """,
            "ioc_summary": lambda: self._generate_iocs_preview(case_data),
            "timeline": lambda: self._generate_timeline_preview(case_data),
            "incident_summary": lambda: f"""
                <p><strong>ID de Incidente:</strong> {case_id}</p>
                <p><strong>Fecha de Detección:</strong> {case_data.get('created_at', 'N/A')}</p>
                <p><strong>Estado Actual:</strong> {case_data.get('status', 'En progreso')}</p>
                <p>{case_data.get('description', 'Descripción del incidente pendiente de completar.')}</p>
            """,
            "detection": lambda: """
                <p><strong>Método de Detección:</strong> Monitoreo de seguridad</p>
                <p><strong>Fuente:</strong> Sistema de detección de amenazas</p>
                <p>Los indicadores iniciales fueron identificados mediante correlación de eventos 
                   y análisis de comportamiento anómalo.</p>
            """,
            "containment": lambda: """
                <h4>Acciones de Contención</h4>
                <ul>
                    <li>Aislamiento de sistemas afectados</li>
                    <li>Bloqueo de comunicaciones maliciosas</li>
                    <li>Preservación de evidencia</li>
                </ul>
            """,
            "eradication": lambda: """
                <h4>Proceso de Erradicación</h4>
                <ul>
                    <li>Eliminación de artefactos maliciosos</li>
                    <li>Parcheo de vulnerabilidades</li>
                    <li>Actualización de credenciales</li>
                </ul>
            """,
            "recovery": lambda: """
                <h4>Plan de Recuperación</h4>
                <ul>
                    <li>Restauración de sistemas</li>
                    <li>Verificación de integridad</li>
                    <li>Monitoreo post-incidente</li>
                </ul>
            """,
            "lessons_learned": lambda: """
                <p>Las lecciones aprendidas de este incidente incluyen:</p>
                <ul>
                    <li>Mejoras en la detección temprana</li>
                    <li>Optimización de procedimientos de respuesta</li>
                    <li>Necesidad de capacitación adicional</li>
                </ul>
            """
        }
        
        generator = section_generators.get(section)
        if generator:
            return generator()
        
        # Sección genérica
        return f"<p>Contenido de la sección <strong>{section.replace('_', ' ').title()}</strong> " \
               f"para el caso {case_id}.</p>"
    
    def _generate_findings_preview(self, case_data: Dict) -> str:
        """Genera preview de hallazgos clave"""
        iocs = case_data.get('iocs', [])
        if not iocs:
            return "<p>No se han registrado hallazgos específicos aún.</p>"
        
        html = "<table style='width:100%;border-collapse:collapse;'>"
        html += "<tr style='background:#1e293b;'><th style='padding:8px;text-align:left;border:1px solid #334155;'>Tipo</th>"
        html += "<th style='padding:8px;text-align:left;border:1px solid #334155;'>Valor</th>"
        html += "<th style='padding:8px;text-align:left;border:1px solid #334155;'>Severidad</th></tr>"
        
        for ioc in iocs[:5]:
            severity_color = {
                'critical': '#ef4444', 'high': '#f97316', 
                'medium': '#eab308', 'low': '#22c55e'
            }.get(ioc.get('threat_level', 'medium'), '#6b7280')
            
            html += f"<tr style='background:#0f172a;'>"
            html += f"<td style='padding:8px;border:1px solid #334155;'>{ioc.get('type', 'N/A')}</td>"
            html += f"<td style='padding:8px;border:1px solid #334155;font-family:monospace;'>{ioc.get('value', 'N/A')}</td>"
            html += f"<td style='padding:8px;border:1px solid #334155;'><span style='background:{severity_color};padding:2px 8px;border-radius:4px;'>{ioc.get('threat_level', 'N/A')}</span></td>"
            html += "</tr>"
        
        html += "</table>"
        
        if len(iocs) > 5:
            html += f"<p style='margin-top:10px;color:#94a3b8;'>... y {len(iocs) - 5} hallazgos más</p>"
        
        return html
    
    def _generate_iocs_preview(self, case_data: Dict) -> str:
        """Genera preview de IOCs"""
        iocs = case_data.get('iocs', [])
        if not iocs:
            return "<p>No se han identificado IOCs en esta investigación.</p>"
        
        html = f"<p><strong>Total de IOCs:</strong> {len(iocs)}</p>"
        html += "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px;'>"
        
        # Contar por tipo
        type_counts = {}
        for ioc in iocs:
            t = ioc.get('type', 'other')
            type_counts[t] = type_counts.get(t, 0) + 1
        
        for t, count in type_counts.items():
            html += f"""
                <div style='background:#1e293b;padding:10px;border-radius:8px;text-align:center;'>
                    <div style='font-size:24px;font-weight:bold;'>{count}</div>
                    <div style='color:#94a3b8;text-transform:uppercase;font-size:12px;'>{t}</div>
                </div>
            """
        
        html += "</div>"
        return html
    
    def _generate_timeline_preview(self, case_data: Dict) -> str:
        """Genera preview de timeline"""
        events = case_data.get('timeline_events', [])
        if not events:
            return "<p>No hay eventos en la línea de tiempo.</p>"
        
        html = "<div style='border-left:3px solid #3b82f6;padding-left:20px;'>"
        
        for event in events[:5]:
            severity_color = {
                'critical': '#ef4444', 'high': '#f97316', 
                'medium': '#eab308', 'low': '#22c55e'
            }.get(event.get('severity', 'info'), '#3b82f6')
            
            html += f"""
                <div style='margin-bottom:15px;position:relative;'>
                    <div style='position:absolute;left:-27px;width:12px;height:12px;background:{severity_color};border-radius:50%;border:2px solid #1e293b;'></div>
                    <div style='color:#94a3b8;font-size:12px;'>{event.get('timestamp', 'N/A')}</div>
                    <div style='font-weight:bold;'>{event.get('type', 'Evento')}</div>
                    <div style='color:#cbd5e1;'>{event.get('description', 'Sin descripción')}</div>
                </div>
            """
        
        html += "</div>"
        
        if len(events) > 5:
            html += f"<p style='color:#94a3b8;'>... y {len(events) - 5} eventos más</p>"
        
        return html
    
    def _build_preview_html(
        self,
        template_name: str,
        case_id: str,
        case_data: Dict,
        sections: List[str],
        section_contents: Dict[str, str]
    ) -> str:
        """Construye el HTML completo del preview"""
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview: {template_name}</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            line-height: 1.6;
            padding: 40px;
            min-height: 100vh;
        }}
        .report-container {{
            max-width: 900px;
            margin: 0 auto;
            background: #1e293b;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            overflow: hidden;
        }}
        .report-header {{
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            padding: 30px 40px;
            text-align: center;
        }}
        .report-header h1 {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .report-header .meta {{
            display: flex;
            justify-content: center;
            gap: 30px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .report-header .badge {{
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
        }}
        .report-body {{
            padding: 40px;
        }}
        .section {{
            margin-bottom: 35px;
            background: #0f172a;
            border-radius: 12px;
            padding: 25px;
            border-left: 4px solid #3b82f6;
        }}
        .section h2 {{
            font-size: 20px;
            color: #60a5fa;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section h2::before {{
            content: '';
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #3b82f6;
            border-radius: 50%;
        }}
        .section p {{
            margin-bottom: 10px;
        }}
        .section ul, .section ol {{
            margin-left: 20px;
            margin-bottom: 10px;
        }}
        .section li {{
            margin-bottom: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border: 1px solid #334155;
        }}
        th {{
            background: #1e293b;
        }}
        .watermark {{
            text-align: center;
            padding: 20px;
            color: #475569;
            font-size: 12px;
            border-top: 1px solid #334155;
        }}
        @media print {{
            body {{
                background: white;
                color: #1e293b;
            }}
            .report-container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1>📋 {template_name}</h1>
            <div class="meta">
                <span>📁 Caso: {case_id}</span>
                <span>📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
                <span class="badge">{case_data.get('classification', 'Confidencial')}</span>
            </div>
        </div>
        <div class="report-body">
"""
        
        for section in sections:
            section_title = section.replace('_', ' ').title()
            content = section_contents.get(section, f"<p>Contenido de {section}</p>")
            html += f"""
            <div class="section" id="{section}">
                <h2>{section_title}</h2>
                {content}
            </div>
"""
        
        html += f"""
        </div>
        <div class="watermark">
            ⚠️ PREVIEW - Documento generado por MCP Kali Forensics v4.5.0<br>
            Este es un preview del reporte. El documento final puede variar.
        </div>
    </div>
</body>
</html>
"""
        return html


# Singleton
reports_service = ReportsService()
