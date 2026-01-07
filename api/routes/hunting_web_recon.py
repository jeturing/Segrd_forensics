"""
Threat Hunting Web Reconnaissance Routes
=========================================
Nuevos endpoints que integran web-check-api para análisis OSINT
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from api.services.web_check_client import web_check_client

router = APIRouter(prefix="/api/hunting/web-recon", tags=["threat-hunting-recon"])

class WebReconRequest(BaseModel):
    domain: str = Field(..., description="Dominio a analizar")
    case_id: Optional[str] = Field(None, description="ID del caso asociado")
    categories: Optional[List[str]] = Field(
        default=["dns", "tls", "headers", "security", "firewall", "dnssec", "blocklists"],
        description="Categorías de análisis a incluir"
    )
    deep_scan: bool = Field(False, description="Incluir port scanning")
    store_result: bool = Field(True, description="Guardar resultado en BD")

class WebReconResponse(BaseModel):
    domain: str
    timestamp: datetime
    status: str
    checks: Dict[str, Any]
    findings_count: int = 0
    risk_level: str = "unknown"
    recommendations: List[str] = []

@router.post("/analyze")
async def analyze_domain(request: WebReconRequest) -> WebReconResponse:
    """Analizar un dominio completo"""
    try:
        domain = request.domain.strip().lower()
        if domain.startswith("http://") or domain.startswith("https://"):
            domain = domain.split("//")[1].split("/")[0]
        
        analysis_result = await web_check_client.analyze_domain(
            domain,
            categories=request.categories
        )
        
        if request.deep_scan:
            ports_result = await web_check_client.get_ports_scan(domain)
            analysis_result["checks"]["ports"] = ports_result
        
        findings = []
        risk_level = "low"
        
        return WebReconResponse(
            domain=domain,
            timestamp=datetime.utcnow(),
            status="completed",
            checks=analysis_result["checks"],
            findings_count=len(findings),
            risk_level=risk_level,
            recommendations=[]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar dominio: {str(e)}")

@router.post("/bulk-analyze")
async def bulk_analyze(
    domains: List[str] = Query(...),
    case_id: Optional[str] = Query(None),
    categories: Optional[List[str]] = Query(None),
    parallel: bool = Query(True)
) -> Dict[str, Any]:
    """Analizar múltiples dominios"""
    total = len(domains)
    
    if parallel:
        import asyncio
        tasks = [
            web_check_client.analyze_domain(domain, categories)
            for domain in domains
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        results = []
        for domain in domains:
            try:
                result = await web_check_client.analyze_domain(domain, categories)
                results.append(result)
            except Exception as e:
                results.append({"domain": domain, "error": str(e)})
    
    successful = sum(1 for r in results if "error" not in r)
    failed = total - successful
    
    return {
        "status": "completed",
        "total_domains": total,
        "successful": successful,
        "failed": failed,
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/threat-assessment/{domain}")
async def threat_assessment(
    domain: str,
    case_id: Optional[str] = Query(None),
    compare_iocs: bool = Query(True)
) -> Dict[str, Any]:
    """Evaluar el nivel de amenaza de un dominio"""
    try:
        recon = await web_check_client.analyze_domain(domain)
        
        return {
            "domain": domain,
            "timestamp": datetime.utcnow().isoformat(),
            "recon_data": recon,
            "threat_indicators": {},
            "ioc_matches": [],
            "overall_risk": "medium",
            "mitre_techniques": [],
            "recommended_actions": []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en evaluación: {str(e)}")

@router.get("/dns-records/{domain}")
async def get_dns_records(domain: str) -> Dict[str, Any]:
    """Obtener registros DNS"""
    return await web_check_client.get_dns_records(domain)

@router.get("/tls-certificate/{domain}")
async def get_tls_cert(domain: str) -> Dict[str, Any]:
    """Obtener información del certificado TLS/SSL"""
    return await web_check_client.get_tls_certificate(domain)

@router.get("/security-headers/{domain}")
async def get_security_headers(domain: str) -> Dict[str, Any]:
    """Analizar headers de seguridad HTTP"""
    return await web_check_client.get_security_headers(domain)

@router.get("/firewall-detection/{domain}")
async def detect_firewall(domain: str) -> Dict[str, Any]:
    """Detectar WAF/Firewall"""
    return await web_check_client.get_firewall_detection(domain)

@router.get("/ports/{domain}")
async def scan_ports(domain: str, ports: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Escanear puertos abiertos"""
    port_list = None
    if ports:
        port_list = [int(p.strip()) for p in ports.split(",")]
    
    return await web_check_client.get_ports_scan(domain, port_list)
