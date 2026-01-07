# 📚 GUÍA DE GESTIÓN DE DOCUMENTACIÓN - MCP Kali Forensics v4.2

## Estructura de Carpetas de Documentación

```
docs/
├── README.md                           ← Índice maestro (START HERE!)
├── getting-started/                    ← Para principiantes
│   ├── QUICKSTART.md
│   ├── INSTALLATION.md
│   ├── FIRST_STEPS.md
│   └── COMMON_ISSUES.md
├── installation/                       ← Guías de instalación
│   ├── NATIVE_INSTALLATION.md
│   ├── DOCKER_INSTALLATION.md
│   ├── REQUIREMENTS.md
│   └── TROUBLESHOOTING.md
├── backend/                            ← Documentación del backend
│   ├── API.md
│   ├── ENDPOINTS.md
│   ├── CONFIGURATION.md
│   ├── DATABASE.md
│   └── TOOLS.md
├── frontend/                           ← Documentación del frontend
│   ├── REACT_SETUP.md
│   ├── COMPONENTS.md
│   ├── DASHBOARD.md
│   └── THEMING.md
├── architecture/                       ← Arquitectura general
│   ├── OVERVIEW.md
│   ├── SYSTEM_DESIGN.md
│   ├── DATA_FLOW.md
│   └── SECURITY.md
├── security/                           ← Seguridad y autenticación
│   ├── OAUTH.md
│   ├── API_SECURITY.md
│   ├── CREDENTIALS.md
│   └── BEST_PRACTICES.md
├── deployment/                         ← Despliegue en producción
│   ├── DOCKER_COMPOSE.md
│   ├── KUBERNETES.md
│   ├── MONITORING.md
│   └── BACKUP.md
├── reference/                          ← Referencia técnica
│   ├── GLOSSARY.md
│   ├── TROUBLESHOOTING.md
│   ├── FAQ.md
│   └── CHANGELOG.md
├── agents/                             ← Documentación de agentes
│   ├── OVERVIEW.md
│   ├── BLUE_AGENT.md
│   ├── RED_AGENT.md
│   └── PURPLE_AGENT.md
├── playbooks/                          ← Playbooks SOAR
│   ├── OVERVIEW.md
│   ├── ACCOUNT_COMPROMISE.md
│   ├── DATA_EXFILTRATION.md
│   └── MALWARE_RESPONSE.md
└── tools/                              ← Referencia de herramientas
    ├── INDEX.md
    ├── 01_BASICO.md
    ├── 02_RECONOCIMIENTO.md
    ├── 03_AUDITORIA.md
    └── 04_FORENSE.md
```

---

## 📋 Estructura Recomendada por Tipo de Contenido

### Para el Usuario Final
1. Empezar en `getting-started/QUICKSTART.md`
2. Ir a `getting-started/INSTALLATION.md` si necesita instalar
3. Consultar `reference/FAQ.md` para preguntas comunes

### Para Desarrolladores
1. Leer `architecture/OVERVIEW.md` primero
2. Explorar `backend/API.md` para endpoints
3. Ir a `frontend/REACT_SETUP.md` si trabaja con React
4. Consultar `deployment/` para producción

### Para Administradores
1. Leer `installation/REQUIREMENTS.md`
2. Seguir `installation/NATIVE_INSTALLATION.md` o `DOCKER_INSTALLATION.md`
3. Configurar según `backend/CONFIGURATION.md`
4. Implementar `security/BEST_PRACTICES.md`

---

## 🎯 Reglas de Gestión de Documentación

### ✅ HACER

1. **Mantener la raíz limpia**
   - Solo `README.md` y `CHANGELOG.md` en la raíz
   - Todo lo demás en `docs/`

2. **Usar nombres descriptivos**
   - ✅ `QUICKSTART.md`
   - ❌ `quick.md`
   - ✅ `OAUTH_AUTHENTICATION.md`
   - ❌ `oauth.md`

3. **Crear un índice en cada carpeta**
   - Incluir `README.md` o nombre del tipo en cada carpeta
   - Listar archivos y contenidos

4. **Mantener archivos actualizados**
   - Si actualizas código, actualiza docs
   - Incluir `Last Updated: YYYY-MM-DD` en archivos críticos

5. **Usar estructura de encabezados**
   ```markdown
   # Título principal
   ## Sección principal
   ### Subsección
   #### Detalles
   ```

6. **Incluir ejemplos prácticos**
   - Comandos reales que funcionan
   - Capturas de pantalla cuando sea apropiado
   - Archivos de ejemplo completos

7. **Referenciar otros documentos**
   ```markdown
   Para más información, ver [Backend API](../backend/API.md)
   ```

### ❌ NO HACER

1. **No dejar archivos .md sueltos en la raíz**
   - ❌ `RANDOM_FEATURE.md` en raíz
   - ✅ `docs/backend/RANDOM_FEATURE.md`

2. **No duplicar contenido**
   - Si la info existe en otro doc, hacer referencia
   - Mantener una única fuente de verdad

3. **No archivos sin propósito claro**
   - Cada archivo debe tener objetivo específico
   - Si no se usa, eliminar o archivar

4. **No cambiar la estructura sin avisar**
   - Si mueves archivos, actualizar todas las referencias
   - Documentar cambios en CHANGELOG.md

5. **No información sensible**
   - Nunca commitar API keys, tokens, contraseñas
   - Usar ejemplos genéricos

---

## 📝 Template para Nuevos Documentos

```markdown
# Título del Documento

**Autor:** Nombre  
**Fecha:** YYYY-MM-DD  
**Última Actualización:** YYYY-MM-DD  
**Versión:** 1.0  
**Estado:** ✅ Actualizado / 🔄 En Progreso / ⚠️ Obsoleto

## Descripción

Explicación breve de qué trata este documento.

## Requisitos Previos

- Requisito 1
- Requisito 2
- Ver también: [Documento Relacionado](../path/to/doc.md)

## Contenido Principal

### Sección 1
Contenido aquí...

### Sección 2
Contenido aquí...

## Ejemplos Prácticos

```bash
# Ejemplo de comando
command --flag value
```

## Troubleshooting

### Problema 1
Solución...

### Problema 2
Solución...

## Referencias

- [Link Interno](../path/doc.md)
- [Link Externo](https://example.com)

## Ver También

- Documento relacionado 1
- Documento relacionado 2

---
**Last Updated:** YYYY-MM-DD
```

---

## 🔄 Workflow de Actualización de Documentación

### Cuando Agregas una Nueva Característica

1. **Crear documento** en carpeta apropiada
   ```bash
   touch docs/backend/NEW_FEATURE.md
   ```

2. **Escribir documentación** siguiendo template
   - Descripción clara
   - Ejemplos prácticos
   - Casos de uso

3. **Actualizar índices** en carpetas padre
   - Agregar referencia en `README.md` local
   - Actualizar tabla de contenidos

4. **Actualizar referencia** en `docs/README.md`
   - Agregar link en sección apropiada

5. **Documenta en CHANGELOG.md**
   ```markdown
   ## [Unreleased]
   ### Added
   - New feature: XYZ (see `docs/backend/NEW_FEATURE.md`)
   ```

### Cuando Modificas Documentación Existente

1. **Actualizar archivo** con cambios
2. **Cambiar fecha** "Last Updated"
3. **Cambiar versión** si es cambio significativo
4. **Actualizar CHANGELOG.md**
   ```markdown
   ### Changed
   - Updated: Feature XYZ documentation
   ```

### Cuando Eliminas Documentación

1. **NO eliminar directamente**
2. **Archivar** en `docs/archive/`
3. **Documentar** por qué se archivó
4. **Actualizar CHANGELOG.md**
   ```markdown
   ### Removed
   - Archived: Deprecated feature documentation
   ```

---

## 🏷️ Etiquetas de Estado

Usar estas etiquetas al inicio de documentos críticos:

```markdown
**Estado:** 
- ✅ Actualizado (coincide con versión actual)
- 🔄 En Progreso (trabajo en marcha)
- ⚠️ Obsoleto (información desactualizada)
- 🔒 Archivado (referencia histórica)
```

---

## 📊 Checklist para Docs Completas

Antes de considerar un documento "completo":

- [ ] Título claro y descriptivo
- [ ] Descripción de propósito
- [ ] Requisitos previos listados
- [ ] Instrucciones paso a paso (si aplica)
- [ ] Al menos 1 ejemplo práctico
- [ ] Sección de troubleshooting
- [ ] Enlaces a documentos relacionados
- [ ] Fecha de última actualización
- [ ] Estado documentado (✅, 🔄, ⚠️, 🔒)
- [ ] Revisado por al menos otra persona

---

## 🚀 Cómo Navegar la Documentación

### Nuevo en el Proyecto?
```
START → docs/README.md
     → docs/getting-started/QUICKSTART.md
     → docs/getting-started/INSTALLATION.md
     → docs/architecture/OVERVIEW.md
```

### Necesito Instalar?
```
START → docs/getting-started/INSTALLATION.md
     → docs/installation/REQUIREMENTS.md
     → docs/installation/NATIVE_INSTALLATION.md (o DOCKER_INSTALLATION.md)
     → docs/installation/TROUBLESHOOTING.md
```

### Necesito Deployar?
```
START → docs/deployment/DOCKER_COMPOSE.md
     → docs/deployment/MONITORING.md
     → docs/security/BEST_PRACTICES.md
     → docs/deployment/BACKUP.md
```

### Busco Referencia API?
```
START → docs/backend/API.md
     → docs/backend/ENDPOINTS.md
     → docs/reference/TROUBLESHOOTING.md
```

---

## 📖 Herramientas Recomendadas

Para editar y mantener documentación:

- **Editor**: VS Code + Markdown Preview
- **Linter**: `markdownlint` para consistencia
- **Generador de TOC**: `markdown-toc`
- **Validador de links**: `markdown-link-check`

### Instalar herramientas

```bash
npm install -g markdownlint-cli
npm install -g markdown-toc
npm install -g markdown-link-check
```

### Usar herramientas

```bash
# Verificar sintaxis Markdown
markdownlint docs/**/*.md

# Generar tabla de contenidos (en un archivo)
markdown-toc -i docs/README.md

# Verificar links
markdown-link-check docs/**/*.md
```

---

## 🎯 Objetivos de Esta Estructura

✅ **Organización Clara** - Fácil encontrar información  
✅ **Escalabilidad** - Crecer sin desorden  
✅ **Mantenibilidad** - Actualizaciones organizadas  
✅ **Accesibilidad** - Para todos: usuarios, devs, admins  
✅ **Consistencia** - Mismo estilo y estructura  

---

## 📞 Preguntas Frecuentes sobre Gestión de Docs

**P: ¿Dónde coloco un documento nuevo?**  
R: Determina su categoría (backend, frontend, arquitectura, etc.) y colócalo en la carpeta correspondiente.

**P: ¿Puedo tener subcarpetas dentro de carpetas?**  
R: Sí, pero mantén máximo 2 niveles. Más puede ser confuso.

**P: ¿Qué hago con documentos antiguos?**  
R: Archívalos en `docs/archive/` con una nota explicativa.

**P: ¿Debo actualizar links si cambio estructura?**  
R: Sí, actualiza todos los links que referencias ese documento.

**P: ¿Puedo usar archivos README.md en subcarpetas?**  
R: Sí, es buena práctica tener un README en cada carpeta.

---

## 🔗 Flujo de Referencias

Los documentos deben referenciar así:

```markdown
<!-- Referencia relativa (recomendado) -->
Para más info, ver [Backend API](../backend/API.md)

<!-- O usar alias -->
Para más info, consulta la [documentación de tools](../tools/INDEX.md)
```

---

**Versión**: 1.0  
**Fecha Creación**: 7 Diciembre 2025  
**Responsable**: GitHub Copilot Assistant  
**Estado**: ✅ Actualizado

---

## Próximos Pasos

1. Revisar esta guía antes de agregar documentación nueva
2. Usar templates para mantener consistencia
3. Seguir workflow de actualización
4. Mantener índices actualizados
5. Realizar auditoría mensual de documentación

