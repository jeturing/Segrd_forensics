"""
Security Checklist API
Endpoint para recibir y procesar formularios de checklist de ciberseguridad
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security-checklist", tags=["Security Checklist"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SecurityChecklistRequest(BaseModel):
    # Sección 1
    company_name: str
    country: str
    industry: str
    employees: Optional[str] = None

    # Sección 2
    computers: Optional[str] = None
    has_servers: Optional[str] = None
    uses_m365: Optional[str] = None
    m365_users: Optional[str] = None
    has_vpn: Optional[str] = None

    # Sección 3
    has_security_officer: bool = False
    security_only_it: bool = False
    has_policies: bool = False

    # Sección 4
    had_incidents: bool = False
    operates_24_7: bool = False
    attack_could_stop_business: bool = False

    # Sección 5
    clients_demand_security: bool = False
    has_cyber_insurance: bool = False
    compliance_requirements: List[str] = []

    # Sección 6
    has_24_7_monitoring: bool = False
    has_centralized_logs: bool = False
    can_reconstruct_incident: bool = False

    # Sección 7
    has_backups: bool = False
    tested_backups: bool = False
    recovery_time_target: Optional[str] = None

    # Sección 8
    needs_digital_evidence: bool = False
    concerned_internal_fraud: bool = False

    # Sección 9
    comments: Optional[str] = None

    # Computed fields
    recommended_tier: Optional[str] = None
    risk_score: Optional[int] = None
    submitted_at: Optional[str] = None


# ============================================================================
# EMAIL TEMPLATE
# ============================================================================

EMAIL_TEMPLATE = """
<html>
  <head>
    <style>
      body { font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5; }
      .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }
      .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
      .header h1 { margin: 0; font-size: 28px; }
      .section { margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px; }
      .section:last-child { border-bottom: none; }
      .section h2 { color: #667eea; font-size: 18px; margin: 0 0 10px 0; }
      .info-row { display: flex; justify-content: space-between; margin: 8px 0; padding: 8px; background-color: #f9f9f9; border-radius: 4px; }
      .label { font-weight: bold; color: #555; }
      .value { color: #333; }
      .yes { color: #22c55e; }
      .no { color: #ef4444; }
      .tier-badge { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; }
      .tier-essential { background-color: #d4edda; color: #155724; }
      .tier-profesional { background-color: #cce5ff; color: #004085; }
      .tier-critica { background-color: #f8d7da; color: #721c24; }
      .score { font-size: 32px; font-weight: bold; color: #667eea; }
      .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
      th { background-color: #f0f0f0; font-weight: bold; }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h1>🛡️ Nuevo Checklist de Ciberseguridad Recibido</h1>
        <p style="margin: 10px 0 0 0;">Jeturing Security Assessment</p>
      </div>

      <div class="section">
        <h2>📊 Resumen de Recomendación</h2>
        <div style="text-align: center; margin: 20px 0;">
          <div>Puntuación de Riesgo</div>
          <div class="score">{{ risk_score }}/10</div>
        </div>
        <div style="text-align: center;">
          <span class="tier-badge {% if recommended_tier == 'Esencial' %}tier-essential{% elif recommended_tier == 'Profesional' %}tier-profesional{% else %}tier-critica{% endif %}">
            Nivel Recomendado: {{ recommended_tier }}
          </span>
        </div>
      </div>

      <div class="section">
        <h2>🏢 Datos de la Empresa</h2>
        <div class="info-row"><span class="label">Empresa:</span><span class="value">{{ company_name }}</span></div>
        <div class="info-row"><span class="label">País:</span><span class="value">{{ country }}</span></div>
        <div class="info-row"><span class="label">Industria:</span><span class="value">{{ industry }}</span></div>
        <div class="info-row"><span class="label">Empleados:</span><span class="value">{{ employees or 'No especificado' }}</span></div>
      </div>

      <div class="section">
        <h2>💻 Infraestructura Tecnológica</h2>
        <div class="info-row"><span class="label">Computadoras/Laptops:</span><span class="value">{{ computers or 'No especificado' }}</span></div>
        <div class="info-row"><span class="label">Servidores:</span><span class="value">{{ has_servers or 'No especificado' }}</span></div>
        <div class="info-row"><span class="label">Microsoft 365:</span><span class="value">{{ uses_m365 or 'No' }}</span></div>
        {% if m365_users %}
        <div class="info-row"><span class="label">Usuarios M365:</span><span class="value">{{ m365_users }}</span></div>
        {% endif %}
        <div class="info-row"><span class="label">VPN/Acceso Remoto:</span><span class="value">{{ has_vpn or 'No especificado' }}</span></div>
      </div>

      <div class="section">
        <h2>🔐 Estado de Seguridad Actual</h2>
        <table>
          <tr>
            <th>Aspecto</th>
            <th>Estado</th>
          </tr>
          <tr>
            <td>¿Responsable de ciberseguridad?</td>
            <td><span class="{% if has_security_officer %}yes{% else %}no{% endif %}">{% if has_security_officer %}✓ Sí{% else %}✗ No{% endif %}</span></td>
          </tr>
          <tr>
            <td>¿Políticas documentadas?</td>
            <td><span class="{% if has_policies %}yes{% else %}no{% endif %}">{% if has_policies %}✓ Sí{% else %}✗ No{% endif %}</span></td>
          </tr>
          <tr>
            <td>¿Incidentes previos?</td>
            <td><span class="{% if had_incidents %}yes{% else %}no{% endif %}">{% if had_incidents %}✓ Sí{% else %}✗ No{% endif %}</span></td>
          </tr>
          <tr>
            <td>¿Operación 24/7?</td>
            <td><span class="{% if operates_24_7 %}yes{% else %}no{% endif %}">{% if operates_24_7 %}✓ Sí{% else %}✗ No{% endif %}</span></td>
          </tr>
        </table>
      </div>

      <div class="section">
        <h2>📋 Cumplimiento y Regulaciones</h2>
        <div class="info-row">
          <span class="label">Normativas:</span>
          <span class="value">
            {% if compliance_requirements %}
              {{ compliance_requirements|join(', ') }}
            {% else %}
              Ninguna especificada
            {% endif %}
          </span>
        </div>
        <div class="info-row"><span class="label">Presión de clientes:</span><span class="value">{% if clients_demand_security %}✓ Sí{% else %}✗ No{% endif %}</span></div>
        <div class="info-row"><span class="label">Seguro cibernético:</span><span class="value">{% if has_cyber_insurance %}✓ Sí{% else %}✗ No{% endif %}</span></div>
      </div>

      <div class="section">
        <h2>🔍 Capacidad de Monitoreo y Respuesta</h2>
        <table>
          <tr>
            <th>Capacidad</th>
            <th>Disponible</th>
          </tr>
          <tr>
            <td>Monitoreo 24/7</td>
            <td><span class="{% if has_24_7_monitoring %}yes{% else %}no{% endif %}">{% if has_24_7_monitoring %}✓ Sí{% else %}✗ No{% endif %}</span></td>
          </tr>
          <tr>
            <td>Logs centralizados</td>
            <td><span class="{% if has_centralized_logs %}yes{% else %}no{% endif %}">{% if has_centralized_logs %}✓ Sí{% else %}✗ No{% endif %}</span></td>
          </tr>
          <tr>
            <td>Reconstrucción de incidentes</td>
            <td><span class="{% if can_reconstruct_incident %}yes{% else %}no{% endif %}">{% if can_reconstruct_incident %}✓ Sí{% else %}✗ No{% endif %}</span></td>
          </tr>
        </table>
      </div>

      {% if comments %}
      <div class="section">
        <h2>💬 Comentarios Adicionales</h2>
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 4px; border-left: 4px solid #667eea;">
          {{ comments }}
        </div>
      </div>
      {% endif %}

      <div class="footer">
        <p>Formulario recibido el: {{ submitted_at }}</p>
        <p>🔐 Jeturing Security — Innovate. Secure. Transform.</p>
      </div>
    </div>
  </body>
</html>
"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def send_email(to_email: str, subject: str, html_content: str, from_email: str = None) -> bool:
    """
    Enviar email usando SMTP
    Soporta tanto STARTTLS (puerto 587) como SSL (puerto 465)
    """
    try:
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        smtp_ssl = os.getenv('SMTP_SSL', 'False').lower() == 'true'
        from_email = from_email or os.getenv('SMTP_FROM_EMAIL', 'no-reply@sajet.us')

        if not smtp_user or not smtp_password:
            logger.warning("SMTP credentials not configured. Email sending disabled.")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        msg.attach(MIMEText(html_content, 'html'))

        # Usar SSL directo para puerto 465, STARTTLS para puerto 587
        if smtp_ssl or smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

        logger.info(f"✅ Email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"❌ Error sending email: {str(e)}")
        return False


def generate_html_report(data: dict) -> str:
    """
    Generar reporte HTML a partir de los datos del formulario
    """
    template = Template(EMAIL_TEMPLATE)
    return template.render(**data)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/submit")
async def submit_security_checklist(
    data: SecurityChecklistRequest,
    background_tasks: BackgroundTasks
):
    """
    Recibir y procesar el formulario de seguridad
    Envía automáticamente el informe a sales@jeturing.com
    """
    try:
        # Convertir datos a diccionario
        checklist_dict = data.dict()

        # Generar reporte HTML
        html_report = generate_html_report(checklist_dict)

        # Enqueue email tasks
        background_tasks.add_task(
            send_email,
            to_email="sales@jeturing.com",
            subject=f"🛡️ Nuevo Checklist de Seguridad - {data.company_name} ({data.recommended_tier})",
            html_content=html_report
        )

        # Opcional: enviar confirmación al cliente (si tuviera email)
        # background_tasks.add_task(
        #     send_email,
        #     to_email=customer_email,
        #     subject="Confirmación: Tu Checklist de Ciberseguridad ha sido recibido",
        #     html_content=f"<p>Hola,<br><br>Gracias por completar nuestro checklist. Un especialista se pondrá en contacto pronto.</p>"
        # )

        return {
            "success": True,
            "message": "Formulario enviado exitosamente",
            "recommended_tier": data.recommended_tier,
            "risk_score": data.risk_score
        }

    except Exception as e:
        logger.error(f"Error submitting checklist: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el formulario: {str(e)}"
        )


@router.get("/status")
async def checklist_status():
    """Health check para endpoint de checklist"""
    return {
        "status": "operational",
        "service": "Security Checklist",
        "email_configured": bool(os.getenv('SMTP_USER')),
        "timestamp": datetime.utcnow().isoformat()
    }
