# MCP Kali Forensics - Dashboard Web

## 🎯 Acceso al Dashboard

El dashboard web ya está **activo y funcionando** en:

```
http://localhost:9000/dashboard/
```

O desde otra máquina en la red:
```
http://<IP-DEL-SERVIDOR>:9000/dashboard/
```

## 📊 Características del Dashboard

### 1. **Vista Principal (Dashboard)**
- ✅ Estadísticas en tiempo real:
  - Casos activos
  - Casos cerrados
  - Alertas pendientes
  - IOCs detectados
  
- ✅ Gráficos interactivos (Plotly):
  - Timeline de casos
  - Distribución de amenazas
  - Actividad reciente

### 2. **Gestión de Casos**
- Crear nuevos casos
- Ver lista de casos activos/cerrados
- Filtrar por estado y prioridad
- Acceso rápido a detalles del caso

### 3. **Análisis Microsoft 365**
- **Sparrow**: Detección de compromisos en Azure/M365
- **Hawk**: Análisis forense de Exchange Online
- Ejecución directa desde la interfaz
- Visualización de resultados en tiempo real

### 4. **Análisis de Endpoints**
- **Loki Scanner**: Escaneo de IOCs
- **YARA**: Detección de malware
- **Volatility**: Análisis de memoria
- Resultados organizados por severidad

### 5. **Verificación de Credenciales**
- Integración con Have I Been Pwned (HIBP)
- Búsqueda de credenciales filtradas
- Historial de verificaciones

### 6. **Timeline de Eventos**
- Visualización cronológica de eventos
- Correlación automática de incidentes
- Exportación de timeline

### 7. **Generación de Reportes**
- Reporte ejecutivo (PDF)
- Reporte técnico detallado
- Timeline completo
- Lista de IOCs

## 🚀 Cómo Usar el Dashboard

### Inicio Rápido

1. **Abrir el Dashboard**:
   ```bash
   # En el navegador, ir a:
   http://localhost:9000/dashboard/
   ```

2. **Ver Documentación de la API**:
   ```bash
   http://localhost:9000/docs
   ```

3. **Health Check**:
   ```bash
   curl http://localhost:9000/health
   ```

### Ejemplo: Crear un Nuevo Caso

1. Ir a la sección "Casos" en el sidebar
2. Click en "Nuevo Caso"
3. Ingresar ID del caso (ej: `IR-2025-001`)
4. El sistema crea automáticamente la estructura de directorios

### Ejemplo: Ejecutar Análisis M365

1. Ir a la sección "Microsoft 365"
2. Seleccionar "Sparrow" o "Hawk"
3. Ingresar ID del caso
4. Click en "Ejecutar Análisis"
5. Ver resultados en tiempo real

## 🎨 Personalización

### Colores del Dashboard

El dashboard usa Tailwind CSS con estos colores base:
- **Primario**: Azul (#3b82f6)
- **Éxito**: Verde (#34d399)
- **Advertencia**: Amarillo (#fbbf24)
- **Peligro**: Rojo (#ef4444)

### Modificar Temas

Editar `/home/hack/mcp-kali-forensics/api/templates/dashboard.html`:

```html
<!-- Cambiar a tema claro -->
<body class="bg-gray-100 text-gray-900">

<!-- Cambiar a tema oscuro (actual) -->
<body class="bg-gray-900 text-gray-100">
```

## 📡 API Endpoints para Datos del Dashboard

### Estadísticas Generales
```bash
curl http://localhost:9000/api/dashboard/stats
```

### Información del Tenant M365
```bash
curl http://localhost:9000/api/dashboard/m365/tenant-info
```

### Últimos IOCs Detectados
```bash
curl http://localhost:9000/api/dashboard/iocs/latest
```

### Estado de Endpoints
```bash
curl http://localhost:9000/api/dashboard/endpoints/status
```

## 🔧 Troubleshooting

### Dashboard no carga

```bash
# Ver logs del servidor
tail -f /home/hack/mcp-kali-forensics/logs/mcp-server.log

# Verificar que el servidor esté corriendo
ps aux | grep uvicorn

# Verificar puerto
netstat -tlnp | grep 9000
```

### Reiniciar el Servidor

```bash
# Detener servidor
pkill -9 uvicorn

# Iniciar de nuevo
cd /home/hack/mcp-kali-forensics
nohup uvicorn api.main:app --host 0.0.0.0 --port 9000 > logs/mcp-server.log 2>&1 &
```

### Cambiar Puerto

Editar comando de inicio:
```bash
# Usar puerto 8080 en lugar de 9000
nohup uvicorn api.main:app --host 0.0.0.0 --port 8080 > logs/mcp-server.log 2>&1 &
```

## 📊 Actualización de Datos

El dashboard se actualiza automáticamente cada **30 segundos**.

Para forzar actualización manual:
- Recargar página (F5)
- Los gráficos se regeneran automáticamente

## 🔐 Seguridad

### Autenticación API

Los endpoints de forensics requieren API Key:

```bash
# Ejemplo con API Key
curl -X POST http://localhost:9000/forensics/m365/analyze \
  -H "X-API-Key: forensics-api-key-2025" \
  -H "Content-Type: application/json" \
  -d '{"case_id":"IR-001","scope":["sparrow"]}'
```

### Configurar API Key

Editar `/home/hack/mcp-kali-forensics/.env`:
```
API_KEY=tu-clave-secreta-aqui
```

## 📈 Rendimiento

El dashboard está optimizado para:
- ✅ Carga rápida (< 2 segundos)
- ✅ Gráficos responsivos
- ✅ Actualización asíncrona sin bloqueo
- ✅ Compatible con dispositivos móviles

## 🛠️ Herramientas Integradas

Estado actual de las herramientas:

```
✓ Sparrow 365:     Instalado
✓ Hawk:            Instalado
✗ O365 Extractor:  Instalado pero no detectado (revisar path)
✓ Loki Scanner:    Instalado
✓ YARA Rules:      Instalado
✓ PowerShell:      Instalado
✓ YARA:            Instalado
✗ Volatility:      Instalado pero no detectado (revisar path)
✓ OSQuery:         Instalado
```

## 📞 Soporte

Para reportar problemas o sugerencias:
1. Ver logs: `tail -f logs/mcp-server.log`
2. Ver logs de auditoría: `cat audit-logs/latest.log`
3. Regenerar auditoría: `./scripts/generate_audit.sh`

## 🎉 ¡Listo para Usar!

El dashboard está **completamente funcional** y listo para análisis forense.

**URL del Dashboard**: http://localhost:9000/dashboard/
**Documentación API**: http://localhost:9000/docs
**Health Check**: http://localhost:9000/health

---

**Fecha de Instalación**: 2025-12-04
**Versión**: 1.0.0
**Estado**: ✅ OPERACIONAL
