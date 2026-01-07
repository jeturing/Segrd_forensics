"""
OAuth Authentication Router
Device Code Flow para autenticación de Azure AD desde el dashboard
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/oauth", tags=["OAuth Authentication"])
logger = logging.getLogger(__name__)

# Store para device codes temporales (en producción usar Redis)
device_code_store = {}


class DeviceCodeInitRequest(BaseModel):
    """Iniciar flujo de Device Code"""
    tenant_id: str
    scopes: Optional[list] = [
        # Lectura de directorio/identidad (solo lectura)
        "User.Read",
        "Directory.Read.All",
        "AuditLog.Read.All",
        "IdentityRiskEvent.Read.All",
        "Reports.Read.All",
        "SecurityEvents.Read.All"
    ]


class DeviceCodeResponse(BaseModel):
    """Respuesta con código de dispositivo"""
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int
    message: str


class TokenExchangeRequest(BaseModel):
    """Intercambiar device code por token"""
    device_code: str
    tenant_id: str


@router.post("/device-code/init", response_model=DeviceCodeResponse)
async def init_device_code_flow(request: DeviceCodeInitRequest):
    """
    Inicia el flujo de Device Code de OAuth 2.0
    
    El usuario debe:
    1. Abrir la URL de verificación en su navegador
    2. Ingresar el código mostrado
    3. Completar autenticación (con MFA si está habilitado)
    4. La app verificará automáticamente el código
    
    ## Ejemplo de uso:
    ```bash
    curl -X POST http://localhost:9000/api/oauth/device-code/init \
      -H "Content-Type: application/json" \
      -d '{"tenant_id": "xxx-tenant-id"}'
    ```
    """
    try:
        import msal
        
        # Usar client_id genérico para Device Code Flow
        # En producción, usar App Registration propia del tenant
        client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Azure CLI oficial
        authority = f"https://login.microsoftonline.com/{request.tenant_id}"
        
        # Crear aplicación MSAL
        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
            token_cache=None  # Sin cache para cada request
        )
        
        # Iniciar flujo de device code con timeout
        try:
            flow = app.initiate_device_flow(scopes=request.scopes)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error al iniciar Device Code: {str(e)[:200]}"
            )
        
        if "error" in flow:
            error_desc = flow.get('error_description', flow.get('error', 'Unknown error'))
            raise HTTPException(
                status_code=400,
                detail=f"Error al iniciar flujo: {error_desc[:200]}"
            )
        
        # Guardar device code temporalmente
        device_code_store[flow["device_code"]] = {
            "tenant_id": request.tenant_id,
            "flow": flow,
            "app": app,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=flow["expires_in"])
        }
        
        logger.info(f"🔐 Device Code iniciado para tenant {request.tenant_id}")
        
        return DeviceCodeResponse(
            device_code=flow["device_code"],
            user_code=flow["user_code"],
            verification_uri=flow["verification_uri"],
            expires_in=flow["expires_in"],
            interval=flow["interval"],
            message=flow["message"]
        )
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="MSAL library not installed. Run: pip install msal"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en device code flow: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)[:200]}"
        )


@router.post("/device-code/poll")
async def poll_device_code(request: TokenExchangeRequest):
    """
    Verifica si el usuario ha completado la autenticación
    
    Debe llamarse cada 5 segundos hasta que:
    - Se obtenga el token (success)
    - Expire el código (expired)
    - El usuario cancele (cancelled)
    """
    try:
        device_code = request.device_code
        
        if device_code not in device_code_store:
            raise HTTPException(status_code=404, detail="Device code not found or expired")
        
        stored = device_code_store[device_code]
        
        # Verificar expiración
        if datetime.utcnow() > stored["expires_at"]:
            del device_code_store[device_code]
            raise HTTPException(status_code=410, detail="Device code expired")
        
        # Intentar obtener token
        app = stored["app"]
        flow = stored["flow"]
        
        try:
            result = app.acquire_token_by_device_flow(flow)
        except Exception as e:
            logger.error(f"Error adquiriendo token: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al adquirir token: {str(e)[:150]}"
            )
        
        if "error" in result:
            error = result.get("error")
            
            # authorization_pending = usuario aún no completó auth
            if error == "authorization_pending":
                return {
                    "status": "pending",
                    "message": "Esperando que el usuario complete la autenticación..."
                }
            
            # Otros errores
            error_desc = result.get("error_description", error)
            logger.warning(f"⚠️  Token error: {error} - {error_desc}")
            
            raise HTTPException(
                status_code=400,
                detail=error_desc[:200]
            )
        
        # ¡Token obtenido exitosamente!
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        expires_in = result.get("expires_in", 3599)
        
        # Limpiar device code
        del device_code_store[device_code]
        
        # Guardar token en base de datos (TODO: implementar)
        # Por ahora, retornar para que el frontend lo guarde
        
        logger.info(f"✅ Token obtenido para tenant {request.tenant_id}")
        
        return {
            "status": "success",
            "message": "Autenticación completada exitosamente",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "token_type": "Bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verificando device code: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)[:150]}")


@router.delete("/device-code/cancel")
async def cancel_device_code(request: TokenExchangeRequest):
    """Cancela el flujo de device code"""
    try:
        if request.device_code in device_code_store:
            del device_code_store[request.device_code]
            logger.info("🚫 Device code cancelado")
            return {"status": "cancelled", "message": "Device code flow cancelado"}
        
        raise HTTPException(status_code=404, detail="Device code not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def oauth_status():
    """Estado del servicio OAuth"""
    try:
        import msal
        msal_installed = True
    except ImportError:
        msal_installed = False
    
    active_flows = len(device_code_store)
    
    return {
        "status": "operational" if msal_installed else "msal_not_installed",
        "msal_installed": msal_installed,
        "active_device_flows": active_flows,
        "supported_flows": ["device_code"],
        "message": "OAuth 2.0 Device Code Flow ready" if msal_installed else "Install msal library"
    }
