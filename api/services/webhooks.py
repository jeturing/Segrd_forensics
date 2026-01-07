"""
📡 Webhook Service - Notificaciones en Tiempo Real
Envía alertas de amenazas detectadas a sistemas externos (Slack, Discord, custom)
"""

import os
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# =============================================================================
# Webhook Configuration
# =============================================================================

WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"

# Slack Configuration
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#security-alerts")
SLACK_USERNAME = os.getenv("SLACK_USERNAME", "Forensics Bot")
SLACK_ICON = os.getenv("SLACK_ICON", ":shield:")

# Discord Configuration
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_USERNAME = os.getenv("DISCORD_USERNAME", "Forensics Bot")

# Custom Webhooks (comma-separated URLs)
CUSTOM_WEBHOOK_URLS = os.getenv("CUSTOM_WEBHOOK_URLS", "").split(",")
CUSTOM_WEBHOOK_URLS = [url.strip() for url in CUSTOM_WEBHOOK_URLS if url.strip()]


# =============================================================================
# Threat Level & Priority
# =============================================================================

class ThreatLevel(str, Enum):
    """Niveles de amenaza para clasificación"""
    CRITICAL = "critical"  # 🔴 Requiere acción inmediata
    HIGH = "high"          # 🟠 Alta prioridad
    MEDIUM = "medium"      # 🟡 Monitoreo necesario
    LOW = "low"            # 🟢 Informativo
    INFO = "info"          # ℹ️ Información general


# Color mapping para diferentes plataformas
THREAT_COLORS = {
    ThreatLevel.CRITICAL: "#FF0000",  # Rojo
    ThreatLevel.HIGH: "#FF8C00",      # Naranja
    ThreatLevel.MEDIUM: "#FFD700",    # Amarillo
    ThreatLevel.LOW: "#32CD32",       # Verde
    ThreatLevel.INFO: "#1E90FF"       # Azul
}

THREAT_EMOJIS = {
    ThreatLevel.CRITICAL: "🔴",
    ThreatLevel.HIGH: "🟠",
    ThreatLevel.MEDIUM: "🟡",
    ThreatLevel.LOW: "🟢",
    ThreatLevel.INFO: "ℹ️"
}


# =============================================================================
# Webhook Alert Models
# =============================================================================

class WebhookAlert:
    """Modelo de alerta para webhook"""
    
    def __init__(
        self,
        title: str,
        message: str,
        threat_level: ThreatLevel,
        source: str,
        target: str,
        investigation_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        recommendations: Optional[List[str]] = None
    ):
        self.title = title
        self.message = message
        self.threat_level = threat_level
        self.source = source
        self.target = target
        self.investigation_id = investigation_id
        self.metadata = metadata or {}
        self.recommendations = recommendations or []
        self.timestamp = datetime.now().isoformat()
        self.alert_id = f"ALERT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


# =============================================================================
# Slack Webhook
# =============================================================================

async def send_slack_alert(alert: WebhookAlert) -> bool:
    """
    Envía alerta a Slack
    
    Formato: Rich message block con color coding y metadata
    """
    if not SLACK_WEBHOOK_URL:
        logger.debug("Slack webhook not configured")
        return False
    
    # Construir bloques de Slack
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{THREAT_EMOJIS[alert.threat_level]} {alert.title}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Threat Level:*\n{alert.threat_level.upper()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Source:*\n{alert.source}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Target:*\n`{alert.target}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Investigation ID:*\n{alert.investigation_id or 'N/A'}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Details:*\n{alert.message}"
            }
        }
    ]
    
    # Añadir metadata si existe
    if alert.metadata:
        metadata_text = "\n".join([f"• *{k}:* {v}" for k, v in alert.metadata.items()])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Additional Info:*\n{metadata_text}"
            }
        })
    
    # Añadir recomendaciones si existen
    if alert.recommendations:
        rec_text = "\n".join([f"• {rec}" for rec in alert.recommendations])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommendations:*\n{rec_text}"
            }
        })
    
    # Timestamp
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"🕐 {alert.timestamp} | Alert ID: {alert.alert_id}"
            }
        ]
    })
    
    payload = {
        "channel": SLACK_CHANNEL,
        "username": SLACK_USERNAME,
        "icon_emoji": SLACK_ICON,
        "attachments": [
            {
                "color": THREAT_COLORS[alert.threat_level],
                "blocks": blocks
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Slack alert sent: {alert.alert_id}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"❌ Slack webhook failed: {error}")
                    return False
    except Exception as e:
        logger.error(f"Slack webhook error: {e}")
        return False


# =============================================================================
# Discord Webhook
# =============================================================================

async def send_discord_alert(alert: WebhookAlert) -> bool:
    """
    Envía alerta a Discord
    
    Formato: Embed con color coding y fields
    """
    if not DISCORD_WEBHOOK_URL:
        logger.debug("Discord webhook not configured")
        return False
    
    # Construir embed de Discord
    embed = {
        "title": f"{THREAT_EMOJIS[alert.threat_level]} {alert.title}",
        "description": alert.message,
        "color": int(THREAT_COLORS[alert.threat_level].replace("#", ""), 16),
        "fields": [
            {
                "name": "🎯 Target",
                "value": f"`{alert.target}`",
                "inline": True
            },
            {
                "name": "📊 Threat Level",
                "value": alert.threat_level.upper(),
                "inline": True
            },
            {
                "name": "🔍 Source",
                "value": alert.source,
                "inline": True
            }
        ],
        "footer": {
            "text": f"Alert ID: {alert.alert_id}"
        },
        "timestamp": alert.timestamp
    }
    
    # Añadir investigation ID si existe
    if alert.investigation_id:
        embed["fields"].append({
            "name": "🔎 Investigation",
            "value": alert.investigation_id,
            "inline": True
        })
    
    # Añadir metadata
    if alert.metadata:
        for key, value in alert.metadata.items():
            embed["fields"].append({
                "name": key,
                "value": str(value),
                "inline": True
            })
    
    # Añadir recomendaciones
    if alert.recommendations:
        rec_text = "\n".join([f"• {rec}" for rec in alert.recommendations])
        embed["fields"].append({
            "name": "💡 Recommendations",
            "value": rec_text,
            "inline": False
        })
    
    payload = {
        "username": DISCORD_USERNAME,
        "embeds": [embed]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 204]:
                    logger.info(f"✅ Discord alert sent: {alert.alert_id}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"❌ Discord webhook failed: {error}")
                    return False
    except Exception as e:
        logger.error(f"Discord webhook error: {e}")
        return False


# =============================================================================
# Custom Webhook (Generic JSON)
# =============================================================================

async def send_custom_alert(webhook_url: str, alert: WebhookAlert) -> bool:
    """
    Envía alerta a webhook custom
    
    Formato: JSON genérico con todos los campos
    """
    payload = {
        "alert_id": alert.alert_id,
        "timestamp": alert.timestamp,
        "threat_level": alert.threat_level.value,
        "title": alert.title,
        "message": alert.message,
        "source": alert.source,
        "target": alert.target,
        "investigation_id": alert.investigation_id,
        "metadata": alert.metadata,
        "recommendations": alert.recommendations
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in range(200, 300):
                    logger.info(f"✅ Custom webhook sent: {alert.alert_id} -> {webhook_url}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"❌ Custom webhook failed ({webhook_url}): {error}")
                    return False
    except Exception as e:
        logger.error(f"Custom webhook error ({webhook_url}): {e}")
        return False


# =============================================================================
# Master Webhook Dispatcher
# =============================================================================

async def send_threat_alert(alert: WebhookAlert) -> Dict[str, bool]:
    """
    Envía alerta a todos los webhooks configurados
    
    Returns:
        Dict con el estado de cada webhook:
        {
            "slack": True/False,
            "discord": True/False,
            "custom": [True/False, ...]
        }
    """
    if not WEBHOOK_ENABLED:
        logger.debug("Webhooks disabled")
        return {"enabled": False}
    
    logger.info(f"📡 Sending {alert.threat_level.upper()} alert: {alert.title}")
    
    # Enviar a todos los webhooks en paralelo
    tasks = []
    
    # Slack
    if SLACK_WEBHOOK_URL:
        tasks.append(("slack", send_slack_alert(alert)))
    
    # Discord
    if DISCORD_WEBHOOK_URL:
        tasks.append(("discord", send_discord_alert(alert)))
    
    # Custom webhooks
    for idx, url in enumerate(CUSTOM_WEBHOOK_URLS):
        tasks.append((f"custom_{idx}", send_custom_alert(url, alert)))
    
    # Ejecutar en paralelo
    results = {}
    if tasks:
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
            except Exception as e:
                logger.error(f"Webhook {name} failed: {e}")
                results[name] = False
    
    # Log summary
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    logger.info(f"📡 Webhooks sent: {success_count}/{total_count} successful")
    
    return results


# =============================================================================
# Helper Functions para Crear Alertas Rápidas
# =============================================================================

async def alert_malicious_ip(
    ip: str,
    risk_score: int,
    sources: List[str],
    indicators: List[str],
    investigation_id: Optional[str] = None
):
    """Alerta de IP maliciosa detectada"""
    
    # Determinar threat level basado en risk score
    if risk_score >= 80:
        threat_level = ThreatLevel.CRITICAL
    elif risk_score >= 60:
        threat_level = ThreatLevel.HIGH
    elif risk_score >= 40:
        threat_level = ThreatLevel.MEDIUM
    else:
        threat_level = ThreatLevel.LOW
    
    alert = WebhookAlert(
        title="Malicious IP Detected",
        message=f"IP address {ip} has been flagged as malicious with a risk score of {risk_score}/100",
        threat_level=threat_level,
        source=", ".join(sources),
        target=ip,
        investigation_id=investigation_id,
        metadata={
            "Risk Score": f"{risk_score}/100",
            "Indicators": ", ".join(indicators[:3])  # Top 3
        },
        recommendations=[
            "Block IP at firewall level",
            "Review recent connections from this IP",
            "Check for compromised accounts"
        ]
    )
    
    return await send_threat_alert(alert)


async def alert_email_breach(
    email: str,
    breach_count: int,
    breaches: List[str],
    exposed_data: List[str],
    investigation_id: Optional[str] = None
):
    """Alerta de email comprometido"""
    
    # Determinar threat level
    if breach_count >= 5 or "passwords" in exposed_data:
        threat_level = ThreatLevel.CRITICAL
    elif breach_count >= 3:
        threat_level = ThreatLevel.HIGH
    else:
        threat_level = ThreatLevel.MEDIUM
    
    alert = WebhookAlert(
        title="Email Credential Breach Detected",
        message=f"Email {email} found in {breach_count} data breaches",
        threat_level=threat_level,
        source="HaveIBeenPwned, Intelligence X",
        target=email,
        investigation_id=investigation_id,
        metadata={
            "Breaches Found": breach_count,
            "Recent Breach": breaches[0] if breaches else "N/A",
            "Exposed Data": ", ".join(exposed_data[:5])
        },
        recommendations=[
            "Force password reset immediately",
            "Enable MFA if not already active",
            "Review account activity for anomalies",
            "Notify user of compromise"
        ]
    )
    
    return await send_threat_alert(alert)


async def alert_phishing_url(
    url: str,
    detections: int,
    threat_level_value: str,
    indicators: List[str],
    investigation_id: Optional[str] = None
):
    """Alerta de URL de phishing"""
    
    # Mapear threat level
    threat_level = ThreatLevel(threat_level_value)
    
    alert = WebhookAlert(
        title="Phishing URL Detected",
        message=f"URL {url} identified as phishing with {detections} malicious detections",
        threat_level=threat_level,
        source="VirusTotal, SecurityTrails",
        target=url,
        investigation_id=investigation_id,
        metadata={
            "Malicious Detections": detections,
            "Indicators": ", ".join(indicators[:3])
        },
        recommendations=[
            "Block URL at DNS/firewall level",
            "Add to threat intelligence feeds",
            "Notify users who may have clicked",
            "Review email logs for delivery"
        ]
    )
    
    return await send_threat_alert(alert)


# =============================================================================
# Webhook Testing
# =============================================================================

async def test_webhooks() -> Dict[str, Any]:
    """
    Prueba todos los webhooks configurados
    
    Envía un mensaje de prueba a cada webhook
    """
    test_alert = WebhookAlert(
        title="Webhook Test",
        message="This is a test alert from MCP Kali Forensics",
        threat_level=ThreatLevel.INFO,
        source="System Test",
        target="N/A",
        investigation_id="TEST-001",
        metadata={
            "Test Type": "Webhook Connectivity",
            "Status": "OK"
        },
        recommendations=["If you see this, webhook is working correctly!"]
    )
    
    results = await send_threat_alert(test_alert)
    
    return {
        "test_sent": True,
        "timestamp": datetime.now().isoformat(),
        "results": results
    }
