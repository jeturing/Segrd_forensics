# 📚 Índice de Documentación - MCP Kali Forensics v4.2

## Estructura de Documentación

```
/docs/
├── tools/                              # Documentación de herramientas
│   ├── 01_BASICO.md                   # Sparrow, Hawk, O365
│   ├── 02_RECONOCIMIENTO.md           # AzureHound, ROADtools, AADInternals
│   ├── 03_AUDITORIA.md                # Monkey365, Maester, PnP PowerShell
│   ├── 04_FORENSE.md                  # Graph API, Cloud Katana, Loki
│   └── INDEX.md                       # Este archivo
│
├── guides/                             # Guías prácticas
│   ├── QUICK_START.md                 # Inicio rápido
│   ├── INSTALLATION.md                # Instalación
│   ├── SETUP_M365.md                  # Configurar M365
│   └── TROUBLESHOOTING.md             # Solución de problemas
│
├── api/                                # Documentación API
│   ├── ENDPOINTS.md                   # Endpoints REST
│   ├── AUTHENTICATION.md              # Autenticación y autorización
│   └── EXAMPLES.md                    # Ejemplos de uso
│
├── architecture/                       # Documentación de arquitectura
│   ├── SYSTEM_DESIGN.md               # Diseño del sistema
│   ├── DATA_FLOW.md                   # Flujo de datos
│   └── SECURITY.md                    # Consideraciones de seguridad
│
└── playbooks/                          # Playbooks de respuesta a incidentes
    ├── ACCOUNT_COMPROMISE.md
    ├── DATA_EXFILTRATION.md
    ├── MALWARE_RESPONSE.md
    └── LATERAL_MOVEMENT.md
```

---

## 🎯 Herramientas por Categoría

### 🦅 BÁSICO (3 herramientas)

Conjunto fundamental para análisis inicial de amenazas.

| Herramienta | Propósito | Documentación |
|-------------|----------|---------------|
| **Sparrow** | OAuth y apps maliciosas | [01_BASICO.md#1-sparrow-365](./01_BASICO.md#1-sparrow-365) |
| **Hawk** | Reglas de correo y delegaciones | [01_BASICO.md#2-hawk](./01_BASICO.md#2-hawk) |
| **O365** | Unified Audit Logs | [01_BASICO.md#3-o365-extractor](./01_BASICO.md#3-o365-extractor) |

**Casos de Uso Típicos**:
- Investigación inicial de incidentes
- Detección de tokens comprometidos
- Auditoría de permisos OAuth
- Análisis de forwarding malicioso

---

### 🐕 RECONOCIMIENTO (3 herramientas)

Herramientas de mapeo y enumeración de infraestructura.

| Herramienta | Propósito | Documentación |
|-------------|----------|---------------|
| **AzureHound** | Attack paths con BloodHound | [02_RECONOCIMIENTO.md#1-azurehound](./02_RECONOCIMIENTO.md#1-azurehound) |
| **ROADtools** | Reconocimiento Azure AD | [02_RECONOCIMIENTO.md#2-roadtools](./02_RECONOCIMIENTO.md#2-roadtools) |
| **AADInternals** | Red Team Azure AD | [02_RECONOCIMIENTO.md#3-aadInternals](./02_RECONOCIMIENTO.md#3-aadinternals) |

**Casos de Uso Típicos**:
- Mapeo de infraestructura
- Identificación de activos críticos
- Análisis de relaciones de confianza
- Detección de misconfiguraciones

---

### 🐵 AUDITORÍA (3 herramientas)

Herramientas de evaluación de seguridad y compliance.

| Herramienta | Propósito | Documentación |
|-------------|----------|---------------|
| **Monkey365** | 300+ checks de seguridad | [03_AUDITORIA.md#1-monkey365](./03_AUDITORIA.md#1-monkey365) |
| **Maester** | Security testing framework | [03_AUDITORIA.md#2-maester](./03_AUDITORIA.md#2-maester) |
| **PnP PowerShell** | Auditoría de SharePoint/Teams | [03_AUDITORIA.md#3-pnp-powershell](./03_AUDITORIA.md#3-pnp-powershell) |

**Casos de Uso Típicos**:
- Auditoría de compliance
- Evaluación de configuración
- Testing de seguridad
- Generación de reportes

---

### 📧 FORENSE (3 herramientas + ML)

Herramientas de análisis forense e IR automatizada con ML.

| Herramienta | Propósito | Documentación |
|-------------|----------|---------------|
| **Graph API** | Extracción forense M365 | [04_FORENSE.md#1-microsoft-graph-api](./04_FORENSE.md#1-microsoft-graph-api) |
| **Cloud Katana** | IR automation + ML | [04_FORENSE.md#2-cloud-katana](./04_FORENSE.md#2-cloud-katana) |
| **Loki** | Escaneo de IOCs | [04_FORENSE.md#3-loki](./04_FORENSE.md#3-loki) |

**Casos de Uso Típicos**:
- Investigación forense completa
- Respuesta automática a incidentes
- Aprendizaje automático de amenazas
- Auto-corrección inteligente

---

## 🚀 Guías Prácticas

### Para Principiantes
1. Leer [QUICK_START.md](./guides/QUICK_START.md)
2. Ejecutar [INSTALLATION.md](./guides/INSTALLATION.md)
3. Configurar [SETUP_M365.md](./guides/SETUP_M365.md)

### Para Administradores
1. [INSTALLATION.md](./guides/INSTALLATION.md) - Instalación completa
2. [SETUP_M365.md](./guides/SETUP_M365.md) - Configuración de permisos
3. [TROUBLESHOOTING.md](./guides/TROUBLESHOOTING.md) - Solución de problemas

### Para Analistas de Seguridad
1. Cada categoría de tools (BÁSICO → RECONOCIMIENTO → AUDITORÍA → FORENSE)
2. [Playbooks](../playbooks/) según tipo de incidente
3. [API Documentation](./api/)

---

## 📊 Matriz de Selección de Herramientas

### Necesito detectar...

| Situación | Herramienta | Prioridad |
|-----------|-------------|----------|
| Tokens comprometidos | Sparrow | 🔴 CRÍTICA |
| Forwarding malicioso | Hawk | 🔴 CRÍTICA |
| Apps OAuth sospechosas | Sparrow | 🔴 CRÍTICA |
| Misconfiguraciones | Monkey365 | 🟠 ALTA |
| Attack paths | AzureHound | 🟠 ALTA |
| Enumeración de activos | ROADtools | 🟠 ALTA |
| Auditoría de compliance | Monkey365 | 🟡 MEDIA |
| Investigación forense | Graph API | 🔴 CRÍTICA |
| Respuesta automática | Cloud Katana | 🟠 ALTA |
| Malware en sistema | Loki | 🔴 CRÍTICA |

---

## 🔄 Flujos de Trabajo Recomendados

### Flujo 1: Respuesta a Incidente de Compromiso

```
1. BÁSICO
   ├─ Sparrow → Detectar tokens/apps maliciosas
   ├─ Hawk → Verificar reglas y delegaciones
   └─ O365 → Extraer logs iniciales

2. FORENSE
   ├─ Graph API → Análisis completo
   ├─ Loki → Escaneo de IOCs
   └─ Cloud Katana → Respuesta automática

3. AUDITORÍA
   └─ Monkey365 → Verificar configuración
```

### Flujo 2: Auditoría de Seguridad

```
1. AUDITORÍA
   ├─ Monkey365 → Escaneo rápido (300+ checks)
   ├─ Maester → Testing detallado
   └─ PnP → Auditoría granular

2. RECONOCIMIENTO
   ├─ AzureHound → Mapear infraestructura
   └─ ROADtools → Base de datos de análisis

3. BÁSICO
   └─ Sparrow/Hawk → Verificación final
```

### Flujo 3: Investigación Forense Completa

```
1. BÁSICO
   └─ O365 → Extracción inicial

2. FORENSE
   ├─ Graph API → Análisis completo
   ├─ Loki → Detección de IOCs
   └─ Cloud Katana → Correlación ML

3. RECONOCIMIENTO
   └─ AzureHound/ROADtools → Mapeo de impacto
```

---

## 📖 Documentación por Tema

### Análisis de Compromiso

- [Sparrow - Detección de OAuth](./01_BASICO.md#1-sparrow-365)
- [Hawk - Análisis de reglas](./01_BASICO.md#2-hawk)
- [Graph API - Extracción](./04_FORENSE.md#1-microsoft-graph-api)
- [Cloud Katana - Respuesta](./04_FORENSE.md#2-cloud-katana)

### Mapeo de Infraestructura

- [AzureHound - Attack Paths](./02_RECONOCIMIENTO.md#1-azurehound)
- [ROADtools - Database](./02_RECONOCIMIENTO.md#2-roadtools)
- [AADInternals - Enumeration](./02_RECONOCIMIENTO.md#3-aadinternals)

### Auditoría y Compliance

- [Monkey365 - Escaneo](./03_AUDITORIA.md#1-monkey365)
- [Maester - Testing](./03_AUDITORIA.md#2-maester)
- [PnP PowerShell - Custom Audits](./03_AUDITORIA.md#3-pnp-powershell)

### Análisis Forense

- [Graph API - Extracción](./04_FORENSE.md#1-microsoft-graph-api)
- [Loki - IOC Scanning](./04_FORENSE.md#3-loki)
- [Cloud Katana - Automatización](./04_FORENSE.md#2-cloud-katana)

---

## 🔐 Requisitos de Acceso

### Permisos Necesarios

| Herramienta | Permisos | Nivel |
|-------------|----------|-------|
| Sparrow | Tenant Admin | 🔴 Alto |
| Hawk | Exchange Admin | 🟠 Medio |
| O365 | Audit Admin | 🟠 Medio |
| AzureHound | Global Reader | 🟠 Medio |
| ROADtools | Tenant Reader | 🟠 Medio |
| AADInternals | Sin permisos | 🟢 Bajo |
| Monkey365 | Global Reader | 🟠 Medio |
| Maester | Tenant Admin | 🔴 Alto |
| Graph API | Variable | 🔴 Alto |
| Loki | Local admin | 🔴 Alto |

---

## 🚀 Inicio Rápido por Rol

### Security Analyst
1. Leer: [01_BASICO.md](./01_BASICO.md)
2. Aprender: [04_FORENSE.md](./04_FORENSE.md)
3. Practicar: [Playbooks](../playbooks/)

### System Administrator
1. Leer: [INSTALLATION.md](./guides/INSTALLATION.md)
2. Configurar: [SETUP_M365.md](./guides/SETUP_M365.md)
3. Monitorear: [03_AUDITORIA.md](./03_AUDITORIA.md)

### Incident Response Team
1. Leer: [QUICK_START.md](./guides/QUICK_START.md)
2. Estudiar: [Playbooks](../playbooks/)
3. Practicar: Flujo de trabajo completo

### Security Architect
1. Leer: [architecture/](./architecture/)
2. Integrar: [API Documentation](./api/)
3. Diseñar: Arquitectura personalizada

---

## 📋 Checklist de Documentación

- ✓ Documentación de herramientas completa
- ✓ Guides prácticas creadas
- ✓ Playbooks de respuesta
- ✓ Ejemplos de uso
- ✓ Troubleshooting
- ✓ Matriz de herramientas
- ✓ Flujos de trabajo
- ✓ Requisitos de acceso

---

## 🌐 MCP Servers Instalados

### Chrome DevTools MCP

| Aspecto | Detalle |
|---------|---------|
| **Versión** | 0.14.0 |
| **Paquete** | `chrome-devtools-mcp` |
| **Documentación** | [MCP_CHROME_DEVTOOLS.md](./MCP_CHROME_DEVTOOLS.md) |
| **Uso** | Automatización de Chrome, capturas, análisis de red |

**Herramientas disponibles**: click, fill, navigate, screenshot, network analysis, performance traces

---

## 🔗 Links Útiles

| Recurso | Descripción |
|---------|-------------|
| [GitHub](https://github.com) | Repositorios de tools |
| [Microsoft Docs](https://docs.microsoft.com) | Documentación oficial |
| [GitHub Issues](https://github.com) | Reporte de problemas |
| [Security Blog](https://techcommunity.microsoft.com) | Blog de seguridad |
| [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | MCP para Chrome |

---

## 💡 Tips de Navegación

- **Buscar por herramienta**: Ve a la sección 🦅🐕🐵📧
- **Buscar por tipo de análisis**: Ve a "Documentación por Tema"
- **Buscar por caso de uso**: Ve a "Flujos de Trabajo"
- **Buscar por rol**: Ve a "Inicio Rápido por Rol"

---

**Version**: 4.7  
**Status**: ✓ Completo  
**Última Actualización**: 2026-01-27  
**Total de Documentos**: 15+

