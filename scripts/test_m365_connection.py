"""
Test de conexión a Microsoft 365 con las credenciales configuradas
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.config import settings
import asyncio

async def test_m365_connection():
    """Probar conexión a Microsoft Graph API"""
    
    print("\n" + "="*60)
    print("🔍 Test de Conexión Microsoft 365")
    print("="*60 + "\n")
    
    # Verificar configuración
    print("📋 Configuración actual:")
    print(f"   Tenant ID:     {settings.M365_TENANT_ID or '❌ NO CONFIGURADO'}")
    print(f"   Client ID:     {settings.M365_CLIENT_ID or '❌ NO CONFIGURADO'}")
    print(f"   Client Secret: {'✅ Configurado' if settings.M365_CLIENT_SECRET else '❌ NO CONFIGURADO'}")
    print()
    
    if not all([settings.M365_TENANT_ID, settings.M365_CLIENT_ID, settings.M365_CLIENT_SECRET]):
        print("❌ Credenciales incompletas. Ejecuta:")
        print("   ./scripts/setup_m365_interactive.sh")
        return False
    
    try:
        import httpx
        
        print("🔐 Autenticando con Microsoft Graph API...")
        
        # Obtener token
        token_url = f"https://login.microsoftonline.com/{settings.M365_TENANT_ID}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    'client_id': settings.M365_CLIENT_ID,
                    'client_secret': settings.M365_CLIENT_SECRET,
                    'scope': 'https://graph.microsoft.com/.default',
                    'grant_type': 'client_credentials'
                },
                timeout=30
            )
            
            if response.status_code != 200:
                error = response.json()
                print(f"❌ Error de autenticación: {error.get('error_description', 'Error desconocido')}")
                return False
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            print("✅ Token obtenido exitosamente")
            print()
            
            # Probar acceso a Graph API
            print("📊 Probando acceso a Microsoft Graph...")
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Test 1: Organization info
            org_response = await client.get(
                'https://graph.microsoft.com/v1.0/organization',
                headers=headers,
                timeout=30
            )
            
            if org_response.status_code == 200:
                org_data = org_response.json()
                if org_data.get('value'):
                    org = org_data['value'][0]
                    print(f"✅ Organización: {org.get('displayName', 'N/A')}")
                    print(f"   Dominio verificado: {org.get('verifiedDomains', [{}])[0].get('name', 'N/A')}")
            else:
                print(f"⚠️  No se pudo obtener info de organización (código {org_response.status_code})")
            
            # Test 2: Audit logs
            print()
            print("📝 Probando acceso a Audit Logs...")
            
            audit_response = await client.get(
                'https://graph.microsoft.com/v1.0/auditLogs/signIns?$top=1',
                headers=headers,
                timeout=30
            )
            
            if audit_response.status_code == 200:
                print("✅ Acceso a Audit Logs: OK")
            elif audit_response.status_code == 403:
                print("⚠️  Sin permisos para Audit Logs")
                print("   Ejecuta en portal Azure:")
                print(f"   https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/{settings.M365_CLIENT_ID}")
                print("   Y aprueba los permisos de aplicación")
            else:
                print(f"⚠️  Error al acceder a Audit Logs (código {audit_response.status_code})")
            
            # Test 3: Users
            print()
            print("👥 Probando acceso a Users...")
            
            users_response = await client.get(
                'https://graph.microsoft.com/v1.0/users?$top=1',
                headers=headers,
                timeout=30
            )
            
            if users_response.status_code == 200:
                print("✅ Acceso a Users: OK")
            elif users_response.status_code == 403:
                print("⚠️  Sin permisos para Users")
            else:
                print(f"⚠️  Error al acceder a Users (código {users_response.status_code})")
            
            print()
            print("="*60)
            print("✅ Test completado")
            print("="*60)
            print()
            
            return True
            
    except ImportError:
        print("❌ Falta la librería httpx. Instala con:")
        print("   pip install httpx")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    return asyncio.run(test_m365_connection())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
