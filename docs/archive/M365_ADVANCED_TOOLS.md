# M365 Advanced Forensics - Guía Completa

## 🎯 Herramientas Implementadas

### Categoría: Básico
1. **Sparrow** 🦅
   - Detección de tokens OAuth abusados
   - Análisis de aplicaciones sospechosas
   - Sign-ins de riesgo

2. **Hawk** 🦅
   - Reglas de reenvío maliciosas
   - Delegaciones de buzones
   - Permisos de Teams

3. **O365 Extractor** 📧
   - Unified Audit Logs completos
   - Exportación PST
   - Timeline forense

### Categoría: Reconocimiento
4. **AzureHound** 🐕
   - Attack paths en Azure AD
   - Integración con BloodHound
   - Visualización de grafos

5. **ROADtools** 🗺️
   - Reconocimiento completo de Azure AD
   - Base de datos SQLite con toda la info
   - GUI web interactiva

6. **AADInternals** 🔓
   - Penetration testing Azure AD
   - Token manipulation
   - Backdoor creation (Red Team)

### Categoría: Auditoría
7. **Monkey365** 🐵
   - 300+ security checks
   - Compliance reports
   - HTML/JSON exports

8. **CrowdStrike CRT** 🦅
   - Análisis de riesgos Azure/M365
   - Misconfiguration detection
   - Remediation recommendations

9. **Maester** 🎯
   - Security testing framework
   - Pester tests automatizados
   - CI/CD integration

### Categoría: Forense
10. **M365 Extractor Suite** 📦
    - Exchange Online forensics
    - Teams data extraction
    - OneDrive analysis

11. **Graph Explorer** 📈
    - Custom queries a Graph API
    - Bulk data extraction
    - Advanced filtering

12. **Cloud Katana** ⚔️
    - Incident response automation
    - Playbooks predefinidos
    - Logic Apps integration

---

## 🔄 Flujo de Trabajo

### 1. Crear Investigación
```http
POST /api/v41/investigations/
{
  "case_id": "IR-2025-001",
  "title": "Compromiso de cuenta M365",
  "priority": "high",
  "description": "Análisis forense completo"
}
```

### 2. Ejecutar Análisis M365
```http
POST /forensics/m365/analyze
{
  "investigation_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "xxxxx-xxxxx-xxxxx-xxxxx",
  "case_id": "IR-2025-001",
  "scope": [
    "sparrow",
    "hawk",
    "azurehound",
    "roadtools",
    "monkey365"
  ],
  "target_users": ["user1@contoso.com", "user2@contoso.com"],
  "days_back": 90,
  "priority": "high"
}
```

### 3. Monitorear Progreso
```http
GET /forensics/case/{case_id}/status

Response:
{
  "status": "running",
  "progress_percentage": 45,
  "current_tool": "azurehound",
  "current_step": "Enumerando permisos de aplicaciones",
  "completed_tools": ["sparrow", "hawk"],
  "estimated_completion": "2025-12-06 15:30 UTC"
}
```

### 4. Generar Reporte Multiidioma
```http
POST /forensics/m365/investigations/{investigation_id}/report?language=es&format=pdf

Idiomas soportados:
- en: English
- es: Español
- zh-CN: 中文 (简体) - Chino Simplificado
- zh-HK: 中文 (繁體) - Cantonés

Formatos:
- html: Reporte HTML con estilos
- pdf: Documento PDF profesional
- json: Datos estructurados
- markdown: Formato Markdown
```

---

## 📦 Instalación

### Instalación Rápida
```bash
cd /home/hack/mcp-kali-forensics
sudo ./scripts/install_m365_tools.sh
```

### Instalación Manual por Herramienta

#### AzureHound
```bash
git clone https://github.com/BloodHoundAD/AzureHound.git /opt/forensics-tools/azurehound
cd /opt/forensics-tools/azurehound
go build -o azurehound
```

#### ROADtools
```bash
pip3 install roadtools roadrecon roadlib
```

#### Monkey365
```bash
git clone https://github.com/silverhack/monkey365.git /opt/forensics-tools/monkey365
pwsh -Command "Install-Module -Name monkey365 -Force"
```

---

## 🎨 UI - Selector de Herramientas

El frontend ahora muestra todas las herramientas agrupadas por categoría:

```jsx
// Selección múltiple con botones "Todas/Ninguna"
// Iconos únicos por herramienta
// Descripción tooltip en hover
// Checkboxes grandes con animaciones
```

### Características UI:
- ✅ **Dropdown de Casos** con buscador en tiempo real
- ✅ **Modal de Usuarios** con checkboxes multi-selección
- ✅ **Consola de Ejecución** animada en esquina inferior derecha
- ✅ **Selector Multi-Tenant** para cambiar entre organizaciones
- ✅ **Progreso en Tiempo Real** con barra animada y estados

---

## 🔗 Vinculación con Investigaciones

**TODO** elemento de análisis M365 se vincula a una investigación:

```python
# Backend automaticamente vincula:
- Casos -> Investigation
- Evidencia -> Investigation
- IOCs -> Investigation  
- Timeline -> Investigation
- Reportes -> Investigation
```

### Beneficios:
- ✅ **Trazabilidad completa** - Chain of custody
- ✅ **Reportes unificados** - Todos los datos en un solo reporte
- ✅ **Correlación automática** - IOCs compartidos entre casos
- ✅ **Auditoría** - Quién hizo qué y cuándo

---

## 📊 Reportes Multiidioma

### Ejemplo: Generar reporte en Español
```bash
curl -X POST "http://localhost:8888/forensics/m365/investigations/IR-2025-001/report?language=es&format=pdf"
```

### Contenido del Reporte:
1. **Resumen Ejecutivo** (traducido)
2. **Hallazgos Críticos** con severidades
3. **Indicadores de Compromiso (IOCs)** en tabla
4. **Línea de Tiempo** de eventos
5. **Recomendaciones** de remediación
6. **Metadata** (herramientas usadas, analista, fecha)

### Formatos de Salida:
- **HTML**: Reporte web completo con estilos CSS
- **PDF**: Documento profesional (requiere wkhtmltopdf)
- **JSON**: Datos estructurados para integración
- **Markdown**: Compatible con Git/Confluence

---

## 🔐 Autenticación

Todas las herramientas usan el mismo token de Azure AD:

```python
# Token almacenado en localStorage del navegador
token_key = f"azure_token_{tenant_id}"

# Las herramientas lo usan automáticamente
# Sin necesidad de re-autenticación
```

---

## 🚀 Ejecución desde Frontend

### Selección de Herramientas:
1. Navegar a **Microsoft 365** en el menú
2. Seleccionar o crear un **Caso**
3. Elegir **Usuarios objetivo** (opcional)
4. Marcar las **herramientas** deseadas por categoría
5. Click **"Iniciar análisis"**

### Monitoreo en Tiempo Real:
- Consola animada aparece en esquina inferior derecha
- Muestra herramienta actual ejecutándose
- Barra de progreso con porcentaje
- Estados por herramienta: ⏸️ Pendiente | ⏳ Ejecutando | ✓ Completado

---

## 📋 Checklist Pre-Análisis

Antes de ejecutar un análisis M365:

- [ ] Tenant ID configurado
- [ ] Token Azure AD válido (Device Code Flow)
- [ ] Permisos Graph API correctos:
  - `User.Read.All`
  - `Directory.Read.All`
  - `AuditLog.Read.All`
  - `IdentityRiskEvent.Read.All`
  - `Reports.Read.All`
- [ ] Investigación creada en el sistema
- [ ] Usuarios objetivo identificados (opcional)
- [ ] Espacio en disco suficiente (mínimo 10GB)

---

## 🛠️ Troubleshooting

### Error: "Tool not found"
```bash
# Verificar instalación
ls -la /opt/forensics-tools/

# Re-instalar herramienta específica
sudo ./scripts/install_m365_tools.sh
```

### Error: "Token expired"
```bash
# Renovar token desde frontend
# Click "Iniciar Device Code" en sección Autenticación
```

### Error: "Permission denied"
```bash
# Verificar permisos de App Registration en Azure Portal
# Agregar permisos faltantes en "API permissions"
```

---

## 📚 Referencias

- [AzureHound Documentation](https://github.com/BloodHoundAD/AzureHound)
- [ROADtools Guide](https://github.com/dirkjanm/ROADtools)
- [Monkey365 Wiki](https://github.com/silverhack/monkey365)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/)
- [JETURING Documentation](./JETURING_MCP_DOCUMENTATION_v3.1.md)

---

## 🎯 Próximos Pasos

1. **Ejecutar instalador**
   ```bash
   sudo ./scripts/install_m365_tools.sh
   ```

2. **Verificar herramientas**
   ```bash
   cd /opt/forensics-tools
   ls -la
   ```

3. **Iniciar servicio**
   ```bash
   cd /home/hack/mcp-kali-forensics
   ./start.sh
   ```

4. **Abrir frontend**
   ```
   http://localhost:3000/m365
   ```

5. **Crear primera investigación y ejecutar análisis** 🚀

---

## ✅ Status de Implementación

| Componente | Estado | Notas |
|------------|--------|-------|
| Frontend - Selector de herramientas | ✅ | 12 herramientas con categorías |
| Frontend - Dropdown casos | ✅ | Con buscador en tiempo real |
| Frontend - Modal usuarios | ✅ | Multi-selección con checkboxes |
| Frontend - Consola animada | ✅ | Progreso en tiempo real |
| Backend - Servicios M365 | ✅ | `m365_tools.py` con 12 handlers |
| Backend - Vinculación investigaciones | ✅ | Todos los análisis se vinculan |
| Backend - Reportes multiidioma | ✅ | 4 idiomas x 4 formatos |
| Instalador herramientas | ✅ | `install_m365_tools.sh` |
| Documentación | ✅ | Este archivo |

**COMPLETADO** ✅✅✅

---

Generado por: JETURING Forensics Platform  
Fecha: 2025-12-06  
Versión: 4.2-M365-Advanced
