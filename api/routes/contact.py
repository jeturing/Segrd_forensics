"""
Contact Form API Routes (v4.6.1)
Handles contact form submissions and email sending via SMTP
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from api.config import settings

router = APIRouter(prefix="/contact", tags=["Contact"])
logger = logging.getLogger("contact")


class ContactFormRequest(BaseModel):
    """Contact form submission model"""
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    message: str
    interest: str = "demo"
    submitted_at: Optional[str] = None


class ContactFormResponse(BaseModel):
    """Contact form response model"""
    success: bool
    message: str
    reference_id: Optional[str] = None


def send_email_smtp(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str
) -> bool:
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)
        
        # Connect and send
        if settings.SMTP_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        
        logger.info(f"📧 Email enviado a {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
        return False


def generate_contact_email_html(data: ContactFormRequest, reference_id: str) -> str:
    """Generate HTML email body for contact form"""
    interest_labels = {
        "demo": "Solicitar Demo",
        "pricing": "Información de Precios",
        "foren": "Módulo FOREN (Forense)",
        "axion": "Módulo AXION (Respuesta a Incidentes)",
        "vigil": "Módulo VIGIL (Monitoreo)",
        "orbia": "Módulo ORBIA (Automatización)",
        "enterprise": "Plan Enterprise",
        "partnership": "Partnership",
        "other": "Otro"
    }
    
    interest_text = interest_labels.get(data.interest, data.interest)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background-color: #111827; color: #f3f4f6; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #1f2937; border-radius: 12px; padding: 30px; border: 1px solid #374151; }}
            h1 {{ color: #22d3ee; margin-bottom: 20px; font-size: 24px; }}
            .label {{ color: #9ca3af; font-size: 12px; text-transform: uppercase; margin-bottom: 4px; }}
            .value {{ color: #f3f4f6; font-size: 16px; margin-bottom: 16px; }}
            .message-box {{ background-color: #374151; border-radius: 8px; padding: 16px; margin-top: 20px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #374151; color: #6b7280; font-size: 12px; }}
            .badge {{ display: inline-block; background: linear-gradient(to right, #06b6d4, #3b82f6); color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📩 Nuevo Contacto - SEGRD</h1>
            
            <p class="label">Referencia</p>
            <p class="value"><span class="badge">{reference_id}</span></p>
            
            <p class="label">Nombre</p>
            <p class="value">{data.name}</p>
            
            <p class="label">Email</p>
            <p class="value"><a href="mailto:{data.email}" style="color: #22d3ee;">{data.email}</a></p>
            
            <p class="label">Empresa</p>
            <p class="value">{data.company or "No especificada"}</p>
            
            <p class="label">Teléfono</p>
            <p class="value">{data.phone or "No especificado"}</p>
            
            <p class="label">Interés</p>
            <p class="value">{interest_text}</p>
            
            <p class="label">Mensaje</p>
            <div class="message-box">
                {data.message.replace(chr(10), '<br>')}
            </div>
            
            <div class="footer">
                <p>Este mensaje fue enviado desde el formulario de contacto de <strong>segrd.com</strong></p>
                <p>Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
            </div>
        </div>
    </body>
    </html>
    """


def generate_contact_email_text(data: ContactFormRequest, reference_id: str) -> str:
    """Generate plain text email body for contact form"""
    return f"""
NUEVO CONTACTO - SEGRD
======================
Referencia: {reference_id}

Nombre: {data.name}
Email: {data.email}
Empresa: {data.company or "No especificada"}
Teléfono: {data.phone or "No especificado"}
Interés: {data.interest}

MENSAJE:
--------
{data.message}

---
Enviado desde segrd.com
Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC
    """


async def process_contact_form(data: ContactFormRequest, reference_id: str):
    """Background task to process contact form and send email"""
    try:
        html_body = generate_contact_email_html(data, reference_id)
        text_body = generate_contact_email_text(data, reference_id)
        
        success = send_email_smtp(
            to_email=settings.SMTP_CONTACT_TO,
            subject=f"[SEGRD Contact] {data.interest.upper()} - {data.name}",
            html_body=html_body,
            text_body=text_body
        )
        
        if success:
            logger.info(f"✅ Formulario {reference_id} procesado y email enviado")
        else:
            logger.error(f"❌ Error enviando email para {reference_id}")
            
    except Exception as e:
        logger.error(f"❌ Error procesando formulario {reference_id}: {e}")


@router.post("/submit", response_model=ContactFormResponse)
async def submit_contact_form(
    data: ContactFormRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a contact form
    
    Receives contact form data and sends an email to sales@jeturing.com
    """
    # Generate reference ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    reference_id = f"SEGRD-{timestamp}"
    
    # Validate required fields
    if not data.name or not data.email or not data.message:
        raise HTTPException(status_code=400, detail="Nombre, email y mensaje son requeridos")
    
    # Check SMTP configuration
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("⚠️ SMTP no configurado, guardando formulario sin enviar email")
        # In production, you might want to save to database here
        return ContactFormResponse(
            success=True,
            message="Formulario recibido. Te contactaremos pronto.",
            reference_id=reference_id
        )
    
    # Process in background
    background_tasks.add_task(process_contact_form, data, reference_id)
    
    logger.info(f"📬 Formulario de contacto recibido: {reference_id} - {data.name} <{data.email}>")
    
    return ContactFormResponse(
        success=True,
        message="Mensaje enviado correctamente. Te contactaremos pronto.",
        reference_id=reference_id
    )


@router.get("/health")
async def contact_health():
    """Check if contact form service is available"""
    smtp_configured = bool(settings.SMTP_USER and settings.SMTP_PASSWORD)
    
    return {
        "status": "available",
        "smtp_configured": smtp_configured,
        "smtp_host": settings.SMTP_HOST if smtp_configured else None,
        "destination": settings.SMTP_CONTACT_TO
    }
