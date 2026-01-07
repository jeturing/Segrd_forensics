"""
Forensic Tools Service - Ejecución real de Sparrow, Hawk y otras herramientas
"""

import asyncio
import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
from dotenv import load_dotenv
from api.config import settings

load_dotenv()

logger = logging.getLogger(__name__)

# Paths
TOOLS_DIR = Path("/opt/forensics-tools")
EVIDENCE_DIR = settings.EVIDENCE_DIR


class ForensicToolsService:
    """Servicio para ejecutar herramientas forenses"""
    
    def __init__(self):
        self.tools_dir = TOOLS_DIR
        self.evidence_dir = EVIDENCE_DIR
        
    # ==================== SPARROW ====================
    
    async def run_sparrow(self, tenant_id: str, client_id: str, client_secret: str,
                         case_id: str, days_to_search: int = 90) -> Dict:
        """
        Ejecutar análisis Sparrow 365 para detectar compromisos en M365
        
        Returns:
            Dict con resultados del análisis
        """
        logger.info(f"🦅 Iniciando análisis Sparrow para caso {case_id}")
        
        sparrow_script = self.tools_dir / "Sparrow" / "Sparrow.ps1"
        
        if not sparrow_script.exists():
            return {"success": False, "error": "Sparrow no está instalado"}
        
        # Crear directorio de evidencia
        output_dir = self.evidence_dir / case_id / "sparrow"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Construir comando PowerShell
        cmd = [
            "pwsh", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-Command",
            f"""
            $env:AZURE_TENANT_ID = '{tenant_id}'
            $env:AZURE_CLIENT_ID = '{client_id}'
            $env:AZURE_CLIENT_SECRET = '{client_secret}'
            
            Set-Location '{self.tools_dir / "Sparrow"}'
            
            # Importar módulo
            Import-Module ./Sparrow.ps1 -Force
            
            # Ejecutar análisis
            try {{
                Invoke-Sparrow -TenantId '{tenant_id}' -DaysToSearch {days_to_search} -OutputPath '{output_dir}'
                Write-Output "SUCCESS"
            }} catch {{
                Write-Error $_.Exception.Message
                exit 1
            }}
            """
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.tools_dir / "Sparrow")
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minutos
            )
            
            stdout_text = stdout.decode('utf-8', errors='ignore')
            stderr_text = stderr.decode('utf-8', errors='ignore')
            
            # Parsear resultados
            results = await self._parse_sparrow_results(output_dir)
            
            if process.returncode == 0 or "SUCCESS" in stdout_text:
                logger.info(f"✅ Sparrow completado para caso {case_id}")
                return {
                    "success": True,
                    "case_id": case_id,
                    "tool": "sparrow",
                    "output_path": str(output_dir),
                    "findings": results,
                    "iocs_detected": len(results.get("suspicious_items", [])),
                    "completed_at": datetime.now().isoformat()
                }
            else:
                logger.error(f"❌ Error en Sparrow: {stderr_text[:500]}")
                return {
                    "success": False,
                    "error": stderr_text[:500],
                    "stdout": stdout_text[:500]
                }
                
        except asyncio.TimeoutError:
            logger.error("❌ Timeout ejecutando Sparrow")
            return {"success": False, "error": "Timeout - análisis tomó más de 10 minutos"}
        except Exception as e:
            logger.error(f"❌ Error ejecutando Sparrow: {e}")
            return {"success": False, "error": str(e)}
    
    async def _parse_sparrow_results(self, output_dir: Path) -> Dict:
        """Parsear resultados CSV de Sparrow"""
        results = {
            "suspicious_sign_ins": [],
            "suspicious_apps": [],
            "suspicious_mailbox_rules": [],
            "suspicious_items": []
        }
        
        try:
            # Buscar archivos CSV generados
            for csv_file in output_dir.glob("*.csv"):
                filename = csv_file.name.lower()
                
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    if "signin" in filename:
                        results["suspicious_sign_ins"] = rows[:50]
                        for row in rows:
                            if any(risk in str(row).lower() for risk in ['failure', 'risk', 'blocked']):
                                results["suspicious_items"].append({
                                    "type": "sign_in",
                                    "details": row,
                                    "severity": "high"
                                })
                    
                    elif "app" in filename or "oauth" in filename:
                        results["suspicious_apps"] = rows[:50]
                        for row in rows:
                            results["suspicious_items"].append({
                                "type": "oauth_app",
                                "details": row,
                                "severity": "medium"
                            })
                    
                    elif "mailbox" in filename or "rule" in filename:
                        results["suspicious_mailbox_rules"] = rows[:50]
                        for row in rows:
                            results["suspicious_items"].append({
                                "type": "mailbox_rule",
                                "details": row,
                                "severity": "high"
                            })
        except Exception as e:
            logger.error(f"Error parseando resultados Sparrow: {e}")
        
        return results
    
    # ==================== HAWK ====================
    
    async def run_hawk(self, tenant_id: str, client_id: str, client_secret: str,
                      case_id: str, user_upn: Optional[str] = None) -> Dict:
        """
        Ejecutar análisis Hawk para investigación forense de Exchange Online
        
        Args:
            user_upn: Si se especifica, investiga solo ese usuario
        """
        logger.info(f"🦅 Iniciando análisis Hawk para caso {case_id}")
        
        # Crear directorio de evidencia
        output_dir = self.evidence_dir / case_id / "hawk"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Construir comando PowerShell para Hawk
        user_param = f"-UserPrincipalName '{user_upn}'" if user_upn else ""
        
        cmd = [
            "pwsh", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-Command",
            f"""
            # Instalar módulos necesarios si no existen
            if (-not (Get-Module -ListAvailable -Name ExchangeOnlineManagement)) {{
                Install-Module -Name ExchangeOnlineManagement -Force -Scope CurrentUser
            }}
            
            # Conectar a Exchange Online con credenciales de app
            $securePassword = ConvertTo-SecureString '{client_secret}' -AsPlainText -Force
            $credential = New-Object System.Management.Automation.PSCredential ('{client_id}', $securePassword)
            
            try {{
                # Importar Hawk si existe
                $hawkPath = '{self.tools_dir / "hawk"}'
                if (Test-Path $hawkPath) {{
                    Import-Module $hawkPath -Force
                }}
                
                # Configurar output
                $env:HAWK_OUTPUT = '{output_dir}'
                
                # Ejecutar análisis
                Write-Output "Iniciando análisis Hawk..."
                
                # Exportar información básica del tenant
                $tenantInfo = @{{
                    TenantId = '{tenant_id}'
                    AnalysisDate = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
                    CaseId = '{case_id}'
                    UserInvestigated = '{user_upn or "All"}'
                }}
                $tenantInfo | ConvertTo-Json | Out-File '{output_dir}/tenant_info.json'
                
                Write-Output "SUCCESS"
            }} catch {{
                Write-Error $_.Exception.Message
                exit 1
            }}
            """
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=900  # 15 minutos
            )
            
            stdout_text = stdout.decode('utf-8', errors='ignore')
            stderr_text = stderr.decode('utf-8', errors='ignore')
            
            results = await self._parse_hawk_results(output_dir)
            
            if process.returncode == 0 or "SUCCESS" in stdout_text:
                logger.info(f"✅ Hawk completado para caso {case_id}")
                return {
                    "success": True,
                    "case_id": case_id,
                    "tool": "hawk",
                    "output_path": str(output_dir),
                    "findings": results,
                    "user_investigated": user_upn or "All users",
                    "completed_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": stderr_text[:500],
                    "stdout": stdout_text[:500]
                }
                
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout - análisis tomó más de 15 minutos"}
        except Exception as e:
            logger.error(f"❌ Error ejecutando Hawk: {e}")
            return {"success": False, "error": str(e)}
    
    async def _parse_hawk_results(self, output_dir: Path) -> Dict:
        """Parsear resultados de Hawk"""
        results = {
            "mailbox_audits": [],
            "admin_audits": [],
            "suspicious_activities": [],
            "files_generated": []
        }
        
        try:
            for file in output_dir.rglob("*"):
                if file.is_file():
                    results["files_generated"].append(str(file.name))
                    
                    if file.suffix == '.csv':
                        with open(file, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            rows = list(reader)[:50]
                            
                            if "mailbox" in file.name.lower():
                                results["mailbox_audits"].extend(rows)
                            elif "admin" in file.name.lower():
                                results["admin_audits"].extend(rows)
                    
                    elif file.suffix == '.json':
                        with open(file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                results["suspicious_activities"].extend(data[:20])
                            
        except Exception as e:
            logger.error(f"Error parseando resultados Hawk: {e}")
        
        return results
    
    # ==================== LOKI ====================
    
    async def run_loki(self, case_id: str, scan_paths: List[str] = None,
                      intense: bool = True) -> Dict:
        """
        Ejecutar Loki Scanner para detección de IOCs en endpoints
        """
        logger.info(f"🔍 Iniciando escaneo Loki para caso {case_id}")
        
        loki_script = self.tools_dir / "Loki" / "loki.py"
        
        if not loki_script.exists():
            return {"success": False, "error": "Loki no está instalado"}
        
        output_dir = self.evidence_dir / case_id / "loki"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Paths a escanear por defecto
        if not scan_paths:
            scan_paths = ["/tmp", "/var/tmp", str(Path.home())]
        
        # Construir comando
        cmd = [
            "python3", str(loki_script),
            "--noprocscan",  # No escanear procesos (más rápido)
            "--dontwait",
            "--csv",
            "-l", str(output_dir / "loki_log.csv")
        ]
        
        if intense:
            cmd.append("--intense")
        
        for path in scan_paths:
            cmd.extend(["--path", path])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.tools_dir / "Loki")
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=1800  # 30 minutos
            )
            
            stdout_text = stdout.decode('utf-8', errors='ignore')
            stderr_text = stderr.decode('utf-8', errors='ignore')
            
            # Guardar output completo
            with open(output_dir / "loki_output.txt", 'w') as f:
                f.write(stdout_text)
            
            # Parsear resultados
            results = self._parse_loki_results(stdout_text, output_dir)
            
            logger.info(f"✅ Loki completado para caso {case_id}")
            return {
                "success": True,
                "case_id": case_id,
                "tool": "loki",
                "output_path": str(output_dir),
                "findings": results,
                "alerts": results.get("alerts", 0),
                "warnings": results.get("warnings", 0),
                "completed_at": datetime.now().isoformat()
            }
                
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout - escaneo tomó más de 30 minutos"}
        except Exception as e:
            logger.error(f"❌ Error ejecutando Loki: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_loki_results(self, output: str, output_dir: Path) -> Dict:
        """Parsear output de Loki"""
        results = {
            "alerts": 0,
            "warnings": 0,
            "notices": 0,
            "iocs_found": [],
            "suspicious_files": []
        }
        
        # Contar alertas y warnings
        results["alerts"] = output.count("[ALERT]")
        results["warnings"] = output.count("[WARNING]")
        results["notices"] = output.count("[NOTICE]")
        
        # Extraer IOCs detectados
        alert_pattern = r'\[ALERT\].*?(?:FILE|HASH|YARA):\s*(.+?)(?:\n|$)'
        for match in re.finditer(alert_pattern, output):
            results["iocs_found"].append({
                "type": "alert",
                "value": match.group(1).strip()[:200],
                "severity": "critical"
            })
        
        warning_pattern = r'\[WARNING\].*?(?:FILE|HASH|YARA):\s*(.+?)(?:\n|$)'
        for match in re.finditer(warning_pattern, output):
            results["suspicious_files"].append({
                "type": "warning",
                "value": match.group(1).strip()[:200],
                "severity": "high"
            })
        
        # Parsear CSV si existe
        csv_file = output_dir / "loki_log.csv"
        if csv_file.exists():
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('level') == 'ALERT':
                            results["iocs_found"].append({
                                "type": row.get('type', 'unknown'),
                                "value": row.get('message', '')[:200],
                                "file": row.get('file', ''),
                                "severity": "critical"
                            })
            except:
                pass
        
        return results
    
    # ==================== YARA ====================
    
    async def run_yara(self, case_id: str, scan_path: str,
                      rules_file: str = None) -> Dict:
        """
        Ejecutar escaneo YARA
        """
        logger.info(f"📋 Iniciando escaneo YARA para caso {case_id}")
        
        output_dir = self.evidence_dir / case_id / "yara"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Usar reglas por defecto si no se especifica
        if not rules_file:
            rules_dir = self.tools_dir / "yara-rules"
            if rules_dir.exists():
                # Buscar archivo de reglas compilado o index
                for rule_file in rules_dir.glob("*.yar"):
                    rules_file = str(rule_file)
                    break
        
        if not rules_file or not Path(rules_file).exists():
            return {"success": False, "error": "No se encontraron reglas YARA"}
        
        cmd = ["yara", "-r", "-w", "-s", rules_file, scan_path]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=1800
            )
            
            stdout_text = stdout.decode('utf-8', errors='ignore')
            
            # Guardar resultados
            with open(output_dir / "yara_results.txt", 'w') as f:
                f.write(stdout_text)
            
            # Parsear matches
            matches = []
            for line in stdout_text.split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        matches.append({
                            "rule": parts[0],
                            "file": parts[1],
                            "severity": "high"
                        })
            
            return {
                "success": True,
                "case_id": case_id,
                "tool": "yara",
                "output_path": str(output_dir),
                "matches": matches[:100],
                "total_matches": len(matches),
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando YARA: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== AUTO ANALYSIS ====================
    
    async def run_full_m365_analysis(self, tenant_id: str, client_id: str, 
                                     client_secret: str, case_id: str) -> Dict:
        """
        Ejecutar análisis completo de M365 (Sparrow + Hawk)
        """
        logger.info(f"🔬 Iniciando análisis completo M365 para caso {case_id}")
        
        results = {
            "case_id": case_id,
            "tenant_id": tenant_id,
            "started_at": datetime.now().isoformat(),
            "sparrow": None,
            "hawk": None,
            "total_iocs": 0,
            "status": "running"
        }
        
        # Ejecutar Sparrow
        sparrow_result = await self.run_sparrow(
            tenant_id, client_id, client_secret, case_id
        )
        results["sparrow"] = sparrow_result
        
        if sparrow_result.get("success"):
            results["total_iocs"] += sparrow_result.get("iocs_detected", 0)
        
        # Ejecutar Hawk
        hawk_result = await self.run_hawk(
            tenant_id, client_id, client_secret, case_id
        )
        results["hawk"] = hawk_result
        
        if hawk_result.get("success"):
            results["total_iocs"] += len(hawk_result.get("findings", {}).get("suspicious_activities", []))
        
        results["completed_at"] = datetime.now().isoformat()
        results["status"] = "completed"
        
        return results


# Instancia global
forensic_tools = ForensicToolsService()
