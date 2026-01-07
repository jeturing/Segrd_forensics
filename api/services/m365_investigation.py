"""
M365 Investigation Service - Ejecuta investigaciones reales usando Microsoft Graph API
Recopila evidencia de Azure AD, Exchange, SharePoint directamente del tenant
"""

import httpx
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import os
from api.config import settings

logger = logging.getLogger(__name__)

EVIDENCE_DIR = settings.EVIDENCE_DIR


class M365InvestigationService:
    """Servicio para ejecutar investigaciones M365 reales usando Graph API"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._token_expiry = None
    
    async def get_token(self) -> Optional[str]:
        """Obtener token de acceso para Microsoft Graph"""
        # Cache token si no ha expirado
        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._token
        
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    token_data = response.json()
                    self._token = token_data.get("access_token")
                    # Token expira en ~1 hora, guardar con margen
                    self._token_expiry = datetime.utcnow() + timedelta(minutes=50)
                    return self._token
                else:
                    logger.error(f"Error obteniendo token: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error de conexión: {e}")
            return None
    
    async def run_full_investigation(
        self, 
        case_id: str, 
        days_back: int = 90,
        target_users: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta investigación completa del tenant M365
        
        Recopila:
        1. Risky Sign-ins (inicios de sesión de riesgo)
        2. Risky Users (usuarios marcados como riesgosos)
        3. Sign-in Logs (todos los inicios de sesión)
        4. Audit Logs (cambios en Azure AD)
        5. OAuth App Consents (aplicaciones con permisos)
        6. Mailbox Rules (reglas de correo)
        7. Mail Forwarding (reenvíos configurados)
        """
        token = await self.get_token()
        if not token:
            return {"status": "failed", "error": "No se pudo autenticar con Microsoft Graph"}
        
        # Crear directorio de evidencia
        evidence_path = EVIDENCE_DIR / case_id / "m365_graph"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        results = {
            "status": "running",
            "case_id": case_id,
            "tenant_id": self.tenant_id,
            "started_at": datetime.utcnow().isoformat(),
            "evidence_path": str(evidence_path),
            "collections": {}
        }
        
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        try:
            # 1. Risky Sign-ins
            logger.info(f"🔍 [{case_id}] Recopilando Risky Sign-ins...")
            risky_signins = await self._collect_risky_signins(token, start_date)
            await self._save_evidence(evidence_path / "risky_signins.json", risky_signins)
            results["collections"]["risky_signins"] = len(risky_signins)
            
            # 2. Risky Users
            logger.info(f"🔍 [{case_id}] Recopilando Risky Users...")
            risky_users = await self._collect_risky_users(token)
            await self._save_evidence(evidence_path / "risky_users.json", risky_users)
            results["collections"]["risky_users"] = len(risky_users)
            
            # 3. Sign-in Logs (filtrados por usuarios objetivo si aplica)
            logger.info(f"🔍 [{case_id}] Recopilando Sign-in Logs...")
            signins = await self._collect_signin_logs(token, start_date, target_users)
            await self._save_evidence(evidence_path / "signin_logs.json", signins)
            results["collections"]["signin_logs"] = len(signins)
            
            # 4. Audit Logs
            logger.info(f"🔍 [{case_id}] Recopilando Audit Logs...")
            audits = await self._collect_audit_logs(token, start_date)
            await self._save_evidence(evidence_path / "audit_logs.json", audits)
            results["collections"]["audit_logs"] = len(audits)
            
            # 5. OAuth Applications (Service Principals con permisos delegados)
            logger.info(f"🔍 [{case_id}] Recopilando OAuth App Consents...")
            oauth_apps = await self._collect_oauth_consents(token)
            await self._save_evidence(evidence_path / "oauth_consents.json", oauth_apps)
            results["collections"]["oauth_consents"] = len(oauth_apps)
            
            # 6. Users con análisis de riesgo
            logger.info(f"🔍 [{case_id}] Analizando usuarios...")
            users = await self._collect_users_with_risk(token, target_users)
            await self._save_evidence(evidence_path / "users_analysis.json", users)
            results["collections"]["users_analyzed"] = len(users)
            
            # 7. Inbox Rules (requiere Exchange permissions)
            logger.info(f"🔍 [{case_id}] Buscando reglas de buzón sospechosas...")
            inbox_rules = await self._collect_inbox_rules(token, target_users or [u["upn"] for u in users[:20]])
            await self._save_evidence(evidence_path / "inbox_rules.json", inbox_rules)
            results["collections"]["inbox_rules"] = len(inbox_rules)
            
            # Generar resumen
            results["status"] = "completed"
            results["completed_at"] = datetime.utcnow().isoformat()
            results["summary"] = self._generate_summary(results["collections"], risky_signins, risky_users, oauth_apps, inbox_rules)
            
            # Guardar resumen
            await self._save_evidence(evidence_path / "investigation_summary.json", results)
            
            logger.info(f"✅ [{case_id}] Investigación M365 completada")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ [{case_id}] Error en investigación: {e}", exc_info=True)
            results["status"] = "failed"
            results["error"] = str(e)
            return results
    
    async def _collect_risky_signins(self, token: str, start_date: datetime) -> List[Dict]:
        """Recopilar inicios de sesión de riesgo"""
        signins = []
        url = "https://graph.microsoft.com/v1.0/auditLogs/signIns"
        params = {
            "$filter": f"createdDateTime ge {start_date.isoformat()}Z and (riskLevelDuringSignIn eq 'high' or riskLevelDuringSignIn eq 'medium' or riskState eq 'atRisk')",
            "$top": "500",
            "$orderby": "createdDateTime desc"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
                if response.status_code == 200:
                    signins = response.json().get("value", [])
                elif response.status_code == 403:
                    logger.warning("⚠️ Sin permisos para AuditLog.Read.All - usando endpoint alternativo")
                else:
                    logger.warning(f"⚠️ Error risky signins: {response.status_code}")
        except Exception as e:
            logger.error(f"Error recopilando risky signins: {e}")
        
        return signins
    
    async def _collect_risky_users(self, token: str) -> List[Dict]:
        """Recopilar usuarios de riesgo"""
        users = []
        url = "https://graph.microsoft.com/v1.0/identityProtection/riskyUsers"
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                if response.status_code == 200:
                    users = response.json().get("value", [])
                elif response.status_code == 403:
                    logger.warning("⚠️ Sin permisos para IdentityRiskyUser.Read.All")
        except Exception as e:
            logger.error(f"Error recopilando risky users: {e}")
        
        return users
    
    async def _collect_signin_logs(self, token: str, start_date: datetime, target_users: Optional[List[str]] = None) -> List[Dict]:
        """Recopilar logs de inicio de sesión"""
        signins = []
        url = "https://graph.microsoft.com/v1.0/auditLogs/signIns"
        
        filter_parts = [f"createdDateTime ge {start_date.isoformat()}Z"]
        if target_users:
            user_filters = " or ".join([f"userPrincipalName eq '{u}'" for u in target_users[:10]])
            filter_parts.append(f"({user_filters})")
        
        params = {
            "$filter": " and ".join(filter_parts),
            "$top": "500",
            "$orderby": "createdDateTime desc"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
                if response.status_code == 200:
                    signins = response.json().get("value", [])
        except Exception as e:
            logger.error(f"Error recopilando signin logs: {e}")
        
        return signins
    
    async def _collect_audit_logs(self, token: str, start_date: datetime) -> List[Dict]:
        """Recopilar logs de auditoría de Azure AD"""
        audits = []
        url = "https://graph.microsoft.com/v1.0/auditLogs/directoryAudits"
        params = {
            "$filter": f"activityDateTime ge {start_date.isoformat()}Z",
            "$top": "500",
            "$orderby": "activityDateTime desc"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
                if response.status_code == 200:
                    audits = response.json().get("value", [])
        except Exception as e:
            logger.error(f"Error recopilando audit logs: {e}")
        
        return audits
    
    async def _collect_oauth_consents(self, token: str) -> List[Dict]:
        """Recopilar consentimientos de aplicaciones OAuth"""
        apps = []
        url = "https://graph.microsoft.com/v1.0/oauth2PermissionGrants"
        params = {"$top": "500"}
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
                if response.status_code == 200:
                    grants = response.json().get("value", [])
                    
                    # Enriquecer con información del service principal
                    for grant in grants:
                        client_id = grant.get("clientId")
                        if client_id:
                            sp_response = await client.get(
                                f"https://graph.microsoft.com/v1.0/servicePrincipals/{client_id}",
                                headers={"Authorization": f"Bearer {token}"}
                            )
                            if sp_response.status_code == 200:
                                sp_data = sp_response.json()
                                grant["appDisplayName"] = sp_data.get("displayName")
                                grant["appPublisher"] = sp_data.get("publisherName")
                                grant["appHomepage"] = sp_data.get("homepage")
                        apps.append(grant)
        except Exception as e:
            logger.error(f"Error recopilando OAuth consents: {e}")
        
        return apps
    
    async def _collect_users_with_risk(self, token: str, target_users: Optional[List[str]] = None) -> List[Dict]:
        """Recopilar usuarios con análisis de riesgo"""
        users = []
        url = "https://graph.microsoft.com/v1.0/users"
        params = {
            "$select": "id,displayName,userPrincipalName,mail,accountEnabled,createdDateTime,lastSignInDateTime",
            "$top": "100"
        }
        
        if target_users:
            filters = " or ".join([f"userPrincipalName eq '{u}'" for u in target_users[:20]])
            params["$filter"] = filters
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
                if response.status_code == 200:
                    for user in response.json().get("value", []):
                        users.append({
                            "id": user.get("id"),
                            "displayName": user.get("displayName"),
                            "upn": user.get("userPrincipalName"),
                            "mail": user.get("mail"),
                            "enabled": user.get("accountEnabled"),
                            "created": user.get("createdDateTime"),
                            "lastSignIn": user.get("lastSignInDateTime")
                        })
        except Exception as e:
            logger.error(f"Error recopilando users: {e}")
        
        return users
    
    async def _collect_inbox_rules(self, token: str, user_upns: List[str]) -> List[Dict]:
        """Recopilar reglas de buzón (requiere permisos de Exchange)"""
        all_rules = []
        
        for upn in user_upns[:20]:  # Limitar para no sobrecargar
            url = f"https://graph.microsoft.com/v1.0/users/{upn}/mailFolders/inbox/messageRules"
            
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                    if response.status_code == 200:
                        rules = response.json().get("value", [])
                        for rule in rules:
                            # Detectar reglas sospechosas
                            actions = rule.get("actions", {})
                            is_suspicious = (
                                actions.get("forwardTo") or 
                                actions.get("forwardAsAttachmentTo") or
                                actions.get("redirectTo") or
                                actions.get("delete") or
                                actions.get("moveToFolder") == "deleteditems"
                            )
                            rule["userPrincipalName"] = upn
                            rule["isSuspicious"] = is_suspicious
                            all_rules.append(rule)
            except Exception as e:
                logger.debug(f"No se pudieron obtener reglas para {upn}: {e}")
        
        return all_rules
    
    async def _save_evidence(self, filepath: Path, data: Any):
        """Guardar evidencia en archivo JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"💾 Guardado: {filepath}")
        except Exception as e:
            logger.error(f"Error guardando {filepath}: {e}")
    
    def _generate_summary(
        self, 
        collections: Dict, 
        risky_signins: List, 
        risky_users: List,
        oauth_apps: List,
        inbox_rules: List
    ) -> Dict:
        """Generar resumen de la investigación"""
        
        # Contar severidades
        high_risk_signins = len([s for s in risky_signins if s.get("riskLevelDuringSignIn") == "high"])
        medium_risk_signins = len([s for s in risky_signins if s.get("riskLevelDuringSignIn") == "medium"])
        
        # Contar usuarios de riesgo
        high_risk_users = len([u for u in risky_users if u.get("riskLevel") == "high"])
        
        # Detectar apps con permisos peligrosos
        dangerous_permissions = ["Mail.Read", "Mail.Send", "Files.ReadWrite.All", "User.ReadWrite.All", "Directory.ReadWrite.All"]
        risky_apps = []
        for app in oauth_apps:
            scope = app.get("scope", "")
            if any(perm in scope for perm in dangerous_permissions):
                risky_apps.append(app.get("appDisplayName", app.get("clientId")))
        
        # Reglas de reenvío sospechosas
        suspicious_rules = [r for r in inbox_rules if r.get("isSuspicious")]
        
        # Calcular score de riesgo
        risk_score = 0
        risk_score += high_risk_signins * 15
        risk_score += medium_risk_signins * 5
        risk_score += high_risk_users * 20
        risk_score += len(risky_apps) * 10
        risk_score += len(suspicious_rules) * 25
        risk_score = min(100, risk_score)  # Cap at 100
        
        return {
            "risk_score": risk_score,
            "critical_findings": {
                "high_risk_signins": high_risk_signins,
                "medium_risk_signins": medium_risk_signins,
                "high_risk_users": high_risk_users,
                "risky_oauth_apps": len(risky_apps),
                "suspicious_inbox_rules": len(suspicious_rules)
            },
            "risky_apps": risky_apps[:10],
            "suspicious_rules_users": [r.get("userPrincipalName") for r in suspicious_rules],
            "total_evidence_items": sum(collections.values())
        }


# Función de conveniencia para crear servicio
def create_m365_investigation_service() -> Optional[M365InvestigationService]:
    """Crear servicio de investigación M365 desde variables de entorno"""
    tenant_id = os.getenv("M365_TENANT_ID")
    client_id = os.getenv("M365_CLIENT_ID")
    client_secret = os.getenv("M365_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        logger.error("❌ Credenciales M365 no configuradas en .env")
        return None
    
    return M365InvestigationService(tenant_id, client_id, client_secret)
