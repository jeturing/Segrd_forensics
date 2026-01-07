"""
Account Analysis Service - Análisis unificado de cuentas de usuario
Integra Sparrow, Hawk, Sherlock y M365 Graph API para perfil completo
"""

import asyncio
import logging
from typing import Dict, List
from datetime import datetime

from api.services.m365 import (
    run_sparrow_analysis,
    run_hawk_analysis
)
from api.services.sherlock_service import sherlock_intelligence_gathering

logger = logging.getLogger(__name__)


async def analyze_user_account(
    user_email: str,
    case_id: str,
    tenant_id: str,
    days_back: int = 90,
    include_osint: bool = True
) -> Dict:
    """
    Análisis forense completo de una cuenta de usuario
    
    Ejecuta todas las herramientas disponibles:
    - M365 Graph API (sign-ins, risk events, MFA status)
    - Sparrow (Azure AD compromise indicators)
    - Hawk (Exchange mailbox, rules, delegations)
    - Sherlock (perfiles en redes sociales)
    
    Args:
        user_email: Email del usuario a analizar
        case_id: ID del caso forense
        tenant_id: Azure AD Tenant ID
        days_back: Días históricos a analizar
        include_osint: Si incluir búsqueda OSINT con Sherlock
    
    Returns:
        Dict con análisis completo del usuario
    """
    try:
        logger.info(f"🔍 Iniciando análisis completo de cuenta: {user_email}")
        
        analysis_result = {
            "user_email": user_email,
            "case_id": case_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "m365_analysis": {},
            "mailbox_analysis": {},
            "osint_analysis": {},
            "risk_assessment": {},
            "timeline": [],
            "recommendations": []
        }
        
        # Ejecutar análisis en paralelo
        tasks = []
        
        # 1. M365 Graph API - Sign-ins y eventos de riesgo
        tasks.append(analyze_m365_activity(user_email, tenant_id, days_back))
        
        # 2. Sparrow - Indicadores de compromiso en Azure AD
        tasks.append(analyze_with_sparrow(user_email, case_id, tenant_id, days_back))
        
        # 3. Hawk - Análisis de buzón de correo
        tasks.append(analyze_with_hawk(user_email, case_id, tenant_id, days_back))
        
        # 4. Sherlock - OSINT perfiles sociales
        if include_osint:
            tasks.append(analyze_with_sherlock(user_email, case_id))
        
        # Ejecutar todas las herramientas en paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error en análisis #{idx}: {result}")
                continue
            
            if idx == 0:  # M365 Graph
                analysis_result["m365_analysis"] = result
            elif idx == 1:  # Sparrow
                analysis_result["sparrow_analysis"] = result
            elif idx == 2:  # Hawk
                analysis_result["mailbox_analysis"] = result
            elif idx == 3 and include_osint:  # Sherlock
                analysis_result["osint_analysis"] = result
        
        # Generar evaluación de riesgo unificada
        analysis_result["risk_assessment"] = calculate_unified_risk(analysis_result)
        
        # Generar timeline de eventos
        analysis_result["timeline"] = build_user_timeline(analysis_result)
        
        # Generar recomendaciones
        analysis_result["recommendations"] = generate_recommendations(analysis_result)
        
        logger.info(f"✅ Análisis completo de {user_email}: Risk Score {analysis_result['risk_assessment'].get('risk_score', 0)}")
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de cuenta: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "user_email": user_email
        }


async def analyze_multiple_accounts(
    user_emails: List[str],
    case_id: str,
    tenant_id: str,
    days_back: int = 90,
    include_osint: bool = True
) -> Dict:
    """
    Análisis forense de múltiples cuentas en paralelo
    
    Args:
        user_emails: Lista de emails de usuarios
        case_id: ID del caso
        tenant_id: Azure AD Tenant ID
        days_back: Días a analizar
        include_osint: Incluir OSINT
    
    Returns:
        Dict con análisis de todas las cuentas
    """
    try:
        logger.info(f"🔍 Analizando {len(user_emails)} cuentas de usuario")
        
        # Limitar a 10 usuarios concurrentes para no saturar APIs
        tasks = []
        for email in user_emails[:10]:
            task = analyze_user_account(
                email, case_id, tenant_id, days_back, include_osint
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Agregar resultados
        accounts_analysis = []
        high_risk_accounts = []
        total_risk_score = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error: {result}")
                continue
            
            accounts_analysis.append(result)
            
            risk_score = result.get("risk_assessment", {}).get("risk_score", 0)
            total_risk_score += risk_score
            
            if risk_score >= 70:
                high_risk_accounts.append(result["user_email"])
        
        return {
            "status": "completed",
            "case_id": case_id,
            "accounts_analyzed": len(accounts_analysis),
            "high_risk_accounts": high_risk_accounts,
            "average_risk_score": total_risk_score / len(accounts_analysis) if accounts_analysis else 0,
            "accounts": accounts_analysis
        }
        
    except Exception as e:
        logger.error(f"❌ Error en análisis múltiple: {e}")
        return {"status": "failed", "error": str(e)}


async def analyze_m365_activity(
    user_email: str,
    tenant_id: str,
    days_back: int
) -> Dict:
    """Analiza actividad M365 usando Graph API"""
    try:
        logger.info(f"📊 Analizando actividad M365 de {user_email}")
        
        # TODO: Implementar llamadas reales a Graph API
        # Por ahora retornar estructura base
        return {
            "sign_ins": [],
            "risky_sign_ins": [],
            "risk_detections": [],
            "mfa_status": "unknown",
            "last_sign_in": None,
            "account_enabled": True
        }
        
    except Exception as e:
        logger.error(f"Error en análisis M365: {e}")
        return {"status": "failed", "error": str(e)}


async def analyze_with_sparrow(
    user_email: str,
    case_id: str,
    tenant_id: str,
    days_back: int
) -> Dict:
    """Analiza con Sparrow buscando compromiso en Azure AD"""
    try:
        logger.info(f"🦅 Ejecutando Sparrow para {user_email}")
        
        # Ejecutar Sparrow con filtro de usuario
        result = await run_sparrow_analysis(
            tenant_id=tenant_id,
            case_id=case_id,
            days_back=days_back
        )
        
        # Filtrar resultados solo para este usuario
        # TODO: Implementar filtrado por usuario en Sparrow
        
        return result
        
    except Exception as e:
        logger.error(f"Error en Sparrow: {e}")
        return {"status": "failed", "error": str(e)}


async def analyze_with_hawk(
    user_email: str,
    case_id: str,
    tenant_id: str,
    days_back: int
) -> Dict:
    """Analiza buzón con Hawk (reglas, delegaciones, OAuth)"""
    try:
        logger.info(f"🦅 Ejecutando Hawk para buzón de {user_email}")
        
        result = await run_hawk_analysis(
            tenant_id=tenant_id,
            case_id=case_id,
            target_users=[user_email],
            days_back=days_back
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error en Hawk: {e}")
        return {"status": "failed", "error": str(e)}


async def analyze_with_sherlock(
    user_email: str,
    case_id: str
) -> Dict:
    """Búsqueda OSINT con Sherlock"""
    try:
        logger.info(f"🕵️ Ejecutando Sherlock OSINT para {user_email}")
        
        result = await sherlock_intelligence_gathering(
            target=user_email,
            case_id=case_id,
            target_type="email"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error en Sherlock: {e}")
        return {"status": "failed", "error": str(e)}


def calculate_unified_risk(analysis: Dict) -> Dict:
    """
    Calcula risk score unificado de todas las fuentes
    
    Factores de riesgo:
    - Sign-ins de riesgo (0-30 puntos)
    - Reglas de correo sospechosas (0-25 puntos)
    - OAuth apps con permisos elevados (0-20 puntos)
    - Perfiles en plataformas de alto riesgo (0-15 puntos)
    - Eventos de Identity Protection (0-10 puntos)
    """
    risk_score = 0
    risk_factors = []
    
    # M365 Activity
    m365 = analysis.get("m365_analysis", {})
    risky_signins = len(m365.get("risky_sign_ins", []))
    if risky_signins > 0:
        points = min(risky_signins * 10, 30)
        risk_score += points
        risk_factors.append({
            "factor": "risky_sign_ins",
            "count": risky_signins,
            "points": points
        })
    
    # Hawk - Mailbox Rules
    mailbox = analysis.get("mailbox_analysis", {})
    suspicious_rules = len(mailbox.get("suspicious_rules", []))
    if suspicious_rules > 0:
        points = min(suspicious_rules * 12, 25)
        risk_score += points
        risk_factors.append({
            "factor": "suspicious_mailbox_rules",
            "count": suspicious_rules,
            "points": points
        })
    
    # Hawk - OAuth Apps
    oauth_apps = len(mailbox.get("oauth_consents", []))
    if oauth_apps > 0:
        points = min(oauth_apps * 5, 20)
        risk_score += points
        risk_factors.append({
            "factor": "oauth_apps_with_permissions",
            "count": oauth_apps,
            "points": points
        })
    
    # Sherlock - High Risk Profiles
    osint = analysis.get("osint_analysis", {})
    high_risk_profiles = len(osint.get("intelligence", {}).get("high_risk_profiles", []))
    if high_risk_profiles > 0:
        points = min(high_risk_profiles * 7, 15)
        risk_score += points
        risk_factors.append({
            "factor": "high_risk_social_profiles",
            "count": high_risk_profiles,
            "points": points
        })
    
    # Categorizar riesgo
    if risk_score >= 70:
        risk_level = "critical"
    elif risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 30:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "total_factors": len(risk_factors)
    }


def build_user_timeline(analysis: Dict) -> List[Dict]:
    """
    Construye timeline de eventos del usuario
    Combina eventos de todas las fuentes en orden cronológico
    """
    timeline = []
    
    # Sign-ins
    m365 = analysis.get("m365_analysis", {})
    for signin in m365.get("sign_ins", []):
        timeline.append({
            "timestamp": signin.get("createdDateTime"),
            "type": "sign_in",
            "source": "M365 Graph API",
            "description": f"Sign-in desde {signin.get('ipAddress')} - {signin.get('location')}",
            "risk_level": signin.get("riskLevel", "none")
        })
    
    # Mailbox rules created
    mailbox = analysis.get("mailbox_analysis", {})
    for rule in mailbox.get("suspicious_rules", []):
        timeline.append({
            "timestamp": rule.get("created_at"),
            "type": "mailbox_rule",
            "source": "Hawk",
            "description": f"Regla de correo creada: {rule.get('name')}",
            "risk_level": "high"
        })
    
    # OAuth consents
    for consent in mailbox.get("oauth_consents", []):
        timeline.append({
            "timestamp": consent.get("consent_date"),
            "type": "oauth_consent",
            "source": "Hawk",
            "description": f"Consentimiento OAuth a: {consent.get('app_name')}",
            "risk_level": "medium"
        })
    
    # Ordenar por timestamp
    timeline.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    
    return timeline[:50]  # Últimos 50 eventos


def generate_recommendations(analysis: Dict) -> List[str]:
    """Genera recomendaciones de seguridad basadas en hallazgos"""
    recommendations = []
    
    risk = analysis.get("risk_assessment", {})
    risk_score = risk.get("risk_score", 0)
    
    # Recomendaciones generales según risk score
    if risk_score >= 70:
        recommendations.append("🔴 CRÍTICO: Considerar suspensión temporal de la cuenta")
        recommendations.append("Forzar reset de contraseña y revocación de todas las sesiones")
        recommendations.append("Activar monitoreo continuo de la cuenta")
        recommendations.append("Notificar al equipo de seguridad senior inmediatamente")
    elif risk_score >= 50:
        recommendations.append("🟠 ALTO: Reset de contraseña recomendado")
        recommendations.append("Revisar y revocar sesiones activas sospechosas")
        recommendations.append("Auditar permisos y accesos de la cuenta")
    elif risk_score >= 30:
        recommendations.append("🟡 MEDIO: Validar actividad reciente con el usuario")
        recommendations.append("Considerar habilitar MFA si no está activo")
    
    # Recomendaciones específicas según hallazgos
    mailbox = analysis.get("mailbox_analysis", {})
    
    if mailbox.get("suspicious_rules"):
        recommendations.append("Eliminar reglas de correo sospechosas inmediatamente")
        recommendations.append("Revisar correos reenviados en los últimos 90 días")
    
    if mailbox.get("oauth_consents"):
        recommendations.append("Revisar y revocar consentimientos OAuth no autorizados")
        recommendations.append("Implementar políticas de consentimiento de aplicaciones")
    
    osint = analysis.get("osint_analysis", {})
    if osint.get("intelligence", {}).get("high_risk_profiles"):
        recommendations.append("Investigar perfiles en plataformas de alto riesgo")
        recommendations.append("Considerar capacitación en seguridad para el usuario")
    
    m365 = analysis.get("m365_analysis", {})
    if not m365.get("mfa_status") == "enabled":
        recommendations.append("Habilitar MFA para la cuenta")
    
    return recommendations
