# Instalación Local - Guía v4.2

## 🎯 Objetivo

Instalar todas las herramientas forenses **dentro de la carpeta `/tools` del proyecto** en lugar de usar `/opt/forensics-tools` del sistema. Esto evita:

✅ Errores de autenticación GitHub  
✅ Dependencias del sistema  
✅ Conflictos de permisos  
✅ Problemas en producción  

---

## 📋 Requisitos Previos

```bash
# Verificar que tienes:
python3 --version          # >= 3.9
git --version              # >= 2.30
curl --version             # >= 7.68
pip3 --version             # >= 21.0
```

---

## 🚀 Instalación

### Opción 1: Instalación Completa (Recomendado)

```bash
cd /home/hack/mcp-kali-forensics

# Ejecutar script principal
./install.sh

# O si necesitas permisos de root solo para deps del sistema:
sudo ./install.sh
```

**Duración**: 15-30 minutos (depende de conexión)

**Resultado**:
```
/home/hack/mcp-kali-forensics/
├── tools/                    # ← Todos los tools aquí
│   ├── Sparrow/
│   ├── hawk/
│   ├── o365-extractor/
│   ├── Loki/
│   ├── yara-rules/
│   ├── azurehound/
│   ├── ROADtools/
│   ├── Monkey365/
│   └── Cloud_Katana/
├── config/
│   └── tools.env            # ← Configuración
├── logs/
├── evidence/                # ← Resultados de análisis
└── run_tool.sh              # ← Helper script
```

### Opción 2: Instalación Parcial (Debugging)

```bash
# Ver logs en tiempo real
./install.sh 2>&1 | tee install.log

# Ver solo errores
./install.sh 2>&1 | grep ERROR

# Ver progreso
./install.sh 2>&1 | grep "✓\|✗\|⚠"
```

### Opción 3: Instalación Manual Paso a Paso

```bash
cd /home/hack/mcp-kali-forensics

# 1. Solo dependencias del sistema
apt install -y python3 python3-pip python3-venv git curl build-essential

# 2. Solo Python deps
pip3 install -q volatility3

# 3. Solo tools
bash scripts/install_local.sh
```

---

## 📁 Estructura de Directorios Creada

```
/home/hack/mcp-kali-forensics/
├── install.sh                      # Script principal
├── scripts/
│   ├── install_local.sh            # Instalador local
│   └── ... (otros scripts)
│
├── tools/                          # ← NUEVOS TOOLS AQUÍ
│   ├── Sparrow/
│   │   ├── Sparrow.ps1
│   │   ├── README.md
│   │   └── ...
│   ├── hawk/
│   ├── o365-extractor/
│   ├── Loki/
│   ├── yara-rules/
│   ├── azurehound/
│   ├── ROADtools/
│   ├── Monkey365/
│   └── Cloud_Katana/
│
├── config/
│   └── tools.env                   # Configuración (nueva)
│
├── logs/
│   ├── install.log                 # Log de instalación
│   └── ...
│
├── evidence/                       # Resultados de análisis
│   ├── sparrow/
│   ├── hawk/
│   ├── o365/
│   └── ...
│
└── run_tool.sh                     # Helper para ejecutar tools
```

---

## ⚙️ Configuración

### Archivo: `config/tools.env`

```bash
# Rutas
TOOLS_DIR="${PROJECT_ROOT}/tools"        # Carpeta de tools
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"  # Resultados
LOG_DIR="${PROJECT_ROOT}/logs"           # Logs

# Timeouts
TOOL_TIMEOUT=3600                        # 1 hora por tool
ANALYSIS_TIMEOUT=7200                    # 2 horas total

# Debug
DEBUG=false
VERBOSE=false
```

**Para cambiar configuración**:

```bash
# Opción 1: Editar directamente
nano config/tools.env

# Opción 2: Exportar variables
export TOOLS_DIR="/custom/path/tools"
export TOOL_TIMEOUT=7200
./install.sh

# Opción 3: Pasar como argumentos (futuro)
./install.sh --tools-dir=/custom/path --timeout=7200
```

---

## 🛠️ Uso de Tools

### Script Helper: `run_tool.sh`

```bash
# Ejecutar Sparrow
./run_tool.sh sparrow --TenantId xxx --DaysToSearch 90

# Ejecutar Hawk
./run_tool.sh hawk --TargetDomain empresa.com

# Ejecutar O365
./run_tool.sh o365 --tenant-id xxx

# Ejecutar Loki
./run_tool.sh loki --path /var/evidence --intense

# Ejecutar YARA
./run_tool.sh yara -r /opt/malware/yara-rules /var/evidence
```

### Uso Directo

```bash
# Navegar a tool específico
cd ./tools/Sparrow
pwsh -ExecutionPolicy Bypass -File "./Sparrow.ps1" ...

# O usar Python
cd ./tools/o365-extractor
python3 ./o365_extractor.py ...
```

---

## ✅ Verificación de Instalación

### Script Automático

```bash
# En el script de instalación se ejecuta:
./scripts/verify_tools.sh

# Muestra:
# ✓ Sparrow instalado
# ✓ Hawk instalado
# ⚠ O365 Extractor no encontrado (usar fallback)
# ... etc
```

### Manual

```bash
# Verificar que cada carpeta existe
ls -la ./tools/

# Verificar permisos
ls -la ./tools/azurehound/azurehound  # debe ser ejecutable

# Verificar logs
cat ./logs/install.log | grep ERROR
```

---

## 🐛 Troubleshooting

### Error: "Authentication failed for GitHub"

**Causa**: Token de GitHub expirado o credenciales incorrectas

**Solución**:
```bash
# El script usa HTTPS sin autenticación
# Si aún falla, omite ese tool:
export SKIP_O365=1
./install.sh
```

### Error: "Tool not found in expected location"

**Causa**: Descarga incompleta

**Solución**:
```bash
# Limpiar y reintentar
rm -rf ./tools
./install.sh

# O instalar solo ese tool:
bash scripts/install_local.sh
# Luego ejecutar solo la función necesaria
```

### Error: "Permission denied"

**Causa**: Permisos incorrectos

**Solución**:
```bash
# Dar permisos de lectura/ejecución
chmod -R +rx ./tools
chmod +x ./run_tool.sh ./install.sh

# O cambiar propiedad
sudo chown -R $USER:$USER ./tools ./evidence ./logs
```

### Error: "PowerShell command not found"

**Causa**: PowerShell no instalado

**Solución**:
```bash
# Instalar PowerShell
sudo apt install -y powershell

# O descargar binarios en lugar de PS scripts
# El script intenta fallback automático
```

---

## 📊 Espacios Requeridos

```
Sparrow:        ~50 MB
Hawk:           ~20 MB
O365:           ~30 MB
Loki:           ~100 MB
YARA rules:     ~200 MB
AzureHound:     ~10 MB
ROADtools:      ~20 MB
Monkey365:      ~50 MB
Cloud Katana:   ~30 MB
-----------
TOTAL:          ~510 MB (+ dependencias Python)

Evidence dir:   Variable (depende de análisis)
Logs:           ~10 MB
```

---

## 🔄 Actualizar Tools

```bash
# Actualizar todos los tools a última versión
cd ./tools

for dir in */; do
  cd "$dir"
  git pull origin main || git pull origin master
  cd ..
done

# O solo uno
cd ./tools/Sparrow
git pull origin main
```

---

## 🗑️ Desinstalar / Limpiar

```bash
# Eliminar tools pero mantener config
rm -rf ./tools

# Eliminar todo (¡CUIDADO!)
rm -rf ./tools ./evidence ./logs ./config/tools.env

# Reinstalar
./install.sh
```

---

## 🚀 Integración con Backend

### En `api/config.py`:

```python
from pathlib import Path

# Cargar variables del tools.env
PROJECT_ROOT = Path(__file__).parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"
EVIDENCE_DIR = PROJECT_ROOT / "evidence"

# Configuración de cada tool
SPARROW_PATH = TOOLS_DIR / "Sparrow" / "Sparrow.ps1"
HAWK_PATH = TOOLS_DIR / "hawk" / "hawk.ps1"
O365_EXTRACTOR_PATH = TOOLS_DIR / "o365-extractor"
```

### En scripts forenses:

```python
import os
from pathlib import Path

# Cargar tools.env
tools_env_path = Path(__file__).parent.parent / "config" / "tools.env"
if tools_env_path.exists():
    with open(tools_env_path) as f:
        for line in f:
            if line.startswith("TOOLS_DIR="):
                TOOLS_DIR = line.split("=")[1].strip()
                break

# Usar tools
sparrow_path = os.path.join(TOOLS_DIR, "Sparrow", "Sparrow.ps1")
```

---

## 📝 Logs

Todos los logs se guardan en `./logs/install.log`:

```bash
# Ver logs en tiempo real
tail -f ./logs/install.log

# Ver solo errores
grep ERROR ./logs/install.log

# Ver solo éxitos
grep "✓" ./logs/install.log

# Búsqueda con timestamp
grep "2025-01-10" ./logs/install.log
```

---

## 🎯 Próximos Pasos

1. **Instalar herramientas**:
   ```bash
   ./install.sh
   ```

2. **Verificar instalación**:
   ```bash
   ls -la ./tools/
   ./run_tool.sh --help
   ```

3. **Configurar backend**:
   ```bash
   # Backend cargará tools.env automáticamente
   cd api && python api/main.py
   ```

4. **Ejecutar análisis**:
   ```bash
   # Desde el dashboard M365
   http://localhost:3000/m365
   # Seleccionar tools y ejecutar
   ```

---

## 📞 Soporte

**Problema**: Script no ejecuta  
**Solución**: `chmod +x install.sh` + `sudo bash install.sh`

**Problema**: Git clone falla  
**Solución**: Script usa HTTPS sin autenticación, debería funcionar

**Problema**: Python deps fallan  
**Solución**: `pip3 install --upgrade pip` + `./install.sh`

**Problema**: PowerShell no disponible  
**Solución**: `sudo apt install powershell` o usar fallback a Python

---

## ✨ Características de esta Instalación

✅ Sin Docker (nativo en Kali)  
✅ Sin autenticación GitHub  
✅ Tools dentro del proyecto  
✅ Configuración por archivo  
✅ Logs completos  
✅ Fallback automático para errores  
✅ Helper script para ejecutar tools  
✅ Fácil de debuggear  

---

**Versión**: 4.2 Local Deployment  
**Fecha**: Diciembre 2025  
**Status**: ✅ Production Ready
