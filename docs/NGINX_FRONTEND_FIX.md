# 🔧 Solución: "Welcome to nginx!" - Configuración Frontend

**Problema**: Al acceder a `http://localhost` ves la página por defecto de nginx en lugar de la aplicación React.

**Causa**: Nginx no está configurado para servir el frontend React compilado.

---

## ✅ Solución Rápida

### Paso 1: Build del Frontend
```bash
cd /Users/owner/Desktop/jcore
./scripts/deploy_frontend.sh
```

Este script automáticamente:
1. Compila el frontend React (`npm run build`)
2. Copia los archivos a `nginx/html/`
3. Reinicia los contenedores Docker
4. Verifica que todo funcione

### Paso 2: Verificar Acceso
```bash
# Frontend
curl http://localhost/

# API
curl http://localhost/api/health

# Docs
open http://localhost/docs
```

---

## 📝 Solución Manual (Si el Script Falla)

### 1. Compilar Frontend
```bash
cd frontend-react
npm install
npm run build
```

### 2. Copiar al Nginx
```bash
mkdir -p nginx/html
cp -r frontend-react/build/* nginx/html/
```

### 3. Verificar Archivos
```bash
ls -la nginx/html/
# Debe contener: index.html, static/, asset-manifest.json, etc.
```

### 4. Reiniciar Nginx
```bash
docker-compose restart nginx
# O si no está corriendo:
docker-compose up -d nginx
```

### 5. Ver Logs (Si Hay Errores)
```bash
docker-compose logs -f nginx
```

---

## 🏗️ Arquitectura Actualizada

```
┌─────────────────────────────────────────┐
│   Browser: http://localhost/           │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│         Nginx (Port 80)                 │
│  ┌─────────────────────────────────┐   │
│  │ / → /usr/share/nginx/html       │   │ (Frontend React)
│  │ /api → mcp-forensics-api:8888   │   │ (Backend Proxy)
│  │ /docs → mcp-forensics-api:8888  │   │ (Swagger Docs)
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
           │                    │
           │                    │
    ┌──────▼────────┐   ┌───────▼──────┐
    │ Frontend      │   │ Backend API  │
    │ React Build   │   │ FastAPI:8888 │
    │ (Static)      │   │              │
    └───────────────┘   └──────────────┘
```

---

## 📋 Archivos Modificados

### 1. `/nginx/conf.d/default.conf`
```nginx
server {
    listen 80 default_server;
    server_name localhost;

    # Servir frontend React
    root /usr/share/nginx/html;
    index index.html;

    # React Router - todas las rutas van a index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api {
        proxy_pass http://mcp_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

### 2. `/docker-compose.yml`
```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: mcp-forensics-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/html:/usr/share/nginx/html:ro
    networks:
      - forensics-net
```

---

## 🧪 Testing

### Test 1: Verificar que Nginx Está Corriendo
```bash
docker ps | grep nginx
# Debe mostrar: mcp-forensics-nginx
```

### Test 2: Verificar Archivos HTML
```bash
docker exec mcp-forensics-nginx ls /usr/share/nginx/html
# Debe mostrar: index.html, static/, etc.
```

### Test 3: Verificar Configuración Nginx
```bash
docker exec mcp-forensics-nginx nginx -t
# Debe retornar: syntax is ok
```

### Test 4: Acceso desde Navegador
```bash
# Abrir en navegador
open http://localhost/

# Debe cargar la aplicación React, no "Welcome to nginx!"
```

---

## 🐛 Troubleshooting

### Problema: Sigue mostrando "Welcome to nginx!"

**Solución 1**: Verificar que se copiaron los archivos
```bash
docker exec mcp-forensics-nginx cat /usr/share/nginx/html/index.html
# Si muestra contenido de nginx, los archivos no se copiaron
```

**Solución 2**: Rebuild y restart completo
```bash
./scripts/deploy_frontend.sh
docker-compose down
docker-compose up -d
```

---

### Problema: Error 404 en rutas de React Router

**Causa**: Falta configuración de `try_files`

**Solución**: Verificar en `/nginx/conf.d/default.conf`:
```nginx
location / {
    try_files $uri $uri/ /index.html;  # ← Esta línea es crítica
}
```

---

### Problema: API no responde (502 Bad Gateway)

**Causa**: Backend no está corriendo o no está en la red correcta

**Solución**:
```bash
# Verificar backend
docker ps | grep mcp-forensics-api

# Verificar red
docker network inspect jcore_forensics-net

# Restart backend
docker-compose restart mcp-forensics-api
```

---

### Problema: Frontend carga pero API falla (CORS)

**Causa**: Variables de entorno incorrectas en frontend

**Solución**: Verificar `.env` en `frontend-react/`:
```bash
VITE_API_BASE_URL=http://localhost
VITE_API_KEY=mcp-forensics-dev-key
```

Rebuild:
```bash
cd frontend-react
npm run build
cd ..
./scripts/deploy_frontend.sh
```

---

## 📚 Próximos Pasos

Una vez que el frontend esté funcionando:

1. **Integrar Onboarding con Stripe**
   - Ver: `/docs/v4.6/STRIPE_ONBOARDING_PLAN.md`
   - Implementar endpoints de registro
   - Configurar webhooks de Stripe

2. **Añadir Gestión de Agentes LLM al UI**
   - Ver: `/docs/v4.6/LLM_AGENT_MANAGEMENT.md`
   - Integrar componentes React en rutas
   - Probar creación de agentes desde UI

3. **Configurar SSL/TLS (Producción)**
   ```bash
   # Usar Let's Encrypt
   docker-compose exec nginx certbot --nginx
   ```

---

## ✅ Checklist

- [ ] Frontend React compilado (`npm run build`)
- [ ] Archivos en `nginx/html/` (verificado)
- [ ] Docker Compose actualizado con servicio nginx
- [ ] Nginx configurado para servir frontend
- [ ] Contenedor nginx corriendo
- [ ] Frontend accesible en `http://localhost/`
- [ ] API accesible en `http://localhost/api/`
- [ ] React Router funcionando (todas las rutas)
- [ ] API Key configurada en frontend

---

**Fecha**: 29 de Diciembre de 2025  
**Versión**: 4.6.0  
**Estado**: ✅ Resuelto
