"""
MCP Kali Forensics - LLM Provider Main v4.4.1
Servidor proxy unificado para múltiples proveedores LLM
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import httpx
import redis.asyncio as redis

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm-provider")

# Configuración
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://100.101.115.5:2714")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "lmstudio")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")

# OpenTelemetry setup
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if OTEL_ENDPOINT:
    resource = Resource.create({"service.name": "llm-provider"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


class LLMProvider(str, Enum):
    LMSTUDIO = "lmstudio"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Message(BaseModel):
    role: str = "user"
    content: str


class CompletionRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    provider: Optional[LLMProvider] = None
    max_tokens: int = Field(default=4096, ge=1, le=32000)
    temperature: float = Field(default=0.7, ge=0, le=2)
    stream: bool = False
    system_prompt: Optional[str] = None


class CompletionResponse(BaseModel):
    id: str
    model: str
    provider: str
    content: str
    usage: Dict[str, int]
    finish_reason: str
    created_at: str


# FastAPI app
app = FastAPI(
    title="MCP LLM Provider",
    version="4.4.1",
    description="Unified LLM proxy for LM Studio, Ollama, OpenAI, Anthropic"
)

FastAPIInstrumentor.instrument_app(app)

# HTTP client
http_client: Optional[httpx.AsyncClient] = None
redis_client = None

# Cache de modelos disponibles
available_models: Dict[str, List[str]] = {
    "lmstudio": [],
    "ollama": [],
    "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
}


@app.on_event("startup")
async def startup():
    global http_client, redis_client
    http_client = httpx.AsyncClient(timeout=120.0)
    redis_client = await redis.from_url(REDIS_URL)
    
    # Descubrir modelos disponibles
    await refresh_models()
    logger.info("🤖 LLM Provider iniciado")


@app.on_event("shutdown")
async def shutdown():
    if http_client:
        await http_client.aclose()
    if redis_client:
        await redis_client.close()


async def refresh_models():
    """Refrescar lista de modelos disponibles"""
    # LM Studio
    try:
        resp = await http_client.get(f"{LM_STUDIO_URL}/v1/models")
        if resp.status_code == 200:
            data = resp.json()
            available_models["lmstudio"] = [m["id"] for m in data.get("data", [])]
            logger.info(f"📦 LM Studio modelos: {available_models['lmstudio']}")
    except Exception as e:
        logger.warning(f"⚠️ LM Studio no disponible: {e}")
    
    # Ollama
    try:
        resp = await http_client.get(f"{OLLAMA_URL}/api/tags")
        if resp.status_code == 200:
            data = resp.json()
            available_models["ollama"] = [m["name"] for m in data.get("models", [])]
            logger.info(f"📦 Ollama modelos: {available_models['ollama']}")
    except Exception as e:
        logger.warning(f"⚠️ Ollama no disponible: {e}")


@app.get("/health")
async def health():
    providers_status = {}
    
    # Check LM Studio
    try:
        resp = await http_client.get(f"{LM_STUDIO_URL}/v1/models", timeout=5.0)
        providers_status["lmstudio"] = resp.status_code == 200
    except:
        providers_status["lmstudio"] = False
    
    # Check Ollama
    try:
        resp = await http_client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        providers_status["ollama"] = resp.status_code == 200
    except:
        providers_status["ollama"] = False
    
    # OpenAI/Anthropic check basado en API key
    providers_status["openai"] = bool(OPENAI_API_KEY)
    providers_status["anthropic"] = bool(ANTHROPIC_API_KEY)
    
    return {
        "status": "healthy" if any(providers_status.values()) else "degraded",
        "service": "llm-provider",
        "version": "4.4.1",
        "providers": providers_status,
        "default_provider": DEFAULT_PROVIDER,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/models")
async def get_models():
    """Obtener todos los modelos disponibles"""
    await refresh_models()
    return {
        "models": available_models,
        "default_provider": DEFAULT_PROVIDER
    }


@app.post("/v1/chat/completions", response_model=CompletionResponse)
async def chat_completion(request: CompletionRequest):
    """Endpoint unificado de chat completion (compatible con OpenAI API)"""
    provider = request.provider or LLMProvider(DEFAULT_PROVIDER)
    
    if provider == LLMProvider.LMSTUDIO:
        return await _lmstudio_completion(request)
    elif provider == LLMProvider.OLLAMA:
        return await _ollama_completion(request)
    elif provider == LLMProvider.OPENAI:
        return await _openai_completion(request)
    elif provider == LLMProvider.ANTHROPIC:
        return await _anthropic_completion(request)
    else:
        raise HTTPException(400, f"Provider no soportado: {provider}")


async def _lmstudio_completion(request: CompletionRequest) -> CompletionResponse:
    """Completion via LM Studio"""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    if request.system_prompt:
        messages.insert(0, {"role": "system", "content": request.system_prompt})
    
    payload = {
        "messages": messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "stream": False
    }
    
    if request.model:
        payload["model"] = request.model
    
    try:
        resp = await http_client.post(
            f"{LM_STUDIO_URL}/v1/chat/completions",
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()
        
        return CompletionResponse(
            id=data.get("id", f"lms-{datetime.utcnow().timestamp()}"),
            model=data.get("model", "unknown"),
            provider="lmstudio",
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            created_at=datetime.utcnow().isoformat()
        )
    except httpx.HTTPError as e:
        logger.error(f"❌ LM Studio error: {e}")
        raise HTTPException(502, f"LM Studio error: {str(e)}")


async def _ollama_completion(request: CompletionRequest) -> CompletionResponse:
    """Completion via Ollama"""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    if request.system_prompt:
        messages.insert(0, {"role": "system", "content": request.system_prompt})
    
    model = request.model or (available_models["ollama"][0] if available_models["ollama"] else "llama2")
    
    payload = {
        "model": model,
        "messages": messages,
        "options": {
            "num_predict": request.max_tokens,
            "temperature": request.temperature
        },
        "stream": False
    }
    
    try:
        resp = await http_client.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()
        
        return CompletionResponse(
            id=f"ollama-{datetime.utcnow().timestamp()}",
            model=model,
            provider="ollama",
            content=data["message"]["content"],
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            },
            finish_reason="stop",
            created_at=datetime.utcnow().isoformat()
        )
    except httpx.HTTPError as e:
        logger.error(f"❌ Ollama error: {e}")
        raise HTTPException(502, f"Ollama error: {str(e)}")


async def _openai_completion(request: CompletionRequest) -> CompletionResponse:
    """Completion via OpenAI API"""
    if not OPENAI_API_KEY:
        raise HTTPException(400, "OpenAI API key not configured")
    
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    if request.system_prompt:
        messages.insert(0, {"role": "system", "content": request.system_prompt})
    
    model = request.model or "gpt-4-turbo"
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature
    }
    
    try:
        resp = await http_client.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
        )
        resp.raise_for_status()
        data = resp.json()
        
        return CompletionResponse(
            id=data["id"],
            model=data["model"],
            provider="openai",
            content=data["choices"][0]["message"]["content"],
            usage=data["usage"],
            finish_reason=data["choices"][0]["finish_reason"],
            created_at=datetime.utcnow().isoformat()
        )
    except httpx.HTTPError as e:
        logger.error(f"❌ OpenAI error: {e}")
        raise HTTPException(502, f"OpenAI error: {str(e)}")


async def _anthropic_completion(request: CompletionRequest) -> CompletionResponse:
    """Completion via Anthropic API"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(400, "Anthropic API key not configured")
    
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    model = request.model or "claude-3-sonnet-20240229"
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature
    }
    
    if request.system_prompt:
        payload["system"] = request.system_prompt
    
    try:
        resp = await http_client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        )
        resp.raise_for_status()
        data = resp.json()
        
        return CompletionResponse(
            id=data["id"],
            model=data["model"],
            provider="anthropic",
            content=data["content"][0]["text"],
            usage={
                "prompt_tokens": data["usage"]["input_tokens"],
                "completion_tokens": data["usage"]["output_tokens"],
                "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
            },
            finish_reason=data["stop_reason"] or "stop",
            created_at=datetime.utcnow().isoformat()
        )
    except httpx.HTTPError as e:
        logger.error(f"❌ Anthropic error: {e}")
        raise HTTPException(502, f"Anthropic error: {str(e)}")


@app.post("/analyze")
async def analyze_forensics(
    content: str,
    analysis_type: str = "general",
    model: Optional[str] = None
):
    """Endpoint especializado para análisis forense con LLM"""
    system_prompts = {
        "general": "You are a cybersecurity forensics analyst. Analyze the following data and provide insights.",
        "malware": "You are a malware analyst. Identify potential malware indicators, techniques, and IOCs.",
        "network": "You are a network forensics expert. Analyze network traffic patterns and identify anomalies.",
        "incident": "You are an incident response specialist. Provide timeline analysis and remediation recommendations.",
        "threat_hunt": "You are a threat hunter. Identify potential threats, TTPs, and hunting hypotheses."
    }
    
    request = CompletionRequest(
        messages=[Message(role="user", content=content)],
        model=model,
        system_prompt=system_prompts.get(analysis_type, system_prompts["general"]),
        max_tokens=MAX_TOKENS,
        temperature=0.3  # Lower temperature for analysis
    )
    
    response = await chat_completion(request)
    
    return {
        "analysis_type": analysis_type,
        "result": response.content,
        "model": response.model,
        "provider": response.provider,
        "tokens_used": response.usage
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8090,
        log_level="info"
    )
