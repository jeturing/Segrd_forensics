# ✅ LLM local con Ollama (phi-4)

## Arranque rápido
```bash
# Levantar Ollama y LLM Provider (usa compose v4.4.1)
docker compose -f docker-compose.v4.4.1.yml up -d ollama llm-provider

# Descargar modelo phi-4 dentro del contenedor (una sola vez)
docker exec -it mcp-ollama ollama pull phi4
```

## Configuración usada
- `OLLAMA_URL` interno: `http://ollama:11434` (ya seteado en llm-provider)
- `OLLAMA_ENABLED=true` (por defecto en compose)
- Puerto expuesto host: `11434`
- Modelos persistentes en volumen `ollama-models`

## Verificación desde backend
```bash
# Health de llm-provider
curl -H "X-API-Key: $API_KEY" http://localhost:8090/health

# Listar modelos disponibles
curl -H "X-API-Key: $API_KEY" "http://localhost:8090/models"
```

## Uso en frontend
- En Panel de Mantenimiento → pestaña "Modelos" → pulsa "🔄 Refrescar Modelos" tras haber hecho `ollama pull phi4`.
- Selecciona el modelo `phi4` como activo; ya queda disponible para generación/análisis.

## Notas
- Si quieres otro modelo, usa `ollama pull <nombre>` y luego "Refrescar Modelos".
- Para reinstalar limpio, borra volumen: `docker volume rm mcp-kali-forensics_ollama-models` (el nombre puede variar por prefijo de proyecto compose).
