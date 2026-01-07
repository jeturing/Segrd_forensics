# 🚀 npm run dev - Guía de Inicio Rápido

## ✨ ¿Qué es?

`npm run dev` inicia **simultáneamente** la API backend y el frontend en un solo comando.

## 🎯 Comando

```bash
cd /home/hack/mcp-kali-forensics
npm run dev
```

## 📊 Qué se inicia

Cuando ejecutas `npm run dev`, ambos servicios se inician en paralelo:

| Servicio | URL | Puerto | Descripción |
|----------|-----|--------|-------------|
| **API Backend** | http://localhost:8080 | 8080 | FastAPI con Uvicorn |
| **Swagger Docs** | http://localhost:8080/docs | 8080 | Documentación interactiva |
| **Frontend React** | http://localhost:5173 | 5173 | Vite dev server |

## 🔍 Cómo funciona

```
npm run dev
  ├─→ concurrently ejecuta en paralelo:
  │   ├─→ npm run dev:api          (API en puerto 8080)
  │   └─→ npm run dev:frontend     (Frontend en puerto 5173)
  │
  └─→ Si presionas Ctrl+C, detiene AMBOS servicios
```

## 📝 Scripts disponibles

### Principal
```bash
# Inicia API + Frontend juntos (RECOMENDADO)
npm run dev
```

### Individuales
```bash
# Solo API backend (puerto 8080)
npm run dev:api

# Solo frontend (puerto 5173)
npm run dev:frontend
```

### Otros
```bash
# Build para producción
npm run build

# Preview de build
npm run preview

# Instalar dependencias de ambos
npm run install:all

# Linting
npm run lint
npm run lint:fix

# Formateo
npm run format

# Tests
npm run test
npm run test:ui
```

## ⚙️ Configuración

El archivo `package.json` en la raíz contiene:

```json
{
  "scripts": {
    "dev": "concurrently \"npm run dev:api\" \"npm run dev:frontend\" --kill-others-on-exit",
    "dev:api": "cd api && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080",
    "dev:frontend": "cd frontend-react && npm run dev"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
```

### Explicación

- **`concurrently`**: Ejecuta múltiples comandos en paralelo
- **`--kill-others-on-exit`**: Si un servicio falla, mata los demás
- **`--reload`**: El API se reinicia automáticamente al cambiar código
- **`--host 0.0.0.0`**: Accesible desde cualquier IP (no solo localhost)

## 🎯 Flujo de desarrollo típico

### 1️⃣ Inicia los servicios
```bash
npm run dev
```

Verás algo como:
```
> concurrently "npm run dev:api" "npm run dev:frontend" --kill-others-on-exit

[0] 
[0] INFO:     Uvicorn running on http://0.0.0.0:8080
[0] INFO:     Application startup complete
[1] 
[1]   VITE v5.0.0  ready in 234 ms
[1]   ➜  Local:   http://localhost:5173/
```

### 2️⃣ Abre dos navegadores
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8080/docs

### 3️⃣ Desarrolla
- Edita archivos en `api/` o `frontend-react/`
- Los cambios se cargan automáticamente (hot reload)
- Los errores aparecen en tiempo real

### 4️⃣ Detén cuando termines
```
Presiona Ctrl+C
```

Ambos servicios se detienen automáticamente.

## 🔧 Solución de problemas

### ❌ "Port 8080 already in use"

```bash
# Encuentra el proceso en el puerto 8080
lsof -i :8080

# Mata el proceso
kill -9 <PID>

# Intenta de nuevo
npm run dev
```

### ❌ "Port 5173 already in use"

```bash
# Encuentra el proceso en el puerto 5173
lsof -i :5173

# Mata el proceso
kill -9 <PID>

# Intenta de nuevo
npm run dev
```

### ❌ "Module not found" en frontend

```bash
# Instala dependencias del frontend
cd frontend-react && npm install
cd ..

# Intenta de nuevo
npm run dev
```

### ❌ "Python module not found"

```bash
# Activa el entorno virtual
source venv/bin/activate

# Intenta de nuevo
npm run dev
```

## 📊 Monitoreo

### Ver logs de API
Busca líneas que comiencen con `[0]` en la terminal

### Ver logs de Frontend
Busca líneas que comiencen con `[1]` en la terminal

### Ejemplo de salida
```
[0] INFO:     127.0.0.1:54321 - "GET /health HTTP/1.1" 200 OK
[1] [plugin:vite:import-analysis] Potential circular dependency: src/main.jsx
```

## 🚀 Producción

Para producción, no uses `npm run dev`. En su lugar:

```bash
# Build
npm run build

# Inicia API con gunicorn (en production)
gunicorn api.main:app --workers 4 --bind 0.0.0.0:8080

# Sirve frontend built files
# (Normalmente con nginx o similar)
```

## 📌 Notas importantes

- ✅ Los cambios en código se cargan automáticamente (hot reload)
- ✅ Los errores aparecen en tiempo real en la terminal
- ✅ Presionar Ctrl+C detiene AMBOS servicios
- ✅ No necesitas abrir dos terminales
- ⚠️ Usa esto solo para desarrollo, NO para producción
- ⚠️ Asegúrate de que puertos 8080 y 5173 están libres

## 📝 Próximos pasos

```bash
# 1. Inicia los servicios
npm run dev

# 2. Abre en navegador
# Frontend:  http://localhost:5173
# API Docs:  http://localhost:8080/docs

# 3. Comienza a desarrollar
# Edita archivos y verás cambios en tiempo real
```

---

**Versión**: 4.2  
**Última actualización**: Diciembre 2025  
**Estado**: ✅ Producción lista
