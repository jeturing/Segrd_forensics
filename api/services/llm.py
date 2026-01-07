"""
LLM Service - Integration with Ollama and Remote APIs
"""
import os
import logging
from typing import Dict, Any, Optional, AsyncGenerator
import aiohttp

from api.models.llm import (
    LLMModelConfig,
    LLM_MODELS,
    ChatRequest,
    ChatResponse,
    ModelListResponse,
)

logger = logging.getLogger(__name__)


class LLMService:
    """LLM Service for AI-powered forensic analysis"""
    
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.current_model = os.getenv("LLM_MODEL_DEFAULT", "basic")
        self.gpu_available = self._check_gpu_available()
        
    def _check_gpu_available(self) -> bool:
        """Check if GPU is available"""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"GPU check failed: {e}")
            return False
    
    async def check_ollama_health(self) -> bool:
        """Check if Ollama service is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> ModelListResponse:
        """List available models"""
        ollama_available = await self.check_ollama_health()
        
        models = []
        for key, config in LLM_MODELS.items():
            model_info = {
                "key": key,
                "name": config.name,
                "display_name": config.display_name,
                "type": config.type.value,
                "ram_required_gb": config.ram_required_gb,
                "gpu_required": config.gpu_required,
                "context_length": config.context_length,
                "available": True,
            }
            
            # Check if model is actually available
            if config.ollama_model and ollama_available:
                model_info["available"] = await self._check_model_exists(config.ollama_model)
            elif config.remote_api:
                model_info["available"] = bool(os.getenv("LLM_REMOTE_API_KEY"))
            
            models.append(model_info)
        
        return ModelListResponse(
            models=models,
            current_model=self.current_model,
            ollama_available=ollama_available,
            gpu_available=self.gpu_available,
        )
    
    async def _check_model_exists(self, model_name: str) -> bool:
        """Check if model exists in Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        return any(m.get("name", "").startswith(model_name) for m in models)
            return False
        except Exception as e:
            logger.error(f"Error checking model existence: {e}")
            return False
    
    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull/download model from Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/pull",
                    json={"name": model_name},
                    timeout=aiohttp.ClientTimeout(total=3600)  # 1 hour for large models
                ) as response:
                    async for line in response.content:
                        if line:
                            try:
                                import json
                                data = json.loads(line)
                                yield data
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            yield {"status": "error", "message": str(e)}
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Chat completion"""
        # Determine model to use
        model_key = request.model or self.current_model
        model_config = LLM_MODELS.get(model_key)
        
        if not model_config:
            raise ValueError(f"Unknown model: {model_key}")
        
        # Route to appropriate backend
        if model_config.ollama_model:
            return await self._chat_ollama(request, model_config)
        elif model_config.remote_api:
            return await self._chat_remote(request, model_config)
        else:
            raise ValueError(f"No backend configured for model: {model_key}")
    
    async def _chat_ollama(
        self, 
        request: ChatRequest, 
        model_config: LLMModelConfig
    ) -> ChatResponse:
        """Chat using Ollama"""
        # Build messages
        messages = []
        
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })
        
        # Add context if provided
        if request.context:
            context_str = f"Context:\n{self._format_context(request.context)}\n\n"
            messages.append({
                "role": "system",
                "content": context_str
            })
        
        # Add chat history
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current prompt
        messages.append({
            "role": "user",
            "content": request.prompt
        })
        
        # Call Ollama API
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model_config.ollama_model,
                    "messages": messages,
                    "stream": False,
                }
                
                if request.temperature is not None:
                    payload["temperature"] = request.temperature
                if request.max_tokens is not None:
                    payload["options"] = {"num_predict": request.max_tokens}
                
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {error_text}")
                    
                    data = await response.json()
                    
                    return ChatResponse(
                        response=data.get("message", {}).get("content", ""),
                        model=model_config.ollama_model,
                        tokens_used=data.get("eval_count"),
                        finish_reason=data.get("done_reason"),
                        metadata={
                            "total_duration": data.get("total_duration"),
                            "load_duration": data.get("load_duration"),
                            "prompt_eval_count": data.get("prompt_eval_count"),
                            "eval_count": data.get("eval_count"),
                        }
                    )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}", exc_info=True)
            raise
    
    async def _chat_remote(
        self, 
        request: ChatRequest, 
        model_config: LLMModelConfig
    ) -> ChatResponse:
        """Chat using remote API (Claude, GPT-4, etc.)"""
        # This is a placeholder - implement specific API integrations
        api_key = os.getenv("LLM_REMOTE_API_KEY")
        api_url = os.getenv("LLM_REMOTE_API_URL")
        
        if not api_key:
            raise ValueError("Remote API key not configured")
        
        # Example for Anthropic Claude
        if model_config.remote_api == "anthropic":
            return await self._chat_anthropic(request, model_config, api_key)
        
        # Add other providers as needed
        raise NotImplementedError(f"Remote API {model_config.remote_api} not implemented")
    
    async def _chat_anthropic(
        self,
        request: ChatRequest,
        model_config: LLMModelConfig,
        api_key: str
    ) -> ChatResponse:
        """Chat using Anthropic Claude API"""
        # Placeholder for Anthropic integration
        # In production, use anthropic Python SDK
        raise NotImplementedError("Anthropic integration pending")
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary into readable string"""
        lines = []
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                import json
                value = json.dumps(value, indent=2)
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    async def analyze_forensic_data(
        self,
        case_id: str,
        analysis_type: str,
        data: Dict[str, Any],
        instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze forensic data using LLM"""
        # Build specialized prompts for forensic analysis
        system_prompt = self._get_forensic_system_prompt(analysis_type)
        
        # Format data for analysis
        data_str = self._format_forensic_data(analysis_type, data)
        
        # Build prompt
        prompt = f"""Analyze the following {analysis_type} data from case {case_id}:

{data_str}

{instructions or 'Provide a detailed analysis with findings and recommendations.'}

Format your response as JSON with keys: findings, iocs, recommendations, severity"""
        
        # Request chat completion
        request = ChatRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            context={"case_id": case_id, "analysis_type": analysis_type},
            temperature=0.3,  # Lower temperature for more focused analysis
        )
        
        response = await self.chat(request)
        
        # Parse response (expecting JSON)
        try:
            import json
            result = json.loads(response.response)
        except json.JSONDecodeError:
            # Fallback to plain text response
            result = {
                "findings": response.response,
                "iocs": [],
                "recommendations": [],
                "severity": "unknown"
            }
        
        return result
    
    def _get_forensic_system_prompt(self, analysis_type: str) -> str:
        """Get system prompt for forensic analysis"""
        prompts = {
            "ioc": "You are a cybersecurity expert specializing in Indicator of Compromise (IOC) analysis. Analyze the data and identify malicious indicators.",
            "malware": "You are a malware analyst. Analyze the suspicious files and behaviors to determine malware presence and characteristics.",
            "timeline": "You are a digital forensics expert. Analyze the timeline of events to reconstruct the incident sequence.",
            "report": "You are a forensic report writer. Summarize the investigation findings in a professional incident response report.",
            "network": "You are a network security analyst. Analyze network traffic and connections for suspicious activity.",
        }
        return prompts.get(analysis_type, "You are a cybersecurity forensics expert.")
    
    def _format_forensic_data(self, analysis_type: str, data: Dict[str, Any]) -> str:
        """Format forensic data for LLM consumption"""
        import json
        return json.dumps(data, indent=2)


# Singleton instance
llm_service = LLMService()
