# Despliegue con un clic - MCP Kali Forensics

Este documento explica cómo desplegar todos los contenedores y arrancar instancias Ollama por agente con un solo comando.

Requisitos previos
- Docker y Docker Compose instalados
- Al menos 16-32 GB de RAM recomendados si vas a ejecutar modelos Phi-4 en CPU

Pasos (rápidos)

1. Clona el repo y sitúate en la carpeta raíz:

```bash
cd /Users/owner/Desktop/jcore
```

2. Asegúrate de tener el archivo `.env` con las variables mínimas:

```
API_KEY=mcp-forensics-dev-key
DB_PASSWORD=forensics_secure_pass
JETURING_CORE_API_KEY=dev-key-placeholder
```

3. Ejecuta el script de arranque (un clic):

```bash
chmod +x ./start_services.sh
./start_services.sh
```

Qué hace el script
- `docker-compose pull` y `docker-compose up -d`
- Espera por `nginx` en `http://localhost/nginx-health`
- Espera por API en `http://localhost:8888/health` (u otros puertos esperados)
- Comprueba modelos en Ollama en los puertos `11434-11437`

Per-agent Ollama
- `docker-compose.yml` incluye instancias `ollama-agent-agent1/2/3` en puertos `11435/11436/11437`
- El script espera que los modelos se hayan descargado; si no, ejecuta `docker exec <container> ollama pull phi4-mini`

Acceso a la aplicación
- API: http://localhost:8888/docs (usa header `X-API-Key: <API_KEY>`)
- Nginx proxy: http://localhost/ (rutea a la API)

Notas
- TLS/HTTPS no está habilitado por defecto: añade certificados en `/etc/nginx/ssl` y ajusta `/etc/nginx/conf.d/default.conf` para habilitar 443.
- Si quieres cambiar la configuración por agente (memoria, puerto, modelo) edita `docker-compose.yml`.

Troubleshooting
- `docker ps` para ver contenedores
- `docker logs <container>` para revisar errores
- Si nginx no arranca, revisa `/Users/owner/Desktop/jcore/nginx.conf` para asegurar que los upstream names coincidan con los nombres de servicio del compose

