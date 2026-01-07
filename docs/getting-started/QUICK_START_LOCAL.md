# 🚀 Instalación Local v4.2 - QUICK START

## El Problema ❌

```bash
sudo ./scripts/install.sh
# ❌ Error: Authentication failed for 'https://github.com/SecurityRiskAdvisors/sra-o365-extractor.git/'
# ❌ Error: Git requiere autenticación
# ❌ Error: Tools quedan en /opt (permisos del sistema)
```

## La Solución ✅

**Todos los tools se descargan en una carpeta `/tools` dentro del proyecto.**

```
/home/hack/mcp-kali-forensics/
├── tools/                    # ← Aquí van todos los tools
│   ├── Sparrow/
│   ├── hawk/
│   ├── o365-extractor/
│   ├── Loki/
│   └── ... (9 tools más)
├── evidence/                 # ← Resultados de análisis
├── logs/                     # ← Logs
├── config/
│   └── tools.env            # ← Configuración
└── install.sh               # ← Script de instalación
```

---

## 📋 Instalación en 3 Pasos

### Paso 1: Navegar al proyecto

```bash
cd /home/hack/mcp-kali-forensics
```

### Paso 2: Ejecutar instalación

```bash
# Instalación completa (con sudo solo si es necesario)
./install.sh

# O con más detalles
./install.sh 2>&1 | tee install_output.log
```

**Duración**: 15-30 minutos

### Paso 3: Verificar instalación

```bash
./verify_installation.sh
```

**Esperado**:
```
✓ Sparrow (200M)
✓ Hawk (50M)
✓ O365 Extractor (30M)
✓ Loki (100M)
✓ YARA Rules (200M)
... (4 tools más)

✓ Todos los tools están instalados
```

---

## 🎯 Eso es Todo

**Los tools están listos** en `/home/hack/mcp-kali-forensics/tools/`

---

## 📁 Qué se Creó

```
✓ ./tools/                    (9 herramientas forenses)
✓ ./logs/                     (logs de instalación)
✓ ./evidence/                 (resultados de análisis)
✓ ./config/tools.env          (configuración)
✓ ./run_tool.sh               (script helper)
✓ ./verify_installation.sh    (verificador)
```

---

## 🔧 Usar los Tools

### Opción 1: Script Helper

```bash
./run_tool.sh sparrow --help
./run_tool.sh hawk --help
./run_tool.sh loki --help
```

### Opción 2: Directamente

```bash
cd ./tools/Sparrow
pwsh -ExecutionPolicy Bypass -File "./Sparrow.ps1"
```

---

## ⚠️ Si Algo Falla

### Error: "No such file or directory"

```bash
# Hacer scripts ejecutables
chmod +x install.sh scripts/install_local.sh
./install.sh
```

### Error: "Authentication failed"

```bash
# El script nuevo usa HTTPS sin autenticación
# Debería funcionar. Si no:
rm -rf ./tools
./install.sh  # Reintentar
```

### Error: "PowerShell not found"

```bash
# Algunos tools necesitan PowerShell
sudo apt install powershell
./install.sh
```

---

## ✅ Verificación Rápida

```bash
# ¿Están los tools instalados?
ls -la ./tools/

# ¿Cuánto espacio usan?
du -sh ./tools/

# ¿Hay logs de errores?
grep ERROR ./logs/install.log

# ¿Está la config?
cat ./config/tools.env | head -20
```

---

## 🚀 Próximo Paso: Backend

El backend cargará automáticamente los tools de `./tools`:

```bash
# En api/config.py, ya está configurado para usar:
TOOLS_DIR = PROJECT_ROOT / "tools"
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
```

**Iniciar backend**:
```bash
cd /home/hack/mcp-kali-forensics
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

---

## 📊 Resumen

| Antes | Después |
|-------|---------|
| ❌ Errores de autenticación GitHub | ✅ Sin autenticación requerida |
| ❌ Tools en /opt (permisos del sistema) | ✅ Tools en ./tools (proyecto) |
| ❌ Problemas en producción | ✅ Fácil de clonar/migrar |
| ❌ Difícil de debuggear | ✅ Todo en la carpeta del proyecto |

---

## 📞 Archivos Importantes

| Archivo | Propósito |
|---------|----------|
| `install.sh` | Script de entrada (llama a install_local.sh) |
| `scripts/install_local.sh` | Instalador real (clona en ./tools) |
| `verify_installation.sh` | Verifica que todo está bien |
| `config/tools.env` | Configuración de paths y timeouts |
| `run_tool.sh` | Helper para ejecutar tools |
| `INSTALL_LOCAL_GUIDE.md` | Documentación completa (si necesitas más detalles) |
| `CONFIG_UPDATE_EXAMPLE.py` | Ejemplo de cómo actualizar backend config |

---

## 🎉 Resultado Final

```
✓ Sin errores de autenticación
✓ Todos los tools en ./tools/
✓ Configuración automática
✓ Listo para producción
✓ Fácil de mantener y actualizar
```

**¡Listo para usar!** 🚀

---

**Próximos comandos**:

```bash
# 1. Instalar
./install.sh

# 2. Verificar
./verify_installation.sh

# 3. Ver la estructura
ls -la ./tools/

# 4. Iniciar backend (en otra terminal)
python -m uvicorn api.main:app --reload

# 5. Iniciar frontend
cd frontend-react && npm run dev

# 6. Abrir navegador
# http://localhost:3000/m365
```

---

**Versión**: 4.2 Local Deployment  
**Status**: ✅ Ready to Use
