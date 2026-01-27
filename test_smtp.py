#!/usr/bin/env python3
"""
Test SMTP Connection
Script para verificar que las credenciales SMTP funcionan correctamente
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

def test_smtp():
    """Probar conexión SMTP"""
    
    smtp_host = os.getenv('SMTP_HOST', 'mail5010.site4now.net')
    smtp_port = int(os.getenv('SMTP_PORT', '465'))
    smtp_user = os.getenv('SMTP_USER', 'no-reply@sajet.us')
    smtp_password = os.getenv('SMTP_PASSWORD', '321Abcd.')
    smtp_ssl = os.getenv('SMTP_SSL', 'True').lower() == 'true'
    from_email = os.getenv('SMTP_FROM_EMAIL', 'no-reply@sajet.us')
    
    print("🧪 Probando conexión SMTP...")
    print(f"   Host: {smtp_host}")
    print(f"   Puerto: {smtp_port}")
    print(f"   Usuario: {smtp_user}")
    print(f"   SSL: {smtp_ssl}")
    print("")
    
    try:
        # Conectar
        if smtp_ssl or smtp_port == 465:
            print(f"📡 Conectando con SMTP_SSL en puerto {smtp_port}...")
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            print(f"📡 Conectando con SMTP en puerto {smtp_port}...")
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        
        print("✅ Conexión establecida")
        
        # Autenticar
        print(f"🔐 Autenticando como {smtp_user}...")
        server.login(smtp_user, smtp_password)
        print("✅ Autenticación exitosa")
        
        # Test: enviar email
        print("")
        print("💌 Enviando email de prueba...")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🧪 Test SMTP - Jeturing Security Checklist'
        msg['From'] = from_email
        msg['To'] = 'sales@jeturing.com'
        
        html = """
        <html>
          <body>
            <h1 style="color: green;">✅ Test SMTP Exitoso</h1>
            <p>Este es un email de prueba del sistema de formularios de Jeturing.</p>
            <p><strong>Las credenciales SMTP están correctamente configuradas.</strong></p>
            <p>El sistema de Security Checklist ya puede enviar reportes a sales@jeturing.com</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        server.send_message(msg)
        print("✅ Email enviado exitosamente")
        
        server.quit()
        
        print("")
        print("🎉 ¡Prueba SMTP completada exitosamente!")
        print("")
        print("📝 Resumen:")
        print(f"   ✅ Conexión SMTP: OK")
        print(f"   ✅ Autenticación: OK")
        print(f"   ✅ Envío de email: OK")
        print("")
        print("Sistema listo para usar.")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Error de autenticación: {str(e)}")
        print("   Verifica que el usuario y contraseña son correctos")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ Error SMTP: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_smtp()
    sys.exit(0 if success else 1)
