"""
Servicio para integración con herramientas M365
Sparrow, Hawk y O365 Extractor - EJECUCIÓN REAL

Este módulo:
- Instala herramientas automáticamente si no están disponibles
- Ejecuta las herramientas reales contra M365
- Guarda resultados en base de datos
- Genera reportes consumibles
"""

import asyncio
import json
import os
import csv
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

from api.config import settings
from api.database import get_db_context
from api.models.tool_report import M365Report

logger = logging.getLogger(__name__)

# Rutas de configuración
TOOLS_DIR = settings.TOOLS_DIR
SPARROW_DIR = TOOLS_DIR / "Sparrow"
HAWK_DIR = TOOLS_DIR / "hawk"
O365_EXTRACTOR_DIR = TOOLS_DIR / "o365-extractor"
EVIDENCE_DIR = settings.EVIDENCE_DIR

# URLs de herramientas
TOOL_REPOS = {
    "Sparrow": "https://github.com/cisagov/Sparrow.git",
    "hawk": "https://github.com/T0pCyber/hawk.git",  # Repositorio oficial de Hawk
    "o365-extractor": "https://github.com/SecurityRiskAdvisors/sra-o365-extractor.git",
    "Loki": "https://github.com/Neo23x0/Loki.git",
    "yara-rules": "https://github.com/Yara-Rules/rules.git",
    "ROADtools": "https://github.com/dirkjanm/ROADtools.git",
    "Monkey365": "https://github.com/silverhack/monkey365.git",
    "AADInternals": "https://github.com/Gerenios/AADInternals.git",
}

# ============================================================================
# INSTALACIÓN AUTOMÁTICA DE HERRAMIENTAS
# ============================================================================

async def ensure_tool_installed(tool_name: str) -> bool:
    """
    Asegura que una herramienta esté instalada.
    Si no existe, la descarga automáticamente.
    """
    tool_path = TOOLS_DIR / tool_name
    
    if tool_path.exists():
        logger.info(f"✅ {tool_name} ya instalado en {tool_path}")
        return True
    
    if tool_name not in TOOL_REPOS:
        logger.error(f"❌ No hay repositorio configurado para {tool_name}")
        return False
    
    repo_url = TOOL_REPOS[tool_name]
    logger.info(f"📦 Instalando {tool_name} desde {repo_url}...")
    
    try:
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        
        process = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", repo_url, str(tool_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"✅ {tool_name} instalado correctamente")
            
            # Instalar dependencias Python si existen
            req_file = tool_path / "requirements.txt"
            if req_file.exists():
                logger.info(f"📦 Instalando dependencias de {tool_name}...")
                pip_proc = await asyncio.create_subprocess_exec(
                    "pip3", "install", "-q", "-r", str(req_file),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await pip_proc.communicate()
            
            return True
        else:
            logger.error(f"❌ Error instalando {tool_name}: {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error instalando {tool_name}: {e}")
        return False


async def ensure_powershell_module(module_name: str) -> bool:
    """Instala módulo de PowerShell si no está disponible"""
    try:
        # Verificar si el módulo existe
        check_cmd = f"Get-Module -ListAvailable -Name {module_name}"
        process = await asyncio.create_subprocess_exec(
            "pwsh", "-NoProfile", "-Command", check_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if module_name.lower() in stdout.decode().lower():
            logger.info(f"✅ Módulo PowerShell {module_name} ya instalado")
            return True
        
        # Instalar módulo
        logger.info(f"📦 Instalando módulo PowerShell {module_name}...")
        install_cmd = f"Install-Module -Name {module_name} -Force -AllowClobber -Scope CurrentUser"
        process = await asyncio.create_subprocess_exec(
            "pwsh", "-NoProfile", "-Command", install_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
        
    except Exception as e:
        logger.error(f"❌ Error con módulo {module_name}: {e}")
        return False


# ============================================================================
# GUARDAR RESULTADOS EN BASE DE DATOS (SQLAlchemy)
# ============================================================================

def save_tool_report(case_id: str, tool_name: str, results: Dict, tenant_id: str = None) -> str:
    """Guarda el reporte de una herramienta en la base de datos usando SQLAlchemy"""
    try:
        with get_db_context() as db:
            report = M365Report(
                case_id=case_id,
                tool_name=tool_name,
                tenant_id=tenant_id,
                status=results.get("status", "unknown"),
                results=results.get("data", results),
                raw_output=results.get("raw_output", ""),
                evidence_path=results.get("evidence_path", ""),
                output_files=results.get("output_files", []),
                findings_count=results.get("findings_count", 0),
                alerts_count=results.get("alerts_count", 0),
                warnings_count=results.get("warnings_count", 0),
                error_message=results.get("error", None),
                started_at=results.get("started_at"),
                completed_at=datetime.utcnow(),
                execution_time_seconds=results.get("execution_time_seconds"),
                parameters=results.get("parameters", {}),
                scope=results.get("scope", [])
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            
            logger.info(f"💾 Reporte guardado: {tool_name} -> ID {report.id}")
            return report.id
            
    except Exception as e:
        logger.error(f"❌ Error guardando reporte: {e}")
        return ""


def get_tool_reports(case_id: str, tool_name: Optional[str] = None) -> List[Dict]:
    """Obtiene reportes de herramientas desde la base de datos"""
    try:
        with get_db_context() as db:
            query = db.query(M365Report).filter(M365Report.case_id == case_id)
            
            if tool_name:
                query = query.filter(M365Report.tool_name == tool_name)
            
            reports = query.order_by(M365Report.created_at.desc()).all()
            
            return [report.to_dict() for report in reports]
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo reportes: {e}")
        return []


def get_report_by_id(report_id: str) -> Optional[Dict]:
    """Obtiene un reporte específico por ID"""
    try:
        with get_db_context() as db:
            report = db.query(M365Report).filter(M365Report.id == report_id).first()
            if report:
                return report.to_dict()
            return None
    except Exception as e:
        logger.error(f"❌ Error obteniendo reporte {report_id}: {e}")
        return None


def update_report_status(report_id: str, status: str, **kwargs) -> bool:
    """Actualiza el estado de un reporte"""
    try:
        with get_db_context() as db:
            report = db.query(M365Report).filter(M365Report.id == report_id).first()
            if report:
                report.status = status
                for key, value in kwargs.items():
                    if hasattr(report, key):
                        setattr(report, key, value)
                db.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"❌ Error actualizando reporte {report_id}: {e}")
        return False


# ============================================================================
# EJECUCIÓN DE SPARROW
# ============================================================================

async def run_sparrow_analysis(
    tenant_id: str,
    case_id: str,
    days_back: int = 90
) -> Dict:
    """
    Ejecuta Sparrow 365 para análisis de Azure AD
    
    Sparrow detecta:
    - Actividad sospechosa en Azure AD
    - Anomalías en roles administrativos
    - Registros de autenticación anómalos
    - Abuso de tokens OAuth
    """
    results = {
        "tool": "sparrow",
        "tenant_id": tenant_id,
        "case_id": case_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Asegurar que Sparrow esté instalado
        if not await ensure_tool_installed("Sparrow"):
            raise Exception("No se pudo instalar Sparrow")
        
        # Crear directorio de evidencia
        evidence_path = EVIDENCE_DIR / case_id / "sparrow"
        evidence_path.mkdir(parents=True, exist_ok=True)
        results["evidence_path"] = str(evidence_path)
        
        logger.info(f"🦅 Ejecutando Sparrow para tenant {tenant_id}")
        
        # Verificar PowerShell
        pwsh_check = await asyncio.create_subprocess_exec(
            "which", "pwsh",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await pwsh_check.communicate()
        if pwsh_check.returncode != 0:
            raise Exception("PowerShell (pwsh) no está instalado")
        
        # Instalar módulos necesarios para Sparrow
        await ensure_powershell_module("ExchangeOnlineManagement")
        await ensure_powershell_module("AzureAD")
        
        # Calcular fechas
        from datetime import timedelta
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        end_date = datetime.utcnow().strftime("%m/%d/%Y")
        
        # Construir comando Sparrow
        sparrow_script = SPARROW_DIR / "Sparrow.ps1"
        cmd = [
            "pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(sparrow_script),
            "-ExportDir", str(evidence_path),
            "-StartDate", start_date,
            "-EndDate", end_date
        ]
        
        logger.info(f"🔧 Comando: {' '.join(cmd)}")
        
        # Ejecutar Sparrow con timeout
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "FORENSICS_CASE_ID": case_id}
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=1800  # 30 minutos máximo
            )
        except asyncio.TimeoutError:
            process.kill()
            raise Exception("Sparrow timeout después de 30 minutos")
        
        results["stdout"] = stdout.decode()[:5000]
        results["stderr"] = stderr.decode()[:2000]
        results["return_code"] = process.returncode
        
        # Parsear resultados
        parsed = parse_sparrow_output(evidence_path)
        results.update(parsed)
        
        if process.returncode == 0:
            results["status"] = "completed"
            logger.info(f"✅ Sparrow completado para {case_id}")
        else:
            results["status"] = "completed_with_errors"
            logger.warning(f"⚠️ Sparrow terminó con código {process.returncode}")
        
        results["completed_at"] = datetime.utcnow().isoformat()
        
        # Guardar en base de datos
        save_tool_report(case_id, "sparrow", results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando Sparrow: {e}", exc_info=True)
        results["status"] = "failed"
        results["error"] = str(e)
        results["completed_at"] = datetime.utcnow().isoformat()
        
        # Guardar error en DB también
        save_tool_report(case_id, "sparrow", results)
        
        return results


def parse_sparrow_output(output_dir: Path) -> Dict:
    """Parsea la salida de Sparrow para extraer hallazgos"""
    findings = {
        "critical_findings": [],
        "abused_tokens": [],
        "suspicious_sign_ins": [],
        "elevated_permissions": [],
        "files_generated": []
    }
    
    try:
        # Listar archivos generados
        if output_dir.exists():
            for f in output_dir.glob("*"):
                findings["files_generated"].append({
                    "name": f.name,
                    "size": f.stat().st_size if f.is_file() else 0,
                    "type": f.suffix
                })
        
        # Parsear CSVs
        for csv_file in output_dir.glob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    filename = csv_file.name.lower()
                    
                    if "signin" in filename or "auth" in filename:
                        for row in rows:
                            if any(k in row for k in ['Status', 'RiskLevel', 'ResultType']):
                                risk = row.get('RiskLevel', row.get('Status', 'Unknown'))
                                if risk and risk.lower() in ['high', 'failed', 'error']:
                                    findings["suspicious_sign_ins"].append({
                                        "user": row.get('UserPrincipalName', row.get('User', 'Unknown')),
                                        "ip": row.get('IPAddress', row.get('IpAddress', 'Unknown')),
                                        "time": row.get('CreatedDateTime', row.get('Timestamp', '')),
                                        "risk": risk,
                                        "source": csv_file.name
                                    })
                    
                    elif "oauth" in filename or "app" in filename or "consent" in filename:
                        for row in rows:
                            findings["abused_tokens"].append({
                                "app": row.get('AppDisplayName', row.get('ApplicationName', 'Unknown')),
                                "user": row.get('UserPrincipalName', row.get('User', 'Unknown')),
                                "permissions": row.get('Permissions', row.get('Scopes', '')),
                                "source": csv_file.name
                            })
                    
                    elif "role" in filename or "admin" in filename:
                        for row in rows:
                            findings["elevated_permissions"].append({
                                "user": row.get('UserPrincipalName', row.get('Member', 'Unknown')),
                                "role": row.get('RoleName', row.get('Role', 'Unknown')),
                                "source": csv_file.name
                            })
                    
                    # Cualquier archivo con datos es un hallazgo
                    if len(rows) > 0:
                        findings["critical_findings"].append({
                            "source": csv_file.name,
                            "count": len(rows),
                            "type": "csv_data"
                        })
            except Exception as e:
                logger.error(f"Error parseando {csv_file}: {e}")
                continue
        
        # Parsear JSONs
        for json_file in output_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    findings["critical_findings"].append({
                        "source": json_file.name,
                        "count": len(data) if isinstance(data, list) else 1,
                        "type": "json_data"
                    })
            except Exception as e:
                logger.error(f"Error parseando {json_file}: {e}")
                continue
        
        logger.info(f"📊 Sparrow parser: {len(findings['critical_findings'])} archivos, "
                   f"{len(findings['suspicious_sign_ins'])} sign-ins sospechosos")
    
    except Exception as e:
        logger.error(f"❌ Error parseando salida de Sparrow: {e}")
    
    return findings


# ============================================================================
# EJECUCIÓN DE HAWK
# ============================================================================

async def run_hawk_analysis(
    tenant_id: str,
    case_id: str,
    target_users: Optional[List[str]] = None,
    days_back: int = 90
) -> Dict:
    """
    Ejecuta Hawk para análisis completo de M365
    
    Hawk analiza:
    - Audit logs completos
    - Reglas de reenvío de correo
    - Aplicaciones OAuth
    - Estado de MFA
    """
    results = {
        "tool": "hawk",
        "tenant_id": tenant_id,
        "case_id": case_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Crear directorio de evidencia
        evidence_path = EVIDENCE_DIR / case_id / "hawk"
        evidence_path.mkdir(parents=True, exist_ok=True)
        results["evidence_path"] = str(evidence_path)
        
        logger.info(f"🦅 Ejecutando Hawk para tenant {tenant_id}")
        
        # Hawk se instala como módulo de PowerShell
        if not await ensure_powershell_module("Hawk"):
            # Intentar instalar desde repositorio
            await ensure_tool_installed("hawk")
        
        # Instalar módulos dependientes
        await ensure_powershell_module("ExchangeOnlineManagement")
        
        # Construir script de PowerShell para Hawk
        ps_script = f"""
        $ErrorActionPreference = 'Continue'
        
        # Importar Hawk
        try {{
            Import-Module Hawk -Force -ErrorAction Stop
        }} catch {{
            Write-Error "No se pudo importar Hawk: $_"
            exit 1
        }}
        
        # Configurar output
        $env:HawkLogPath = '{evidence_path}'
        
        # Ejecutar investigación de tenant
        try {{
            Start-HawkTenantInvestigation -FilePath '{evidence_path}'
        }} catch {{
            Write-Warning "Error en tenant investigation: $_"
        }}
        """
        
        # Agregar investigación de usuarios si se especificaron
        if target_users:
            for user in target_users[:5]:  # Máximo 5 usuarios
                ps_script += f"""
        try {{
            Start-HawkUserInvestigation -UserPrincipalName '{user}' -FilePath '{evidence_path}'
        }} catch {{
            Write-Warning "Error investigando {user}: $_"
        }}
        """
        
        # Ejecutar PowerShell
        cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        
        logger.info("🔧 Ejecutando Hawk...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=3600  # 1 hora máximo
            )
        except asyncio.TimeoutError:
            process.kill()
            raise Exception("Hawk timeout después de 1 hora")
        
        results["stdout"] = stdout.decode()[:5000]
        results["stderr"] = stderr.decode()[:2000]
        results["return_code"] = process.returncode
        
        # Parsear resultados
        parsed = parse_hawk_output(evidence_path)
        results.update(parsed)
        
        results["status"] = "completed" if process.returncode == 0 else "completed_with_errors"
        results["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"✅ Hawk completado para {case_id}")
        
        # Guardar en base de datos
        save_tool_report(case_id, "hawk", results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando Hawk: {e}", exc_info=True)
        results["status"] = "failed"
        results["error"] = str(e)
        results["completed_at"] = datetime.utcnow().isoformat()
        
        save_tool_report(case_id, "hawk", results)
        return results


def parse_hawk_output(output_dir: Path) -> Dict:
    """Parsea la salida de Hawk"""
    findings = {
        "suspicious_accounts": [],
        "forwarding_rules": [],
        "oauth_apps": [],
        "mfa_status": {},
        "mailbox_access": [],
        "files_generated": []
    }
    
    try:
        if not output_dir.exists():
            return findings
        
        # Listar todos los archivos generados
        for f in output_dir.rglob("*"):
            if f.is_file():
                findings["files_generated"].append({
                    "name": f.name,
                    "path": str(f.relative_to(output_dir)),
                    "size": f.stat().st_size
                })
        
        # Parsear CSVs de Hawk
        for csv_file in output_dir.rglob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    filename = csv_file.name.lower()
                    
                    if "forward" in filename or "rule" in filename:
                        for row in rows:
                            findings["forwarding_rules"].append({
                                "mailbox": row.get('Mailbox', row.get('User', 'Unknown')),
                                "rule_name": row.get('RuleName', row.get('Name', '')),
                                "forward_to": row.get('ForwardTo', row.get('Recipients', '')),
                                "source": csv_file.name
                            })
                    
                    elif "oauth" in filename or "consent" in filename:
                        for row in rows:
                            findings["oauth_apps"].append({
                                "name": row.get('DisplayName', row.get('AppName', 'Unknown')),
                                "permissions": row.get('Permissions', ''),
                                "source": csv_file.name
                            })
                    
                    elif "mfa" in filename or "auth" in filename:
                        findings["mfa_status"]["file"] = csv_file.name
                        findings["mfa_status"]["count"] = len(rows)
                    
            except Exception as e:
                logger.error(f"Error parseando {csv_file}: {e}")
        
        logger.info(f"📊 Hawk parser: {len(findings['forwarding_rules'])} reglas, "
                   f"{len(findings['oauth_apps'])} apps OAuth")
    
    except Exception as e:
        logger.error(f"❌ Error parseando salida de Hawk: {e}")
    
    return findings


# ============================================================================
# EJECUCIÓN DE O365 EXTRACTOR
# ============================================================================

async def run_o365_extractor(
    tenant_id: str,
    case_id: str,
    days_back: int = 90,
    target_users: Optional[List[str]] = None
) -> Dict:
    """
    Ejecuta O365 Extractor para obtener Unified Audit Logs
    """
    results = {
        "tool": "o365-extractor",
        "tenant_id": tenant_id,
        "case_id": case_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Asegurar instalación
        if not await ensure_tool_installed("o365-extractor"):
            raise Exception("No se pudo instalar O365 Extractor")
        
        evidence_path = EVIDENCE_DIR / case_id / "o365"
        evidence_path.mkdir(parents=True, exist_ok=True)
        results["evidence_path"] = str(evidence_path)
        
        logger.info(f"📦 Ejecutando O365 Extractor para tenant {tenant_id}")
        
        # Buscar script principal
        extractor_script = O365_EXTRACTOR_DIR / "o365_extractor.py"
        if not extractor_script.exists():
            extractor_script = O365_EXTRACTOR_DIR / "extractor.py"
        
        if not extractor_script.exists():
            # Listar archivos disponibles
            available = list(O365_EXTRACTOR_DIR.glob("*.py"))
            raise Exception(f"Script de O365 no encontrado. Disponibles: {available}")
        
        # Ejecutar
        cmd = [
            "python3", str(extractor_script),
            "--output", str(evidence_path),
            "--days", str(days_back)
        ]
        
        if target_users:
            cmd.extend(["--users", ",".join(target_users)])
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(O365_EXTRACTOR_DIR)
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=1800
        )
        
        results["stdout"] = stdout.decode()[:5000]
        results["stderr"] = stderr.decode()[:2000]
        results["return_code"] = process.returncode
        
        # Parsear salida
        parsed = parse_o365_output(evidence_path)
        results.update(parsed)
        
        results["status"] = "completed" if process.returncode == 0 else "completed_with_errors"
        results["completed_at"] = datetime.utcnow().isoformat()
        
        save_tool_report(case_id, "o365-extractor", results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando O365 Extractor: {e}", exc_info=True)
        results["status"] = "failed"
        results["error"] = str(e)
        save_tool_report(case_id, "o365-extractor", results)
        return results


def parse_o365_output(output_dir: Path) -> Dict:
    """Parsea salida de O365 Extractor"""
    findings = {
        "audit_logs": {"total": 0, "suspicious": 0},
        "activities": [],
        "files_generated": []
    }
    
    try:
        if not output_dir.exists():
            return findings
        
        for f in output_dir.glob("*"):
            if f.is_file():
                findings["files_generated"].append({
                    "name": f.name,
                    "size": f.stat().st_size
                })
        
        # Contar registros en CSVs
        for csv_file in output_dir.glob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    rows = list(csv.DictReader(f))
                    findings["audit_logs"]["total"] += len(rows)
                    
                    # Primeras actividades como muestra
                    for row in rows[:10]:
                        findings["activities"].append({
                            "operation": row.get('Operation', row.get('Activity', '')),
                            "user": row.get('UserId', row.get('User', '')),
                            "time": row.get('CreationTime', row.get('Timestamp', '')),
                            "source": csv_file.name
                        })
            except Exception:
                continue
        
    except Exception as e:
        logger.error(f"Error parseando O365: {e}")
    
    return findings


# ============================================================================
# API PARA CONSULTAR REPORTES
# ============================================================================

async def get_case_reports(case_id: str) -> Dict:
    """Obtiene todos los reportes de un caso"""
    reports = await get_tool_reports(case_id)
    
    summary = {
        "case_id": case_id,
        "total_reports": len(reports),
        "tools_executed": list(set(r["tool_name"] for r in reports)),
        "latest_run": reports[0]["created_at"] if reports else None,
        "reports": reports
    }
    
    # Estadísticas agregadas
    all_findings = []
    for r in reports:
        results = r.get("results", {})
        all_findings.extend(results.get("critical_findings", []))
        all_findings.extend(results.get("suspicious_sign_ins", []))
        all_findings.extend(results.get("forwarding_rules", []))
    
    summary["total_findings"] = len(all_findings)
    
    return summary


async def get_report_by_id(report_id: int) -> Optional[Dict]:
    """Obtiene un reporte específico por ID"""
    try:
        query = "SELECT * FROM tool_reports WHERE id = ?"
        result = await execute_query(query, (report_id,))
        row = result.fetchone() if hasattr(result, 'fetchone') else None
        
        if row:
            return {
                "id": row[0],
                "case_id": row[1],
                "tool_name": row[2],
                "status": row[3],
                "results": json.loads(row[4]) if row[4] else {},
                "evidence_path": row[5],
                "created_at": row[6]
            }
        return None
    except Exception as e:
        logger.error(f"Error obteniendo reporte {report_id}: {e}")
        return None
