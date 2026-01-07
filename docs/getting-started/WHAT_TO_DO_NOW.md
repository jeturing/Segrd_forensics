# ✅ TODO - Instalación Local v4.2

## Archivos Nuevos Creados

```
✓ ./install.sh                    (Script principal - 864 bytes)
✓ ./scripts/install_local.sh      (Instalador - 12 KB, +450 líneas)
✓ ./verify_installation.sh        (Verificador - 4.6 KB)
✓ ./config/tools.env              (Configuración - 3 KB)
✓ ./INSTALL_LOCAL_GUIDE.md        (Documentación completa)
✓ ./QUICK_START_LOCAL.md          (Guía rápida)
✓ ./CONFIG_UPDATE_EXAMPLE.py      (Ejemplo para backend)
```

---

## 🎯 QUÉ HACER AHORA

### PASO 1: Ejecutar Instalación

```bash
# Ir al proyecto
cd /home/hack/mcp-kali-forensics

# Ejecutar instalación
./install.sh

# O ver el progreso:
./install.sh 2>&1 | tee install_progress.log
```

**Esto va a**:
- ✓ Crear carpeta `/home/hack/mcp-kali-forensics/tools/`
- ✓ Clonar 9 herramientas forenses
- ✓ Instalar dependencias Python
- ✓ Crear archivos de configuración
- ✓ Generar logs

**Duración**: 15-30 minutos (depende de conexión)

---

### PASO 2: Verificar Instalación

```bash
./verify_installation.sh
```

**Esperado**:
```
✓ Sparrow
✓ Hawk
✓ O365 Extractor
✓ Loki
✓ YARA Rules
✓ AzureHound
✓ ROADtools
✓ Monkey365
✓ Cloud Katana

✓ Todos los tools están instalados
```

---

### PASO 3: Actualizar Backend Config

El backend ya tiene soporte para tools locales, pero si quieres verificar:

**Archivo**: `api/config.py`

Debe tener:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
```

**Si está en versión antigua**:
- Lee: `CONFIG_UPDATE_EXAMPLE.py` (te muestra exactamente qué cambiar)
- Reemplaza rutas de `/opt/forensics-tools` por `./tools`

---

### PASO 4: Iniciaar Backend

```bash
cd /home/hack/mcp-kali-forensics

# Instalar dependencias (si no lo hiciste)
pip3 install -r requirements.txt

# Iniciar server
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

**Esperado**:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     ✓ Verificando herramientas instaladas...
INFO:     ✓ Sparrow found at ./tools/Sparrow/Sparrow.ps1
INFO:     ✓ Hawk found at ./tools/hawk/hawk.ps1
... (resto de tools)
INFO:     ✓ All required tools installed
```

---

### PASO 5: Iniciar Frontend

**En otra terminal**:

```bash
cd /home/hack/mcp-kali-forensics/frontend-react
npm install  # Si no lo hiciste
npm run dev
```

**Esperado**:
```
VITE v5.4.21 building for development
Port 3000 configured. Accessing...
```

---

### PASO 6: Probar en Navegador

Abre: **http://localhost:3000/m365**

**Debe aparecer**:
- Tarjeta "Selecciona herramientas" (con 12 tools)
- Tarjeta "💻 Comandos Automatizados" (nueva, abajo)

---

## 🔍 Si Algo No Funciona

### Error: "No such file or directory"

```bash
# Hacer scripts ejecutables
chmod +x /home/hack/mcp-kali-forensics/install.sh
chmod +x /home/hack/mcp-kali-forensics/scripts/install_local.sh
chmod +x /home/hack/mcp-kali-forensics/verify_installation.sh

# Reintentar
./install.sh
```

### Error: "Authentication failed for GitHub"

```bash
# El script nuevo usa HTTPS sin autenticación
# Si aún falla, limpia y reinicia:
rm -rf ./tools
./install.sh  # Reintentar

# Alternativa: Ver qué falta
./verify_installation.sh  # Te dice qué tools faltan
```

### Error: "PowerShell not found"

```bash
# Instalar PowerShell
sudo apt install powershell

# Reintentar instalación
./install.sh
```

### Error: "pip: command not found"

```bash
# Instalar pip
sudo apt install python3-pip

# Reintentar instalación
./install.sh
```

---

## 📊 Estructura Final

Después de ejecutar `./install.sh`:

```
/home/hack/mcp-kali-forensics/
├── tools/                      ✓ SE CREA
│   ├── Sparrow/                ✓ Clonado
│   ├── hawk/                   ✓ Clonado
│   ├── o365-extractor/         ✓ Clonado
│   ├── Loki/                   ✓ Clonado
│   ├── yara-rules/             ✓ Clonado
│   ├── azurehound/             ✓ Descargado
│   ├── ROADtools/              ✓ Clonado
│   ├── Monkey365/              ✓ Clonado
│   └── Cloud_Katana/           ✓ Clonado
│
├── evidence/                   ✓ SE CREA
│   ├── sparrow/                (resultados de análisis)
│   ├── hawk/
│   ├── o365/
│   └── ... (uno por tool)
│
├── logs/                       ✓ SE CREA
│   └── install.log             (log de instalación)
│
├── config/                     ✓ EXISTENTE
│   ├── tools.env               ✓ SE ACTUALIZA
│   └── ...
│
├── install.sh                  ✓ NUEVO
├── verify_installation.sh      ✓ NUEVO
├── run_tool.sh                 ✓ SE CREA (helper)
└── ... (resto del proyecto)
```

---

## 🎯 Checklist de Completación

```
[ ] Ejecuté ./install.sh
[ ] Verificación con ./verify_installation.sh pasó
[ ] Revisé estructura con ls -la ./tools/
[ ] Backend arranca sin errores de tools
[ ] Frontend se ve en http://localhost:3000
[ ] Puedo ver la tarjeta "Comandos Automatizados"
[ ] Los 12 tools aparecen en la UI
```

---

## 📚 Documentación

Si necesitas más información:

| Quiero | Leo |
|--------|-----|
| Quick start rápido | `QUICK_START_LOCAL.md` |
| Guía completa de instalación | `INSTALL_LOCAL_GUIDE.md` |
| Cómo actualizar el backend | `CONFIG_UPDATE_EXAMPLE.py` |
| Qué hace cada script | Este archivo |

---

## 🚀 Resumen

**Lo que necesitas hacer ahora**:

1. **Ejecutar instalación**:
   ```bash
   cd /home/hack/mcp-kali-forensics
   ./install.sh
   ```

2. **Esperar a que termine** (15-30 minutos)

3. **Verificar**:
   ```bash
   ./verify_installation.sh
   ```

4. **Iniciar servicios** (en terminales separadas):
   ```bash
   # Terminal 1: Backend
   python -m uvicorn api.main:app --reload --port 8080
   
   # Terminal 2: Frontend
   cd frontend-react && npm run dev
   ```

5. **Probar en navegador**:
   ```
   http://localhost:3000/m365
   ```

**¡Eso es todo!** 🎉

---

## ✨ Ventajas de Esta Instalación

✅ **Sin errores de autenticación** - Clona con HTTPS sin credenciales  
✅ **Tools en el proyecto** - Fácil de versionar y migrar  
✅ **Automático** - El backend detecta tools automáticamente  
✅ **Debuggeable** - Todo está en una carpeta  
✅ **Escalable** - Fácil agregar más tools después  
✅ **Seguro** - No modifica el sistema (`/opt`, `/var`)  

---

**¿Preguntas?** Revisa la documentación correspondiente:
- `QUICK_START_LOCAL.md` - Si necesitas ir rápido
- `INSTALL_LOCAL_GUIDE.md` - Si necesitas detalles
- `CONFIG_UPDATE_EXAMPLE.py` - Si necesitas actualizar backend

**Versión**: 4.2 Local Deployment  
**Status**: ✅ Ready to Execute
