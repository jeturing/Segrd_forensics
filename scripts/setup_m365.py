#!/usr/bin/env python3
"""
Script para configurar automáticamente Microsoft 365 App Registration
Busca tenant ID y crea la aplicación con permisos necesarios
"""

import sys
import json
import subprocess
import getpass
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Instalando requests...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

# Colores para output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{NC}")

def print_error(msg):
    print(f"{RED}❌ {msg}{NC}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{NC}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{NC}")

class M365Setup:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.tenant_id = None
        self.access_token = None
        self.app_id = None
        self.app_secret = None
        
    def get_tenant_id(self):
        """Obtener tenant ID del dominio del usuario"""
        print_info("Obteniendo Tenant ID...")
        
        domain = self.username.split('@')[1]
        url = f"https://login.microsoftonline.com/{domain}/v2.0/.well-known/openid-configuration"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Extraer tenant ID de la URL
                token_endpoint = data.get('token_endpoint', '')
                tenant_id = token_endpoint.split('/')[3]
                self.tenant_id = tenant_id
                print_success(f"Tenant ID encontrado: {tenant_id}")
                return True
            else:
                print_error("No se pudo obtener el Tenant ID")
                return False
        except Exception as e:
            print_error(f"Error al buscar tenant: {e}")
            return False
    
    def get_access_token(self):
        """Obtener token de acceso usando credenciales del usuario"""
        print_info("Autenticando con Microsoft 365...")
        
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': '1b730954-1685-4b74-9bfd-dac224a7b894',  # Azure CLI client ID (público)
            'scope': 'https://graph.microsoft.com/.default',
            'username': self.username,
            'password': self.password,
            'grant_type': 'password'
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                print_success("Autenticación exitosa")
                return True
            else:
                error_data = response.json()
                error_desc = error_data.get('error_description', 'Error desconocido')
                
                if 'AADSTS50076' in error_desc or 'MFA' in error_desc:
                    print_error("La cuenta requiere autenticación multifactor (MFA)")
                    print_warning("Usa el método interactivo con Azure CLI:")
                    print("   az login")
                    print("   az account show --query tenantId -o tsv")
                    return False
                else:
                    print_error(f"Error de autenticación: {error_desc}")
                    return False
                    
        except Exception as e:
            print_error(f"Error al autenticar: {e}")
            return False
    
    def create_app_registration(self):
        """Crear App Registration con permisos necesarios para forensics"""
        print_info("Creando App Registration en Azure AD...")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Permisos requeridos para análisis forense
        required_permissions = {
            "requiredResourceAccess": [
                {
                    "resourceAppId": "00000003-0000-0000-c000-000000000000",  # Microsoft Graph
                    "resourceAccess": [
                        {"id": "230c1aed-a721-4c5d-9cb4-a90514e508ef", "type": "Role"},  # Directory.Read.All
                        {"id": "7ab1d382-f21e-4acd-a863-ba3e13f7da61", "type": "Role"},  # Directory.Read.All
                        {"id": "df021288-bdef-4463-88db-98f22de89214", "type": "Role"},  # User.Read.All
                        {"id": "b0afded3-3588-46d8-8b3d-9842eff778da", "type": "Role"},  # AuditLog.Read.All
                        {"id": "dc5007c0-2d7d-4c42-879c-2dab87571379", "type": "Role"},  # IdentityRiskEvent.Read.All
                        {"id": "6e472fd1-ad78-48da-a0f0-97ab2c6b769e", "type": "Role"},  # IdentityRiskyUser.Read.All
                        {"id": "7438b122-aefc-4978-80ed-43db9fcc7715", "type": "Role"},  # SecurityEvents.Read.All
                        {"id": "bf394140-e372-4bf9-a898-299cfc7564e5", "type": "Role"},  # SecurityEvents.ReadWrite.All
                        {"id": "dc377aa6-52d8-4e23-b271-2a7ae04cedf3", "type": "Role"},  # Mail.Read (Exchange)
                    ]
                }
            ]
        }
        
        app_manifest = {
            "displayName": "MCP Kali Forensics Worker",
            "signInAudience": "AzureADMyOrg",
            "requiredResourceAccess": required_permissions["requiredResourceAccess"]
        }
        
        try:
            # Crear aplicación
            response = requests.post(
                "https://graph.microsoft.com/v1.0/applications",
                headers=headers,
                json=app_manifest,
                timeout=30
            )
            
            if response.status_code == 201:
                app_data = response.json()
                self.app_id = app_data.get('appId')
                object_id = app_data.get('id')
                
                print_success(f"App creada exitosamente")
                print_success(f"Application ID: {self.app_id}")
                
                # Crear client secret
                secret_payload = {
                    "passwordCredential": {
                        "displayName": "MCP Forensics Secret",
                        "endDateTime": "2027-12-31T23:59:59Z"
                    }
                }
                
                secret_response = requests.post(
                    f"https://graph.microsoft.com/v1.0/applications/{object_id}/addPassword",
                    headers=headers,
                    json=secret_payload,
                    timeout=30
                )
                
                if secret_response.status_code == 200:
                    secret_data = secret_response.json()
                    self.app_secret = secret_data.get('secretText')
                    print_success("Client Secret generado")
                    
                    # Crear Service Principal
                    sp_payload = {"appId": self.app_id}
                    sp_response = requests.post(
                        "https://graph.microsoft.com/v1.0/servicePrincipals",
                        headers=headers,
                        json=sp_payload,
                        timeout=30
                    )
                    
                    if sp_response.status_code == 201:
                        print_success("Service Principal creado")
                        print_warning("IMPORTANTE: Un administrador debe aprobar los permisos en:")
                        print(f"   https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/{self.app_id}")
                        return True
                    else:
                        print_warning("Service Principal no creado, pero la app existe")
                        return True
                else:
                    print_error("No se pudo generar el Client Secret")
                    return False
            else:
                error_data = response.json()
                print_error(f"Error al crear app: {error_data.get('error', {}).get('message', 'Error desconocido')}")
                return False
                
        except Exception as e:
            print_error(f"Error al crear app: {e}")
            return False
    
    def save_to_env(self):
        """Guardar credenciales en .env"""
        print_info("Guardando credenciales en .env...")
        
        env_path = Path(__file__).parent.parent / '.env'
        
        # Leer .env existente
        env_content = []
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_content = f.readlines()
        
        # Actualizar o agregar valores
        updates = {
            'M365_TENANT_ID': self.tenant_id,
            'M365_CLIENT_ID': self.app_id,
            'M365_CLIENT_SECRET': self.app_secret
        }
        
        for key, value in updates.items():
            found = False
            for i, line in enumerate(env_content):
                if line.startswith(f'{key}='):
                    env_content[i] = f'{key}={value}\n'
                    found = True
                    break
            if not found:
                env_content.append(f'{key}={value}\n')
        
        # Guardar
        with open(env_path, 'w') as f:
            f.writelines(env_content)
        
        print_success(f"Credenciales guardadas en {env_path}")
        return True
    
    def run(self):
        """Ejecutar todo el proceso"""
        print("\n" + "="*60)
        print(f"{BLUE}🔧 Microsoft 365 - Configuración Automática{NC}")
        print("="*60 + "\n")
        
        # Paso 1: Obtener Tenant ID
        if not self.get_tenant_id():
            return False
        
        print()
        
        # Paso 2: Autenticar
        if not self.get_access_token():
            print()
            print_warning("ALTERNATIVA: Configuración manual")
            print("1. Ve a: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps")
            print("2. Click en 'New registration'")
            print("3. Nombre: MCP Kali Forensics")
            print("4. Agregar permisos de Microsoft Graph:")
            print("   - Directory.Read.All")
            print("   - User.Read.All")
            print("   - AuditLog.Read.All")
            print("   - SecurityEvents.Read.All")
            print("   - Mail.Read")
            print("5. Crear Client Secret en 'Certificates & secrets'")
            print("6. Guardar en .env:")
            print(f"   M365_TENANT_ID={self.tenant_id}")
            print("   M365_CLIENT_ID=<tu-app-id>")
            print("   M365_CLIENT_SECRET=<tu-secret>")
            return False
        
        print()
        
        # Paso 3: Crear App Registration
        if not self.create_app_registration():
            return False
        
        print()
        
        # Paso 4: Guardar en .env
        self.save_to_env()
        
        print("\n" + "="*60)
        print(f"{GREEN}✅ Configuración completada{NC}")
        print("="*60 + "\n")
        
        print("📋 Credenciales generadas:")
        print(f"   Tenant ID:     {self.tenant_id}")
        print(f"   Client ID:     {self.app_id}")
        print(f"   Client Secret: {self.app_secret[:10]}...{self.app_secret[-10:]}")
        print()
        print("⚠️  SIGUIENTE PASO REQUERIDO:")
        print("   Un administrador global debe aprobar los permisos en:")
        print(f"   {BLUE}https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/{self.app_id}{NC}")
        print()
        print("   O ejecutar este comando PowerShell como admin:")
        print(f"   Connect-MgGraph -Scopes 'Application.ReadWrite.All'")
        print(f"   Grant-MgServicePrincipalAppRoleAssignment -ServicePrincipalId <sp-id> -AppRoleId <role-id>")
        print()
        
        return True

def main():
    print(f"{BLUE}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   Microsoft 365 - Configuración Automática para MCP      ║")
    print("║   Kali Forensics & IR Worker                              ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{NC}\n")
    
    print("Este script configurará automáticamente:")
    print("  1. ✅ Buscar Tenant ID desde el dominio")
    print("  2. ✅ Crear App Registration en Azure AD")
    print("  3. ✅ Configurar permisos para análisis forense")
    print("  4. ✅ Generar Client Secret")
    print("  5. ✅ Guardar credenciales en .env")
    print()
    
    # Solicitar credenciales
    print_info("Ingresa las credenciales de administrador M365:")
    username = input("  Email: ").strip()
    password = getpass.getpass("  Password: ")
    
    if not username or not password:
        print_error("Credenciales inválidas")
        return 1
    
    print()
    
    # Ejecutar configuración
    setup = M365Setup(username, password)
    success = setup.run()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
