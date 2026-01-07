"""
🤖 SOAR Playbooks - Threat Intelligence Automation
Playbooks automáticos que usan APIs de Threat Intel
"""

from typing import Dict, Any
from datetime import datetime
import logging
import asyncio

from api.services import threat_intel
from api.services import webhooks

logger = logging.getLogger(__name__)

# =============================================================================
# Playbook: IP Reputation Analysis
# =============================================================================

async def playbook_ip_reputation_analysis(ip: str, investigation_id: str) -> Dict[str, Any]:
    """
    Playbook automático de análisis de reputación de IP
    
    Pasos:
    1. Consultar Shodan (puertos, servicios, vulnerabilidades)
    2. Consultar VirusTotal (detecciones de malware)
    3. Consultar X-Force (threat score)
    4. Consultar Censys (certificados SSL)
    5. Generar score consolidado
    6. Crear recomendaciones
    
    Retorna:
    - Risk score (0-100)
    - Threat indicators encontrados
    - Recomendaciones de acción
    """
    logger.info(f"🤖 Iniciando playbook IP Reputation Analysis: {ip}")
    
    results = {
        "playbook": "ip_reputation_analysis",
        "target": ip,
        "investigation_id": investigation_id,
        "timestamp": datetime.now().isoformat(),
        "steps": [],
        "risk_score": 0,
        "indicators": [],
        "recommendations": []
    }
    
    # Step 1: Shodan Lookup
    try:
        logger.info("  Step 1/4: Shodan lookup...")
        shodan_result = await threat_intel.shodan_ip_lookup(ip)
        results["steps"].append({
            "step": 1,
            "name": "shodan_lookup",
            "status": "completed" if shodan_result.get("success") else "failed",
            "data": shodan_result
        })
        
        # Analizar vulnerabilidades
        if shodan_result.get("success"):
            vulns = shodan_result.get("vulns", [])
            if vulns:
                results["indicators"].append({
                    "type": "vulnerabilities",
                    "severity": "high",
                    "count": len(vulns),
                    "details": vulns[:5]  # Top 5
                })
                results["risk_score"] += 30
            
            # Puertos sospechosos
            suspicious_ports = [22, 23, 3389, 445, 1433, 3306]
            open_suspicious = [p for p in shodan_result.get("ports", []) if p in suspicious_ports]
            if open_suspicious:
                results["indicators"].append({
                    "type": "suspicious_ports",
                    "severity": "medium",
                    "ports": open_suspicious
                })
                results["risk_score"] += 10
    except Exception as e:
        logger.error(f"  Shodan error: {e}")
        results["steps"].append({
            "step": 1,
            "name": "shodan_lookup",
            "status": "error",
            "error": str(e)
        })
    
    await asyncio.sleep(1)  # Rate limit
    
    # Step 2: VirusTotal Lookup
    try:
        logger.info("  Step 2/4: VirusTotal lookup...")
        vt_result = await threat_intel.virustotal_ip_report(ip)
        results["steps"].append({
            "step": 2,
            "name": "virustotal_lookup",
            "status": "completed" if vt_result.get("success") else "failed",
            "data": vt_result
        })
        
        if vt_result.get("success"):
            malicious = vt_result.get("malicious", 0)
            suspicious = vt_result.get("suspicious", 0)
            
            if malicious > 0:
                results["indicators"].append({
                    "type": "malicious_detections",
                    "severity": "critical",
                    "count": malicious,
                    "source": "virustotal"
                })
                results["risk_score"] += 40
            
            if suspicious > 0:
                results["indicators"].append({
                    "type": "suspicious_detections",
                    "severity": "medium",
                    "count": suspicious,
                    "source": "virustotal"
                })
                results["risk_score"] += 15
    except Exception as e:
        logger.error(f"  VirusTotal error: {e}")
        results["steps"].append({
            "step": 2,
            "name": "virustotal_lookup",
            "status": "error",
            "error": str(e)
        })
    
    await asyncio.sleep(1)
    
    # Step 3: X-Force Lookup
    try:
        logger.info("  Step 3/4: X-Force lookup...")
        xforce_result = await threat_intel.xforce_ip_report(ip)
        results["steps"].append({
            "step": 3,
            "name": "xforce_lookup",
            "status": "completed" if xforce_result.get("success") else "failed",
            "data": xforce_result
        })
        
        if xforce_result.get("success"):
            score = xforce_result.get("score", 0)
            if score > 7:
                results["indicators"].append({
                    "type": "high_risk_score",
                    "severity": "high",
                    "score": score,
                    "source": "xforce"
                })
                results["risk_score"] += 25
            elif score > 4:
                results["risk_score"] += 10
    except Exception as e:
        logger.error(f"  X-Force error: {e}")
        results["steps"].append({
            "step": 3,
            "name": "xforce_lookup",
            "status": "error",
            "error": str(e)
        })
    
    await asyncio.sleep(1)
    
    # Step 4: Censys Lookup
    try:
        logger.info("  Step 4/4: Censys lookup...")
        censys_result = await threat_intel.censys_ip_lookup(ip)
        results["steps"].append({
            "step": 4,
            "name": "censys_lookup",
            "status": "completed" if censys_result.get("success") else "failed",
            "data": censys_result
        })
    except Exception as e:
        logger.error(f"  Censys error: {e}")
        results["steps"].append({
            "step": 4,
            "name": "censys_lookup",
            "status": "error",
            "error": str(e)
        })
    
    # Generar recomendaciones
    if results["risk_score"] >= 70:
        results["recommendations"] = [
            "🚨 BLOCK immediately in firewall",
            "🔍 Review all connections from this IP in logs",
            "📧 Alert SOC team for immediate investigation",
            "🔒 Consider adding to threat feed"
        ]
        results["action"] = "block"
    elif results["risk_score"] >= 40:
        results["recommendations"] = [
            "⚠️ MONITOR closely for suspicious activity",
            "🔍 Enable enhanced logging for this IP",
            "👁️ Review recent connections",
            "📊 Schedule detailed investigation"
        ]
        results["action"] = "monitor"
    else:
        results["recommendations"] = [
            "✅ Low risk - Continue normal monitoring",
            "📝 Log for future reference"
        ]
        results["action"] = "allow"
    
    results["completed_at"] = datetime.now().isoformat()
    logger.info(f"✅ Playbook completed - Risk Score: {results['risk_score']}/100")
    
    # 🔔 Enviar alerta webhook si el riesgo es alto
    if results["risk_score"] >= 60:
        try:
            await webhooks.alert_malicious_ip(
                ip=ip,
                risk_score=results["risk_score"],
                sources=["Shodan", "VirusTotal", "X-Force", "Censys"],
                indicators=results["indicators"],
                investigation_id=investigation_id
            )
        except Exception as e:
            logger.error(f"Webhook alert error: {e}")
    
    return results


# =============================================================================
# Playbook: Email Compromise Investigation
# =============================================================================

async def playbook_email_compromise_investigation(
    email: str,
    investigation_id: str,
    check_domain: bool = True
) -> Dict[str, Any]:
    """
    Playbook automático de investigación de compromiso de email
    
    Pasos:
    1. Verificar en HaveIBeenPwned
    2. Buscar en Intelligence X (dark web)
    3. Descubrir otros emails del dominio
    4. Verificar dominio en Shodan
    5. Generar reporte de exposición
    
    Retorna:
    - Brechas encontradas
    - Datos expuestos
    - Otros emails del dominio en riesgo
    - Recomendaciones
    """
    logger.info(f"🤖 Iniciando playbook Email Compromise Investigation: {email}")
    
    results = {
        "playbook": "email_compromise_investigation",
        "target": email,
        "investigation_id": investigation_id,
        "timestamp": datetime.now().isoformat(),
        "steps": [],
        "exposure_level": "unknown",
        "breaches": [],
        "exposed_data": set(),
        "recommendations": []
    }
    
    domain = email.split("@")[1] if "@" in email else None
    
    # Step 1: HIBP Check
    try:
        logger.info("  Step 1/3: HaveIBeenPwned check...")
        hibp_result = await threat_intel.hibp_check_email(email)
        results["steps"].append({
            "step": 1,
            "name": "hibp_check",
            "status": "completed" if hibp_result.get("success") else "failed",
            "data": hibp_result
        })
        
        if hibp_result.get("success") and hibp_result.get("breached"):
            results["breaches"] = hibp_result.get("breaches", [])
            
            # Consolidar datos expuestos
            for breach in results["breaches"]:
                for data_class in breach.get("data_classes", []):
                    results["exposed_data"].add(data_class)
            
            breach_count = len(results["breaches"])
            if breach_count > 10:
                results["exposure_level"] = "critical"
            elif breach_count > 5:
                results["exposure_level"] = "high"
            elif breach_count > 0:
                results["exposure_level"] = "medium"
            else:
                results["exposure_level"] = "low"
    except Exception as e:
        logger.error(f"  HIBP error: {e}")
        results["steps"].append({
            "step": 1,
            "name": "hibp_check",
            "status": "error",
            "error": str(e)
        })
    
    await asyncio.sleep(2)  # HIBP rate limit
    
    # Step 2: Intelligence X Search
    try:
        logger.info("  Step 2/3: Intelligence X dark web search...")
        intelx_result = await threat_intel.intelx_search(email, maxresults=50)
        results["steps"].append({
            "step": 2,
            "name": "intelx_search",
            "status": "completed" if intelx_result.get("success") else "failed",
            "data": intelx_result
        })
        
        if intelx_result.get("success"):
            records = intelx_result.get("records", [])
            if len(records) > 0:
                results["dark_web_mentions"] = len(records)
                if len(records) > 10:
                    results["exposure_level"] = "critical"
    except Exception as e:
        logger.error(f"  Intelligence X error: {e}")
        results["steps"].append({
            "step": 2,
            "name": "intelx_search",
            "status": "error",
            "error": str(e)
        })
    
    await asyncio.sleep(1)
    
    # Step 3: Domain Email Discovery
    if check_domain and domain:
        try:
            logger.info("  Step 3/3: Hunter.io domain search...")
            hunter_result = await threat_intel.hunter_domain_search(domain)
            results["steps"].append({
                "step": 3,
                "name": "domain_email_discovery",
                "status": "completed" if hunter_result.get("success") else "failed",
                "data": hunter_result
            })
            
            if hunter_result.get("success"):
                other_emails = hunter_result.get("emails", [])
                results["domain_emails"] = len(other_emails)
                results["other_emails_at_risk"] = [
                    e.get("value") for e in other_emails[:10]
                ]
        except Exception as e:
            logger.error(f"  Hunter error: {e}")
            results["steps"].append({
                "step": 3,
                "name": "domain_email_discovery",
                "status": "error",
                "error": str(e)
            })
    
    # Convertir set a list para JSON
    results["exposed_data"] = list(results["exposed_data"])
    
    # Generar recomendaciones
    if results["exposure_level"] == "critical":
        results["recommendations"] = [
            "🚨 IMMEDIATE PASSWORD RESET required",
            "🔐 Enable MFA on all accounts",
            "📧 Notify user of breach exposure",
            "🔍 Audit all account activity",
            "👥 Reset passwords for all domain emails",
            "🛡️ Implement additional security monitoring"
        ]
    elif results["exposure_level"] == "high":
        results["recommendations"] = [
            "⚠️ PASSWORD RESET recommended",
            "🔐 Enable MFA if not already active",
            "📧 Notify user of potential exposure",
            "🔍 Review recent account activity"
        ]
    elif results["exposure_level"] == "medium":
        results["recommendations"] = [
            "🔒 Consider password change",
            "🔐 Verify MFA is enabled",
            "📝 Monitor for suspicious activity"
        ]
    else:
        results["recommendations"] = [
            "✅ No immediate action required",
            "🔐 Ensure MFA is enabled as best practice"
        ]
    
    results["completed_at"] = datetime.now().isoformat()
    logger.info(f"✅ Playbook completed - Exposure Level: {results['exposure_level']}")
    
    # 🔔 Enviar alerta webhook si la exposición es crítica o alta
    if results["exposure_level"] in ["critical", "high"]:
        try:
            await webhooks.alert_email_breach(
                email=email,
                breach_count=results["breaches_found"],
                breaches=[b["name"] for b in results["breaches"][:5]],
                exposed_data=list(results["exposed_data"]),
                investigation_id=investigation_id
            )
        except Exception as e:
            logger.error(f"Webhook alert error: {e}")
    
    return results


# =============================================================================
# Playbook: Phishing URL Analysis
# =============================================================================

async def playbook_phishing_url_analysis(url: str, investigation_id: str) -> Dict[str, Any]:
    """
    Playbook automático de análisis de URL sospechosa
    
    Pasos:
    1. Escanear URL en VirusTotal
    2. Extraer dominio y analizar con SecurityTrails
    3. Verificar IP del dominio en Shodan
    4. Buscar indicadores de phishing
    5. Generar reporte de seguridad
    
    Retorna:
    - Detecciones de malware
    - Indicadores de phishing
    - Información del dominio
    - Recomendaciones
    """
    logger.info(f"🤖 Iniciando playbook Phishing URL Analysis: {url}")
    
    results = {
        "playbook": "phishing_url_analysis",
        "target": url,
        "investigation_id": investigation_id,
        "timestamp": datetime.now().isoformat(),
        "steps": [],
        "threat_level": "unknown",
        "indicators": [],
        "recommendations": []
    }
    
    # Step 1: VirusTotal URL Scan
    try:
        logger.info("  Step 1/2: VirusTotal URL scan...")
        vt_result = await threat_intel.virustotal_url_scan(url)
        results["steps"].append({
            "step": 1,
            "name": "virustotal_url_scan",
            "status": "completed" if vt_result.get("success") else "failed",
            "data": vt_result
        })
        
        if vt_result.get("success"):
            malicious = vt_result.get("malicious", 0)
            suspicious = vt_result.get("suspicious", 0)
            
            if malicious > 5:
                results["threat_level"] = "critical"
                results["indicators"].append({
                    "type": "malware_detected",
                    "severity": "critical",
                    "detections": malicious
                })
            elif malicious > 0:
                results["threat_level"] = "high"
                results["indicators"].append({
                    "type": "malware_detected",
                    "severity": "high",
                    "detections": malicious
                })
            elif suspicious > 3:
                results["threat_level"] = "medium"
                results["indicators"].append({
                    "type": "suspicious_activity",
                    "severity": "medium",
                    "detections": suspicious
                })
            else:
                results["threat_level"] = "low"
    except Exception as e:
        logger.error(f"  VirusTotal error: {e}")
        results["steps"].append({
            "step": 1,
            "name": "virustotal_url_scan",
            "status": "error",
            "error": str(e)
        })
    
    await asyncio.sleep(1)
    
    # Step 2: Domain Analysis
    try:
        # Extraer dominio de la URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        
        if domain:
            logger.info("  Step 2/2: SecurityTrails domain analysis...")
            st_result = await threat_intel.securitytrails_domain_info(domain)
            results["steps"].append({
                "step": 2,
                "name": "domain_analysis",
                "status": "completed" if st_result.get("success") else "failed",
                "data": st_result
            })
    except Exception as e:
        logger.error(f"  Domain analysis error: {e}")
        results["steps"].append({
            "step": 2,
            "name": "domain_analysis",
            "status": "error",
            "error": str(e)
        })
    
    # Generar recomendaciones
    if results["threat_level"] == "critical":
        results["recommendations"] = [
            "🚨 BLOCK URL immediately in web gateway",
            "📧 Alert users who may have clicked the link",
            "🔍 Scan all systems that accessed this URL",
            "🛡️ Add to threat intelligence feed",
            "📊 Report to abuse team"
        ]
    elif results["threat_level"] == "high":
        results["recommendations"] = [
            "⚠️ BLOCK URL in web gateway",
            "🔍 Investigate access logs",
            "📧 Warn users about this threat"
        ]
    elif results["threat_level"] == "medium":
        results["recommendations"] = [
            "👁️ MONITOR access to this URL",
            "🔍 Review in context of other indicators"
        ]
    else:
        results["recommendations"] = [
            "✅ URL appears safe",
            "📝 Continue normal monitoring"
        ]
    
    results["completed_at"] = datetime.now().isoformat()
    logger.info(f"✅ Playbook completed - Threat Level: {results['threat_level']}")
    
    # 🔔 Enviar alerta webhook si la amenaza es crítica o alta
    if results["threat_level"] in ["critical", "high"]:
        try:
            await webhooks.alert_phishing_url(
                url=url,
                detections=results["malicious_detections"],
                threat_level_value=results["threat_level"],
                indicators=results["phishing_indicators"],
                investigation_id=investigation_id
            )
        except Exception as e:
            logger.error(f"Webhook alert error: {e}")
    
    return results


# =============================================================================
# Playbook Registry
# =============================================================================

THREAT_INTEL_PLAYBOOKS = {
    "ip_reputation_analysis": playbook_ip_reputation_analysis,
    "email_compromise_investigation": playbook_email_compromise_investigation,
    "phishing_url_analysis": playbook_phishing_url_analysis
}


async def execute_playbook(
    playbook_name: str,
    target: str,
    investigation_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Ejecuta un playbook de Threat Intelligence
    
    Args:
        playbook_name: Nombre del playbook a ejecutar
        target: Objetivo del análisis (IP, email, URL, etc.)
        investigation_id: ID de la investigación
        **kwargs: Parámetros adicionales para el playbook
    
    Returns:
        Resultados del playbook
    """
    if playbook_name not in THREAT_INTEL_PLAYBOOKS:
        raise ValueError(f"Playbook not found: {playbook_name}")
    
    playbook_func = THREAT_INTEL_PLAYBOOKS[playbook_name]
    return await playbook_func(target, investigation_id, **kwargs)
