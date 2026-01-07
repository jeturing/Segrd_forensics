# ✅ Actualización: Todas las Herramientas M365 en Script de Instalación

## 📋 Cambios Implementados

### 1. Script de Instalación Principal (`scripts/install.sh`)

**Antes**: Solo incluía 3 herramientas básicas
- Sparrow
- Hawk  
- O365 Extractor

**Ahora**: Incluye todas las 12 herramientas mostradas en la UI

#### 🔵 BÁSICO (3 herramientas)
✅ Sparrow - Detección de tokens abusados y apps OAuth  
✅ Hawk - Reglas maliciosas, delegaciones y Teams  
✅ O365 - Unified Audit Logs completos  

#### 🔍 RECONOCIMIENTO (3 herramientas)
✅ AzureHound - Attack paths en Azure AD (BloodHound)  
✅ ROADtools - Reconocimiento completo de Azure AD  
✅ AADInternals - Penetration testing Azure AD  

#### 📊 AUDITORÍA (3 herramientas)
✅ Monkey365 - 300+ checks de seguridad M365  
✅ CrowdStrike CRT - Análisis de riesgos Azure/M365  
✅ Maester - Security testing framework M365  

#### 🔬 FORENSE (3 herramientas)
✅ M365 Extractor - Extracción forense Exchange/Teams/OneDrive  
✅ Graph SDK - Queries custom a Microsoft Graph API  
✅ Cloud Katana - Automation de respuesta a incidentes  

---

## 🆕 Nuevos Scripts Creados

### 1. `scripts/verify_tools.sh`
Script interactivo que:
- ✅ Verifica qué herramientas están instaladas
- ✅ Lista herramientas faltantes
- ✅ Ofrece instalación individual on-demand
- ✅ Genera reporte de estado

**Uso:**
```bash
./scripts/verify_tools.sh
```

### 2. `docs/TOOLS_REFERENCE.md`
Documentación completa con:
- ✅ Descripción de cada herramienta
- ✅ Casos de uso
- ✅ Comandos de ejemplo
- ✅ Ubicación de instalación
- ✅ Links a repositorios oficiales
- ✅ Permisos requeridos

---

## 🔧 Mejoras en el Script de Instalación

### Manejo de Errores
```bash
# Continúa si alguna herramienta falla
command || echo "⚠ Instalación parcial"
```

### Instalación Inteligente
```bash
# Verifica si ya existe antes de clonar
if [ ! -d "/opt/forensics-tools/tool" ]; then
    git clone ...
else
    echo "⚠ Ya instalado, omitiendo"
fi
```

### Verificación Post-Instalación
```bash
# Reporte detallado por categoría
📋 HERRAMIENTAS BÁSICAS:
✓ Sparrow 365
✓ Hawk
✓ O365 Extractor

📋 HERRAMIENTAS DE RECONOCIMIENTO:
✓ AzureHound
✓ ROADtools
⚠ AADInternals (requiere configuración manual)
```

---

## 🚀 Cómo Usar

### Instalación Completa (Recomendado)
```bash
cd /home/hack/mcp-kali-forensics
sudo ./scripts/install.sh
```

### Verificar Estado
```bash
./scripts/verify_tools.sh
```

### Instalar Solo Herramientas Faltantes
```bash
# El script verify_tools.sh pregunta por cada herramienta faltante
./scripts/verify_tools.sh
# Responde 's' para instalar las que faltan
```

---

## 📦 Estructura de Directorios

```
/opt/forensics-tools/
├── Sparrow/                    # Básico
├── hawk/                       # Básico
├── sra-o365-extractor/         # Básico
├── Loki/                       # Endpoint scanning
├── yara-rules/                 # Malware detection
├── azurehound/                 # Reconocimiento
├── monkey365/                  # Auditoría
├── crt/                        # Auditoría (CrowdStrike)
├── maester/                    # Auditoría
├── Microsoft-Extractor-Suite/  # Forense
└── cloud-katana/               # Forense
```

---

## 🔍 Validación Backend

Las herramientas se verifican automáticamente al iniciar el backend:

```python
# api/services/health.py
async def check_tools_availability():
    tools_status = {
        "sparrow": check_path("/opt/forensics-tools/Sparrow"),
        "hawk": check_path("/opt/forensics-tools/hawk"),
        "azurehound": check_path("/opt/forensics-tools/azurehound"),
        "monkey365": check_path("/opt/forensics-tools/monkey365"),
        # ... etc
    }
    return tools_status
```

---

## 📝 Notas Importantes

### PowerShell Modules
Algunos módulos requieren instalación manual si fallan:
```powershell
Install-Module -Name AADInternals -Force
Install-Module -Name Maester -Force
Install-Module -Name Monkey365 -Force
```

### Python Packages
ROADtools y Graph SDK via pip:
```bash
pip3 install roadtools roadrecon roadlib
pip3 install msgraph-sdk azure-identity msal
```

### Permisos
Algunos tools requieren permisos específicos en Azure AD:
- **AuditLog.Read.All**
- **Directory.Read.All**
- **IdentityRiskEvent.Read.All**
- **User.Read.All**

Consulta `docs/M365_SETUP.md` para configuración completa.

---

## ✅ Checklist de Validación

- [x] Script `install.sh` actualizado con 12 herramientas
- [x] Script `verify_tools.sh` creado
- [x] Documentación `TOOLS_REFERENCE.md` creada
- [x] Verificación post-instalación mejorada
- [x] Manejo de errores implementado
- [x] Instalación idempotente (no reinstala si existe)
- [x] Soporte para instalación parcial
- [x] Categorización de herramientas en la UI
- [x] Todas las herramientas de la imagen incluidas

---

## 🎯 Próximos Pasos

1. **Ejecutar instalación completa**:
   ```bash
   sudo ./scripts/install.sh
   ```

2. **Verificar estado**:
   ```bash
   ./scripts/verify_tools.sh
   ```

3. **Reiniciar backend** para detectar nuevas herramientas:
   ```bash
   sudo systemctl restart mcp-forensics
   ```

4. **Validar en UI**: Todas las herramientas deberían aparecer como disponibles en la interfaz.

---

**Fecha**: 2025-12-07  
**Versión**: 4.1  
**Estado**: ✅ Completado
