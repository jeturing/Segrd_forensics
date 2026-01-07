"""
Sherlock Service - OSINT para búsqueda de perfiles en redes sociales
Usa Sherlock Project para rastrear usernames a través de múltiples plataformas
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List
import logging
from api.config import settings

logger = logging.getLogger(__name__)

SHERLOCK_PATH = Path("/opt/forensics-tools/sherlock")
EVIDENCE_DIR = settings.EVIDENCE_DIR


async def run_sherlock_search(
    username: str,
    case_id: str,
    timeout: int = 300
) -> Dict:
    """
    Ejecuta Sherlock para buscar un username en múltiples redes sociales
    
    Args:
        username: Username a buscar
        case_id: ID del caso forense
        timeout: Timeout en segundos (default: 5 minutos)
    
    Returns:
        Dict con resultados de la búsqueda
    """
    try:
        logger.info(f"🔍 Buscando username '{username}' con Sherlock")
        
        # Validar instalación
        sherlock_bin = SHERLOCK_PATH / "sherlock_project" / "sherlock.py"
        if not sherlock_bin.exists():
            raise Exception(f"Sherlock no encontrado en {sherlock_bin}")
        
        # Crear directorio de evidencia
        evidence_path = EVIDENCE_DIR / case_id / "sherlock"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        output_file = evidence_path / f"{username}_results.json"
        
        # Construir comando (usar python3 -m)
        cmd = [
            "python3",
            "-m",
            "sherlock_project",
            username,
            "--timeout", "10",
            "--print-found",
            "--folderoutput", str(evidence_path)
        ]
        
        logger.info(f"🛠️ Ejecutando: sherlock {username}...")
        
        # Ejecutar Sherlock
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(SHERLOCK_PATH),
            env={**os.environ, "PYTHONPATH": str(SHERLOCK_PATH)}
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            raise Exception(f"Sherlock timeout después de {timeout}s")
        
        # Parsear resultados
        results = parse_sherlock_results(
            username,
            output_file,
            stdout.decode(),
            stderr.decode()
        )
        
        logger.info(f"✅ Sherlock completado: {results['found_count']} perfiles encontrados")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando Sherlock: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "username": username
        }


async def run_sherlock_bulk(
    usernames: List[str],
    case_id: str,
    timeout: int = 600
) -> Dict:
    """
    Ejecuta Sherlock para múltiples usernames en paralelo
    
    Args:
        usernames: Lista de usernames a buscar
        case_id: ID del caso forense
        timeout: Timeout por username en segundos
    
    Returns:
        Dict con resultados agregados
    """
    try:
        logger.info(f"🔍 Búsqueda masiva de {len(usernames)} usernames con Sherlock")
        
        # Ejecutar búsquedas en paralelo (max 3 concurrentes)
        tasks = []
        for username in usernames[:10]:  # Limitar a 10 para evitar sobrecarga
            task = run_sherlock_search(username, case_id, timeout)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Agregar resultados
        all_profiles = []
        total_found = 0
        errors = []
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"{usernames[idx]}: {str(result)}")
            elif result.get("status") == "failed":
                errors.append(f"{result['username']}: {result['error']}")
            else:
                all_profiles.extend(result.get("profiles", []))
                total_found += result.get("found_count", 0)
        
        return {
            "status": "completed",
            "usernames_searched": len(usernames),
            "total_profiles_found": total_found,
            "profiles": all_profiles,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"❌ Error en búsqueda masiva: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def parse_sherlock_results(
    username: str,
    json_file: Path,
    stdout: str,
    stderr: str
) -> Dict:
    """
    Parsea resultados de Sherlock
    
    Sherlock genera un archivo JSON con el formato:
    {
        "Twitter": {
            "url_main": "https://twitter.com/",
            "url_user": "https://twitter.com/username",
            "exists": "yes",
            "http_status": 200,
            "response_time_s": 0.5
        },
        ...
    }
    """
    results = {
        "status": "completed",
        "username": username,
        "found_count": 0,
        "profiles": [],
        "raw_output": stdout
    }
    
    try:
        # Sherlock crea un archivo por username en el folderoutput
        txt_file = json_file.parent / f"{username}.txt"
        
        # Parsear archivo de texto si existe
        if txt_file.exists():
            logger.info(f"Parseando resultados desde {txt_file}")
            with open(txt_file, 'r') as f:
                content = f.read()
            
            for line in content.split('\n'):
                if line.strip() and 'http' in line:
                    # Formato típico: "[+] Platform: https://platform.com/username"
                    if '[+]' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            platform = parts[0].replace('[+]', '').strip()
                            url = parts[1].strip()
                            results["found_count"] += 1
                            results["profiles"].append({
                                "platform": platform,
                                "url": url,
                                "risk_level": categorize_platform_risk(platform)
                            })
        
        # Parsear stdout como fallback
        else:
            logger.warning("Archivo de resultados no encontrado, parseando stdout")
            for line in stdout.split('\n'):
                if '[+]' in line and 'http' in line:
                    # Extraer nombre de plataforma y URL
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        platform = parts[0].replace('[+]', '').strip()
                        url = parts[1].strip()
                        if url.startswith('http'):
                            results["found_count"] += 1
                            results["profiles"].append({
                                "platform": platform,
                                "url": url,
                                "risk_level": categorize_platform_risk(platform)
                            })
        
        # Ordenar por nivel de riesgo
        risk_order = {"high": 0, "medium": 1, "low": 2}
        results["profiles"].sort(
            key=lambda x: risk_order.get(x.get("risk_level", "medium"), 1)
        )
        
    except Exception as e:
        logger.error(f"Error parseando resultados de Sherlock: {e}")
        results["parse_error"] = str(e)
    
    return results


def categorize_platform_risk(platform: str) -> str:
    """
    Categoriza el nivel de riesgo de una plataforma social
    
    Plataformas de alto riesgo:
    - Foros de hacking, darkweb, marketplaces
    - Sitios de leaks, pastebins
    
    Plataformas de riesgo medio:
    - Redes sociales anónimas
    - Foros técnicos
    
    Plataformas de bajo riesgo:
    - Redes sociales convencionales
    - Plataformas profesionales
    """
    platform_lower = platform.lower()
    
    high_risk = [
        'pastebin', 'ghostbin', 'hastebin',
        'hackforums', 'cracked', 'nulled',
        '4chan', '8chan', 'kiwifarms',
        'telegram', 'discord' # Pueden ser usados para C2
    ]
    
    low_risk = [
        'linkedin', 'facebook', 'instagram',
        'twitter', 'youtube', 'github',
        'stackoverflow', 'reddit'
    ]
    
    for keyword in high_risk:
        if keyword in platform_lower:
            return "high"
    
    for keyword in low_risk:
        if keyword in platform_lower:
            return "low"
    
    return "medium"


async def extract_usernames_from_email(email: str) -> List[str]:
    """
    Extrae posibles usernames de un email
    
    Ejemplos:
    - john.doe@empresa.com -> ["john.doe", "johndoe", "jdoe"]
    - admin@empresa.com -> ["admin"]
    """
    usernames = []
    
    if '@' not in email:
        return [email]
    
    local_part = email.split('@')[0]
    usernames.append(local_part)
    
    # Variaciones comunes
    if '.' in local_part:
        # Sin punto: john.doe -> johndoe
        usernames.append(local_part.replace('.', ''))
        
        # Primera inicial + apellido: john.doe -> jdoe
        parts = local_part.split('.')
        if len(parts) == 2:
            usernames.append(parts[0][0] + parts[1])
    
    if '_' in local_part:
        usernames.append(local_part.replace('_', ''))
    
    return list(set(usernames))


async def sherlock_intelligence_gathering(
    target: str,
    case_id: str,
    target_type: str = "username"
) -> Dict:
    """
    Inteligencia OSINT completa usando Sherlock
    
    Args:
        target: Username o email a investigar
        case_id: ID del caso
        target_type: "username" o "email"
    
    Returns:
        Dict con inteligencia recopilada
    """
    try:
        if target_type == "email":
            usernames = await extract_usernames_from_email(target)
            logger.info(f"📧 Email {target} -> Usernames: {usernames}")
            results = await run_sherlock_bulk(usernames, case_id)
            results["original_email"] = target
            results["derived_usernames"] = usernames
        else:
            results = await run_sherlock_search(target, case_id)
        
        # Agregar análisis de inteligencia
        if results.get("profiles"):
            results["intelligence"] = {
                "high_risk_profiles": [
                    p for p in results["profiles"] 
                    if p.get("risk_level") == "high"
                ],
                "total_digital_footprint": len(results["profiles"]),
                "platforms_of_interest": [
                    p["platform"] for p in results["profiles"]
                ]
            }
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en intelligence gathering: {e}")
        return {"status": "failed", "error": str(e)}
