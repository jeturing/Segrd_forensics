# 🚀 ACCIÓN INMEDIATA: Resolver "Welcome to nginx!"

**Fecha**: 29 de Diciembre de 2025  
**Tiempo estimado**: 10 minutos  
**Estado**: ⚡ EJECUTAR AHORA

---

## 📋 Paso a Paso

### 1. Abrir Terminal
```bash
# En tu Mac, abrir Terminal y navegar al proyecto
cd /Users/owner/Desktop/jcore
```

### 2. Ejecutar Script de Deployment
```bash
# Este script hace TODO automáticamente:
# - Compila React
# - Copia archivos a nginx
# - Reinicia contenedores
./scripts/deploy_frontend.sh
```

**Output esperado**:
```
🚀 Deployment MCP Forensics v4.6 - Frontend + Nginx
====================================================
📁 Creando directorio nginx/html...
🔨 Compilando frontend React...
📦 Instalando dependencias npm... (si es necesario)
⚙️  Ejecutando build de producción...
✅ Build completado exitosamente
📋 Copiando archivos a nginx/html...
✅ Archivos copiados correctamente
¿Reiniciar contenedores de Docker? (y/n): y
🔄 Reiniciando contenedores...
✅ Contenedores reiniciados
✅ Frontend accesible en http://localhost/
✅ API accesible en http://localhost/api/
====================================================
✅ Deployment completado!
```

### 3. Verificar en Navegador
```bash
# Abrir la aplicación
open http://localhost/
```

**Resultado esperado**: 
- ✅ Ves la aplicación React (MCP Forensics Dashboard)
- ❌ NO ves "Welcome to nginx!"

---

## 🐛 Si Algo Sale Mal

### Problema 1: Script no ejecuta
```bash
# Hacer el script ejecutable
chmod +x ./scripts/deploy_frontend.sh

# Intentar de nuevo
./scripts/deploy_frontend.sh
```

### Problema 2: Frontend no compila
```bash
# Instalar dependencias manualmente
cd frontend-react
npm install
npm run build

# Copiar archivos manualmente
cd ..
mkdir -p nginx/html
cp -r frontend-react/build/* nginx/html/

# Reiniciar nginx
docker-compose restart nginx
```

### Problema 3: Docker no está corriendo
```bash
# Iniciar Docker Desktop (Mac)
open -a Docker

# Esperar 30 segundos
sleep 30

# Intentar de nuevo
./scripts/deploy_frontend.sh
```

### Problema 4: Sigue mostrando "Welcome to nginx!"
```bash
# Hard reset de nginx
docker-compose stop nginx
docker-compose rm -f nginx
docker-compose up -d nginx

# Esperar 10 segundos
sleep 10

# Verificar
curl http://localhost/
```

---

## ✅ Verificación Final

### Test 1: Frontend
```bash
curl -s http://localhost/ | grep -q "<!doctype html>" && echo "✅ Frontend OK" || echo "❌ Frontend FAIL"
```

### Test 2: API
```bash
curl -s http://localhost/api/health | grep -q "healthy" && echo "✅ API OK" || echo "❌ API FAIL"
```

### Test 3: Docs
```bash
curl -s http://localhost/docs | grep -q "FastAPI" && echo "✅ Docs OK" || echo "❌ Docs FAIL"
```

**Todos deben mostrar ✅ OK**

---

## 📞 Soporte

Si después de estos pasos TODAVÍA ves "Welcome to nginx!":

1. **Ver logs de nginx**:
   ```bash
   docker-compose logs -f nginx
   ```

2. **Ver logs del backend**:
   ```bash
   docker-compose logs -f mcp-forensics-api
   ```

3. **Ver configuración actual**:
   ```bash
   docker exec mcp-forensics-nginx cat /etc/nginx/conf.d/default.conf
   ```

4. **Ver archivos en nginx**:
   ```bash
   docker exec mcp-forensics-nginx ls -la /usr/share/nginx/html/
   ```

5. **Revisar documentación completa**:
   - `/docs/NGINX_FRONTEND_FIX.md` - Troubleshooting detallado
   - `/docs/v4.6/IMPLEMENTATION_SUMMARY_COMPLETE.md` - Resumen completo

---

## 🎯 Después de Resolver

Una vez que el frontend esté funcionando:

### Explorar la Aplicación
```bash
# Dashboard principal
open http://localhost/

# Gestión de Agentes LLM
open http://localhost/admin/llm-agents

# Gestión de Tenants
open http://localhost/admin/tenants

# API Docs
open http://localhost/docs
```

### Siguiente Paso: Implementar Onboarding con Stripe
- Ver plan completo: `/docs/v4.6/STRIPE_ONBOARDING_PLAN.md`
- Timeline estimado: 5-8 días
- Valor: Onboarding automatizado con pagos recurrentes

---

## 🎉 ¡Listo!

Una vez ejecutado `./scripts/deploy_frontend.sh` correctamente, deberías poder acceder a:

- ✅ Frontend React: `http://localhost/`
- ✅ API Backend: `http://localhost/api/`
- ✅ Swagger Docs: `http://localhost/docs`
- ✅ Health Check: `http://localhost/api/health`

**Problema resuelto!** 🚀

---

**Versión**: 4.6.0  
**Creado**: 29 de Diciembre de 2025  
**Estado**: ⚡ ACCIÓN INMEDIATA
