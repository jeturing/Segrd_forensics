# MCP Chrome DevTools - Guía de Instalación y Uso

> **Versión**: 0.14.0  
> **Fecha**: 2026-01-27  
> **Estado**: ✅ Instalado y Configurado

## 📋 Descripción

`chrome-devtools-mcp` es un servidor MCP (Model Context Protocol) que permite a tu agente de codificación (como Gemini, Claude, Cursor o Copilot) controlar e inspeccionar un navegador Chrome en vivo. Proporciona acceso completo al poder de Chrome DevTools para automatización confiable, debugging profundo y análisis de rendimiento.

## 🔧 Requisitos

- **Node.js**: v20.19 o superior (versión LTS)
- **Chrome**: Versión estable actual o más reciente
- **npm**: Incluido con Node.js

## 📦 Instalación

### Instalación Global (Recomendada)

```bash
npm install -g chrome-devtools-mcp@latest
```

### Uso con npx (Sin instalación)

```bash
npx chrome-devtools-mcp@latest
```

## ⚙️ Configuración para MCP Clients

### VS Code / Copilot

Añade la siguiente configuración a tu archivo `settings.json` o configuración de MCP:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

### Claude Desktop

Edita `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) o la ruta equivalente:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

### Cursor / Cline / Windsurf

Similar configuración en el archivo de configuración del cliente MCP correspondiente.

## 🛠️ Herramientas Disponibles

### Input Automation (8 herramientas)

| Herramienta | Descripción |
|-------------|-------------|
| `click` | Hacer clic en elementos |
| `drag` | Arrastrar elementos |
| `fill` | Rellenar campos de texto |
| `fill_form` | Rellenar formularios completos |
| `handle_dialog` | Manejar diálogos del navegador |
| `hover` | Pasar el mouse sobre elementos |
| `press_key` | Presionar teclas |
| `upload_file` | Subir archivos |

### Navigation Automation (6 herramientas)

| Herramienta | Descripción |
|-------------|-------------|
| `close_page` | Cerrar pestañas |
| `list_pages` | Listar pestañas abiertas |
| `navigate_page` | Navegar a URLs |
| `new_page` | Abrir nueva pestaña |
| `select_page` | Seleccionar pestaña activa |
| `wait_for` | Esperar elementos/condiciones |

### Emulation (2 herramientas)

| Herramienta | Descripción |
|-------------|-------------|
| `emulate` | Emular dispositivos móviles |
| `resize_page` | Redimensionar viewport |

### Performance (3 herramientas)

| Herramienta | Descripción |
|-------------|-------------|
| `performance_analyze_insight` | Analizar insights de rendimiento |
| `performance_start_trace` | Iniciar trace de rendimiento |
| `performance_stop_trace` | Detener trace de rendimiento |

### Network (2 herramientas)

| Herramienta | Descripción |
|-------------|-------------|
| `get_network_request` | Obtener detalles de petición |
| `list_network_requests` | Listar peticiones de red |

### Debugging (5 herramientas)

| Herramienta | Descripción |
|-------------|-------------|
| `evaluate_script` | Ejecutar JavaScript |
| `get_console_message` | Obtener mensaje de consola |
| `list_console_messages` | Listar mensajes de consola |
| `take_screenshot` | Capturar pantalla |
| `take_snapshot` | Tomar snapshot del DOM |

## 🚀 Uso Básico

### Primer Prompt de Prueba

Ingresa el siguiente prompt en tu cliente MCP para verificar que todo funciona:

```
Check the performance of https://developers.chrome.com
```

El cliente MCP debería abrir el navegador y grabar un trace de rendimiento.

### Ejemplos de Prompts

```
# Navegar y tomar screenshot
Navigate to https://segrd.com and take a screenshot

# Análisis de rendimiento
Analyze the performance of https://example.com

# Debugging
Open https://myapp.com, check for console errors and network failures

# Formularios
Go to the login page and fill in the credentials

# Inspección de red
List all API calls made when loading the dashboard
```

## ⚡ Opciones de Configuración

### Opciones CLI

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--headless` | Modo sin interfaz gráfica | `false` |
| `--isolated` | Usar directorio temporal (se limpia al cerrar) | `false` |
| `--channel` | Canal de Chrome (stable, beta, canary, dev) | `stable` |
| `--viewport` | Tamaño inicial del viewport (ej: 1280x720) | Auto |
| `--browserUrl` | Conectar a Chrome existente | - |
| `--wsEndpoint` | WebSocket endpoint para conexión | - |
| `--proxyServer` | Configuración de proxy | - |
| `--acceptInsecureCerts` | Ignorar errores de certificado | `false` |
| `--logFile` | Archivo para logs de debug | - |
| `--userDataDir` | Directorio de datos de usuario | `~/.cache/chrome-devtools-mcp/` |

### Configuración Headless (Sin UI)

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--headless=true",
        "--isolated=true"
      ]
    }
  }
}
```

### Conectar a Chrome Existente

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--browser-url=http://127.0.0.1:9222"
      ]
    }
  }
}
```

Para iniciar Chrome con debugging habilitado:

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-profile

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%TEMP%\chrome-profile"
```

### Conexión Automática (Chrome 144+)

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest", "--autoConnect"]
    }
  }
}
```

Requiere habilitar remote debugging en Chrome:
1. Navega a `chrome://inspect/#remote-debugging`
2. Sigue el diálogo para permitir conexiones de debugging

## 🔒 Seguridad

⚠️ **Advertencias importantes:**

1. `chrome-devtools-mcp` expone el contenido del navegador a los clientes MCP, permitiéndoles inspeccionar, debuggear y modificar cualquier dato.

2. **Evita** compartir información sensible o personal que no quieras exponer a los clientes MCP.

3. Cuando uses `--remote-debugging-port`, cualquier aplicación en tu máquina puede conectarse y controlar el navegador.

4. Usa `--isolated=true` para sesiones temporales que se limpian automáticamente.

## 🐛 Troubleshooting

### El navegador no inicia

```bash
# Verificar que Chrome esté instalado
which google-chrome || which chromium-browser

# Probar con logs verbose
DEBUG=* npx chrome-devtools-mcp@latest --logFile=/tmp/mcp-debug.log
```

### Errores de permisos (Sandbox)

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--chrome-arg=--no-sandbox",
        "--chrome-arg=--disable-setuid-sandbox"
      ]
    }
  }
}
```

### Conexión a VM/Remoto

Si hay problemas de port forwarding entre VM y host, consulta la [documentación de troubleshooting](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/HEAD/docs/troubleshooting.md).

## 📚 Recursos

- **NPM**: https://www.npmjs.com/package/chrome-devtools-mcp
- **GitHub**: https://github.com/ChromeDevTools/chrome-devtools-mcp
- **Tool Reference**: https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/HEAD/docs/tool-reference.md
- **Changelog**: https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/HEAD/CHANGELOG.md
- **Troubleshooting**: https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/HEAD/docs/troubleshooting.md

## 📝 Directorio de Datos

Por defecto, `chrome-devtools-mcp` usa:

- **Linux/macOS**: `$HOME/.cache/chrome-devtools-mcp/chrome-profile-$CHANNEL`
- **Windows**: `%HOMEPATH%/.cache/chrome-devtools-mcp/chrome-profile-$CHANNEL`

Este directorio **no se limpia** entre ejecuciones a menos que uses `--isolated=true`.

---

## 🎯 Integración con SEGRD Forensics

### Casos de Uso en Forensics

1. **Web Scraping Forense**: Capturar evidencia de páginas web sospechosas
2. **Análisis de Phishing**: Inspeccionar sitios de phishing de forma segura
3. **Capturas de Evidencia**: Screenshots automatizados con timestamps
4. **Análisis de Red**: Monitorear tráfico de red de sitios maliciosos
5. **Extracción de IOCs**: Obtener indicadores de compromiso de páginas web

### Ejemplo de Uso Forense

```
Navigate to the suspected phishing URL https://suspicious-site.com, 
take a full-page screenshot, list all network requests, 
and extract any JavaScript that loads external resources
```

---

*Documentación generada para MCP Kali Forensics v4.7 - 2026-01-27*
