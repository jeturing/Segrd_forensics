"""
LLM Models and Configuration
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class LLMModelType(str, Enum):
    """LLM Model Types"""
    BASIC = "basic"      # TinyLlama, MCP models (~2GB RAM)
    MEDIUM = "medium"    # Phi-4 (~8GB RAM)
    FULL = "full"        # Remote API (Claude, GPT-4)


class LLMModelConfig(BaseModel):
    """LLM Model Configuration"""
    name: str
    display_name: str
    type: LLMModelType
    ollama_model: Optional[str] = None
    remote_api: Optional[str] = None
    ram_required_gb: int
    gpu_required: bool = False
    context_length: int = 2048
    temperature: float = 0.7
    max_tokens: int = 1000


# Predefined model configurations
LLM_MODELS = {
    "basic": LLMModelConfig(
        name="tinyllama",
        display_name="TinyLlama 1.1B",
        type=LLMModelType.BASIC,
        ollama_model="tinyllama",
        ram_required_gb=2,
        gpu_required=False,
        context_length=2048,
    ),
    "medium": LLMModelConfig(
        name="phi4",
        display_name="Microsoft Phi-4 14B",
        type=LLMModelType.MEDIUM,
        ollama_model="phi4",
        ram_required_gb=8,
        gpu_required=True,
        context_length=4096,
    ),
    "full": LLMModelConfig(
        name="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet (Remote)",
        type=LLMModelType.FULL,
        remote_api="anthropic",
        ram_required_gb=0,
        gpu_required=False,
        context_length=200000,
    ),
}


class ChatMessage(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request"""
    prompt: str = Field(..., description="User prompt")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    messages: Optional[List[ChatMessage]] = Field(default_factory=list, description="Chat history")
    model: Optional[str] = Field(None, description="Override model (basic/medium/full)")
    temperature: Optional[float] = Field(None, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    stream: bool = Field(False, description="Stream response")


class ChatResponse(BaseModel):
    """Chat completion response"""
    response: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelPullRequest(BaseModel):
    """Model pull/download request"""
    model_name: str = Field(..., description="Model name (tinyllama, phi4, etc.)")


class ModelPullResponse(BaseModel):
    """Model pull response"""
    status: str
    model_name: str
    message: str
    progress: Optional[Dict[str, Any]] = None


class ModelListResponse(BaseModel):
    """Available models list"""
    models: List[Dict[str, Any]]
    current_model: str
    ollama_available: bool
    gpu_available: bool


class AnalysisRequest(BaseModel):
    """LLM analysis request for forensic data"""
    case_id: str
    analysis_type: str = Field(..., description="ioc, malware, timeline, report, etc.")
    data: Dict[str, Any] = Field(..., description="Data to analyze")
    instructions: Optional[str] = Field(None, description="Special instructions")
    model: Optional[str] = Field(None, description="Override model")


class AnalysisResponse(BaseModel):
    """LLM analysis response"""
    case_id: str
    analysis_type: str
    findings: Dict[str, Any]
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_used: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
