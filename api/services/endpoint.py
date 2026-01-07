"""
Servicios para análisis forense de endpoints
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import logging

from api.config import settings

logger = logging.getLogger(__name__)

async def run_loki_scan(
    hostname: str,
    tailscale_ip: Optional[str] = None,
    target_paths: Optional[List[str]] = None
) -> Dict:
    """
    Ejecuta Loki Scanner para detectar IOCs
    
    Loki detecta:
    - Archivos maliciosos conocidos
    - Hashes de malware
    - Nombres de archivos sospechosos
    - Yara rules matches
    """
    try:
        loki_path = settings.TOOLS_DIR / "Loki" / "loki.py"
        
        # Validar que Loki esté instalado
        if not loki_path.exists():
            raise Exception(f"Loki no encontrado en {loki_path}. Ejecuta scripts/install.sh")
        
        logger.info(f"🔍 Ejecutando Loki en {hostname}")
        
        # Rutas por defecto si no se especifican
        if not target_paths:
            target_paths = ["/tmp", "/home", "/var/www"] if not tailscale_ip else []
        
        # Construir comando Loki
        cmd = [
            "python3",
            str(loki_path),
            "--noprocscan",  # No escanear procesos (requiere root)
            "--dontwait",    # No esperar input
            "--intense",     # Escaneo intensivo
            "--csv"          # Output CSV
        ]
        
        # Agregar rutas específicas
        if target_paths:
            for path in target_paths:
                cmd.extend(["--path", path])
        
        # Si es remoto, usar SSH via Tailscale
        if tailscale_ip:
            logger.info(f"🌐 Conectando vía Tailscale a {tailscale_ip}")
            # Ejecutar Loki remotamente
            cmd = [
                "ssh",
                f"root@{tailscale_ip}",
                "python3", "/opt/loki/loki.py", "--noprocscan", "--dontwait", "--csv"
            ] + ([item for path in target_paths for item in ["--path", path]] if target_paths else [])
        
        logger.info(f"🛠️ Comando Loki: {' '.join(cmd[:5])}...")
        
        # Ejecutar Loki con timeout de 10 minutos
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minutos
            )
        except asyncio.TimeoutError:
            process.kill()
            raise Exception("Loki timeout después de 10 minutos")
        
        if process.returncode != 0:
            logger.warning(f"⚠️ Loki terminó con código {process.returncode}: {stderr.decode()[:500]}")
        
        # Parsear resultados
        results = parse_loki_output(stdout.decode(), stderr.decode())
        
        logger.info(f"✅ Loki completado: {results.get('ioc_count', 0)} IOCs detectados")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando Loki: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}

def parse_loki_output(stdout: str, stderr: str) -> Dict:
    """Parsea salida de Loki"""
    results = {
        "ioc_count": 0,
        "suspicious_files": [],
        "malware_detected": [],
        "alerts": [],
        "warnings": []
    }
    
    try:
        lines = stdout.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detectar alertas de Loki (formato: [ALERT] ...)
            if '[ALERT]' in line:
                results['ioc_count'] += 1
                results['alerts'].append(line)
                
                # Extraer nombre de archivo si está presente
                if 'FILE:' in line:
                    file_match = line.split('FILE:')[1].split()[0] if 'FILE:' in line else 'Unknown'
                    results['malware_detected'].append({
                        'file': file_match,
                        'alert': line
                    })
            
            # Detectar advertencias
            elif '[WARNING]' in line:
                results['warnings'].append(line)
                results['suspicious_files'].append(line)
            
            # Detectar matches de YARA
            elif 'YARA MATCH' in line.upper():
                results['ioc_count'] += 1
                results['malware_detected'].append({
                    'file': 'Unknown',
                    'alert': line
                })
        
        # Parsear CSV si fue generado
        csv_pattern = r'loki.*\.csv'
        import re
        csv_matches = re.findall(csv_pattern, stderr + stdout)
        if csv_matches:
            logger.info(f"📊 CSV generado: {csv_matches[0]}")
    
    except Exception as e:
        logger.error(f"❌ Error parseando Loki output: {e}")
    
    return results

async def run_yara_scan(
    hostname: str,
    tailscale_ip: Optional[str] = None,
    target_paths: Optional[List[str]] = None,
    rules: Optional[List[str]] = None
) -> Dict:
    """
    Ejecuta escaneo YARA para detectar malware
    """
    try:
        rules_path = settings.TOOLS_DIR / "yara-rules"
        
        # Validar que YARA esté instalado
        yara_check = await asyncio.create_subprocess_exec(
            "which", "yara",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await yara_check.communicate()
        if yara_check.returncode != 0:
            raise Exception("YARA no está instalado. Instala: apt install yara")
        
        if not rules_path.exists():
            raise Exception(f"YARA rules no encontradas en {rules_path}. Ejecuta scripts/install.sh")
        
        logger.info(f"🧬 Ejecutando YARA en {hostname}")
        
        # Rutas por defecto
        if not target_paths:
            target_paths = ["/tmp", "/home", "/var/www"]
        
        # Reglas por defecto (infostealers, malware general)
        if not rules:
            rules = [
                str(rules_path / "community" / "malware" / "MALW_*.yar"),
                str(rules_path / "gen_malware_set.yar")
            ]
        
        all_matches = []
        scanned_count = 0
        
        # Escanear cada ruta con YARA
        for target in target_paths:
            for rule_file in rules:
                # Expandir wildcards
                import glob
                rule_files = glob.glob(rule_file)
                
                for rf in rule_files:
                    if not Path(rf).exists():
                        continue
                    
                    logger.info(f"🔍 Escaneando {target} con {Path(rf).name}")
                    
                    cmd = [
                        "yara",
                        "-r",  # Recursivo
                        "-w",  # No warnings
                        "-s",  # Mostrar strings matched
                        rf,    # Archivo de reglas
                        target # Directorio a escanear
                    ]
                    
                    # Si es remoto, usar SSH
                    if tailscale_ip:
                        cmd = ["ssh", f"root@{tailscale_ip}"] + cmd
                    
                    try:
                        process = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(),
                            timeout=300  # 5 minutos por regla
                        )
                        
                        # Parsear matches
                        matches = parse_yara_output(stdout.decode())
                        all_matches.extend(matches)
                        scanned_count += 1
                    
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ YARA timeout en {target} con {Path(rf).name}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error escaneando {target}: {e}")
                        continue
        
        logger.info(f"✅ YARA completado: {len(all_matches)} matches en {scanned_count} escaneos")
        
        return {
            "status": "completed",
            "matches": all_matches,
            "scanned_files": scanned_count,
            "rules_used": len(rules)
        }
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando YARA: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}

def parse_yara_output(output: str) -> List[Dict]:
    """Parsea salida de YARA"""
    matches = []
    
    try:
        lines = output.split('\n')
        current_match = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Formato: RuleName FileName
            if not line.startswith('0x') and ' ' in line:
                parts = line.split()
                if len(parts) >= 2:
                    if current_match:
                        matches.append(current_match)
                    
                    current_match = {
                        'rule': parts[0],
                        'file': ' '.join(parts[1:]),
                        'strings': []
                    }
            
            # Strings matched (formato: 0xOFFSET:$string: "content")
            elif line.startswith('0x') and current_match:
                current_match['strings'].append(line)
        
        # Agregar último match
        if current_match:
            matches.append(current_match)
    
    except Exception as e:
        logger.error(f"❌ Error parseando YARA output: {e}")
    
    return matches

async def collect_osquery_artifacts(
    hostname: str,
    tailscale_ip: Optional[str] = None
) -> Dict:
    """
    Recolecta artefactos del sistema usando OSQuery
    
    Recolecta:
    - Procesos en ejecución
    - Conexiones de red
    - Usuarios y grupos
    - Programas instalados
    - Tareas programadas
    - Claves de registro (Windows)
    """
    try:
        # Validar que osqueryi esté instalado
        osquery_check = await asyncio.create_subprocess_exec(
            "which", "osqueryi",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await osquery_check.communicate()
        if osquery_check.returncode != 0:
            raise Exception("OSQuery no está instalado. Instala: apt install osquery")
        
        logger.info(f"📦 Recolectando artefactos con OSQuery de {hostname}")
        
        # Queries forenses importantes
        queries = {
            "processes": "SELECT pid, name, path, cmdline, uid, parent FROM processes WHERE name NOT LIKE '%osquery%';",
            "connections": "SELECT pid, fd, local_address, local_port, remote_address, remote_port, state FROM process_open_sockets WHERE remote_port != 0;",
            "users": "SELECT uid, username, description, directory, shell FROM users;",
            "listening_ports": "SELECT pid, port, address, protocol FROM listening_ports;",
            "startup_items": "SELECT name, path, source, status FROM startup_items;",
            "cron_jobs": "SELECT command, path, minute, hour, day_of_month FROM crontab;",
            "ssh_keys": "SELECT uid, path, encrypted FROM user_ssh_keys;",
            "installed_packages": "SELECT name, version, source FROM deb_packages LIMIT 50;"
        }
        
        results = {}
        suspicious_processes = []
        network_connections = []
        
        for query_name, query_sql in queries.items():
            try:
                logger.info(f"🔍 Ejecutando query: {query_name}")
                
                cmd = [
                    "osqueryi",
                    "--json",
                    query_sql
                ]
                
                # Si es remoto, usar SSH
                if tailscale_ip:
                    cmd = ["ssh", f"root@{tailscale_ip}"] + cmd
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30  # 30 segundos por query
                )
                
                if process.returncode == 0:
                    import json
                    data = json.loads(stdout.decode())
                    results[query_name] = data
                    
                    # Analizar procesos sospechosos
                    if query_name == "processes":
                        for proc in data:
                            # Detectar procesos con nombres sospechosos
                            suspicious_names = ['nc', 'ncat', 'socat', 'wget', 'curl', 'python -c', 'bash -i', 'powershell', 'meterpreter']
                            if any(sus in proc.get('name', '').lower() or sus in proc.get('cmdline', '').lower() for sus in suspicious_names):
                                suspicious_processes.append(proc)
                    
                    # Analizar conexiones sospechosas
                    if query_name == "connections":
                        for conn in data:
                            # Puertos sospechosos
                            suspicious_ports = [4444, 5555, 6666, 7777, 8888, 31337, 12345]
                            if conn.get('remote_port') in suspicious_ports:
                                network_connections.append(conn)
                else:
                    logger.warning(f"⚠️ Query {query_name} falló: {stderr.decode()[:200]}")
            
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Query {query_name} timeout")
                continue
            except Exception as e:
                logger.error(f"❌ Error en query {query_name}: {e}")
                continue
        
        logger.info(f"✅ OSQuery completado: {len(results)} queries exitosas, "
                   f"{len(suspicious_processes)} procesos sospechosos")
        
        return {
            "status": "completed",
            "raw_data": results,
            "suspicious_processes": suspicious_processes,
            "network_connections": network_connections,
            "installed_software": results.get('installed_packages', [])[:20]
        }
        
    except Exception as e:
        logger.error(f"❌ Error en OSQuery: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}

async def analyze_memory_dump(dump_path: str) -> Dict:
    """
    Analiza dump de memoria con Volatility 3
    
    Plugins ejecutados:
    - windows.info / linux.info
    - windows.pslist / linux.pslist
    - windows.netscan / linux.netscan
    - windows.malfind (código inyectado)
    - windows.cmdline
    """
    try:
        # Validar que vol.py esté instalado
        vol_check = await asyncio.create_subprocess_exec(
            "which", "vol.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await vol_check.communicate()
        
        # Alternativamente, buscar vol3 o volatility3
        if vol_check.returncode != 0:
            vol_check = await asyncio.create_subprocess_exec(
                "which", "vol3",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await vol_check.communicate()
            vol_cmd = "vol3" if vol_check.returncode == 0 else "vol.py"
        else:
            vol_cmd = "vol.py"
        
        if vol_check.returncode != 0:
            raise Exception("Volatility 3 no está instalado. Instala: apt install volatility3")
        
        logger.info(f"🧠 Analizando dump de memoria: {dump_path}")
        
        # Validar que el dump existe
        if not Path(dump_path).exists():
            raise Exception(f"Dump de memoria no encontrado: {dump_path}")
        
        results = {
            "status": "running",
            "os_info": {},
            "processes": [],
            "network": [],
            "injected_code": [],
            "command_lines": [],
            "dlls": []
        }
        
        # 1. Detectar sistema operativo
        logger.info("🔍 Detectando sistema operativo...")
        
        # Intentar con windows.info primero
        os_type = await detect_os_type(vol_cmd, dump_path)
        results["os_info"]["type"] = os_type
        
        # 2. Listar procesos
        logger.info("🔍 Listando procesos...")
        plugin = "windows.pslist" if os_type == "windows" else "linux.pslist"
        processes = await run_volatility_plugin(vol_cmd, dump_path, plugin)
        results["processes"] = processes[:50]  # Limitar a 50
        
        # 3. Conexiones de red
        if os_type == "windows":
            logger.info("🌐 Analizando conexiones de red...")
            network = await run_volatility_plugin(vol_cmd, dump_path, "windows.netscan")
            results["network"] = network[:30]
        
        # 4. Código inyectado (solo Windows)
        if os_type == "windows":
            logger.info("💉 Buscando código inyectado...")
            malfind = await run_volatility_plugin(vol_cmd, dump_path, "windows.malfind")
            results["injected_code"] = malfind[:20]
        
        # 5. Líneas de comando
        if os_type == "windows":
            logger.info("📝 Extrayendo líneas de comando...")
            cmdline = await run_volatility_plugin(vol_cmd, dump_path, "windows.cmdline")
            results["command_lines"] = cmdline[:30]
        
        results["status"] = "completed"
        
        logger.info(f"✅ Análisis de memoria completado: {len(results['processes'])} procesos, "
                   f"{len(results['network'])} conexiones, {len(results['injected_code'])} inyecciones")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error analizando memoria: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}

async def detect_os_type(vol_cmd: str, dump_path: str) -> str:
    """Detecta el tipo de OS del dump"""
    try:
        # Intentar windows.info
        cmd = [vol_cmd, "-f", dump_path, "windows.info"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        
        if process.returncode == 0 and b"windows" in stdout.lower():
            return "windows"
        
        # Intentar linux.info
        cmd = [vol_cmd, "-f", dump_path, "linux.info"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        
        if process.returncode == 0:
            return "linux"
        
        return "unknown"
    
    except Exception as e:
        logger.error(f"❌ Error detectando OS: {e}")
        return "unknown"

async def run_volatility_plugin(vol_cmd: str, dump_path: str, plugin: str) -> List[Dict]:
    """Ejecuta un plugin de Volatility 3"""
    try:
        cmd = [vol_cmd, "-f", dump_path, plugin]
        
        logger.info(f"🔧 Ejecutando plugin: {plugin}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=300  # 5 minutos por plugin
        )
        
        if process.returncode != 0:
            logger.warning(f"⚠️ Plugin {plugin} falló: {stderr.decode()[:200]}")
            return []
        
        # Parsear salida (Volatility usa formato tabular)
        return parse_volatility_output(stdout.decode())
    
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ Plugin {plugin} timeout")
        return []
    except Exception as e:
        logger.error(f"❌ Error ejecutando plugin {plugin}: {e}")
        return []

def parse_volatility_output(output: str) -> List[Dict]:
    """Parsea salida tabular de Volatility 3"""
    results = []
    
    try:
        lines = output.split('\n')
        headers = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # La primera línea no vacía suele ser el header
            if not headers and '\t' in line:
                headers = [h.strip() for h in line.split('\t')]
                continue
            
            # Parsear filas de datos
            if headers and '\t' in line:
                values = [v.strip() for v in line.split('\t')]
                if len(values) == len(headers):
                    row = dict(zip(headers, values))
                    results.append(row)
    
    except Exception as e:
        logger.error(f"❌ Error parseando output de Volatility: {e}")
    
    return results
