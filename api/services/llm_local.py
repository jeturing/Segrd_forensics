"""
LLM Local Integration (Phi-4)
Clasifica hallazgos, genera recomendaciones y alimenta el SOAR Engine.
Seguridad: Este módulo solo analiza texto, NO ejecuta ninguna acción ofensiva.

Requiere: pip install transformers torch accelerate
Para CPU: pip install torch --index-url https://download.pytorch.org/whl/cpu
"""

from typing import Dict, Any, List, Optional
import json
import re
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# Intentar cargar el modelo real
_model = None
_tokenizer = None
_model_loaded = False

def _load_model():
    """Cargar modelo Phi-4 de forma lazy"""
    global _model, _tokenizer, _model_loaded
    
    if _model_loaded:
        return _model is not None
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        model_name = "microsoft/phi-4"
        logger.info(f"🧠 Cargando modelo {model_name}...")
        
        _tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        logger.info(f"✅ Modelo {model_name} cargado correctamente")
        _model_loaded = True
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ No se pudo cargar el modelo LLM: {e}")
        logger.info("🔧 Usando clasificación heurística (sin LLM)")
        _model_loaded = True
        return False


class Phi4LocalLLM:
    """
    LLM Local Phi-4 con fallback a clasificación heurística.
    En producción se conecta a un modelo local real (CPU/GPU).
    """
    
    # Patrones de detección para clasificación heurística
    CRITICAL_PATTERNS = [
        r"token.*malicious",
        r"credential.*theft",
        r"ransomware",
        r"c2.*server",
        r"command.*control",
        r"exfiltrat",
        r"admin.*compromis",
        r"privilege.*escalation",
        r"lateral.*movement",
        r"persistence.*backdoor"
    ]
    
    HIGH_PATTERNS = [
        r"impossible.*travel",
        r"suspicious.*signin",
        r"anomalous.*location",
        r"new.*device.*unknown",
        r"oauth.*abuse",
        r"consent.*phishing",
        r"mail.*forward.*external",
        r"delegate.*full.*access",
        r"mfa.*disabled"
    ]
    
    MEDIUM_PATTERNS = [
        r"suspicious.*rule",
        r"inbox.*rule.*create",
        r"password.*change",
        r"role.*change",
        r"app.*consent",
        r"permission.*grant",
        r"failed.*login.*multiple"
    ]
    
    IOC_PATTERNS = {
        "ip": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        "domain": r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "hash_md5": r"\b[a-fA-F0-9]{32}\b",
        "hash_sha1": r"\b[a-fA-F0-9]{40}\b",
        "hash_sha256": r"\b[a-fA-F0-9]{64}\b",
        "url": r"https?://[^\s<>\"{}|\\^`\[\]]+"
    }

    def __init__(self):
        self.use_llm = False
        
    def _init_llm(self):
        """Inicializar LLM de forma lazy"""
        if not self.use_llm:
            self.use_llm = _load_model()
    
    def classify_severity(self, findings: Dict) -> str:
        """Asigna severidad basada en señales forenses."""
        text = json.dumps(findings, default=str).lower()
        
        # Buscar patrones críticos
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "critical"
        
        # Buscar patrones altos
        for pattern in self.HIGH_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "high"
        
        # Buscar patrones medios
        for pattern in self.MEDIUM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "medium"
        
        return "low"
    
    def calculate_confidence_score(self, findings: Dict) -> float:
        """Calcula score de confianza basado en cantidad de evidencia"""
        text = json.dumps(findings, default=str).lower()
        score = 50.0  # Base
        
        # +10 por cada patrón crítico encontrado
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 10
        
        # +5 por cada patrón alto
        for pattern in self.HIGH_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 5
        
        # +2 por cada IOC encontrado
        for ioc_type, pattern in self.IOC_PATTERNS.items():
            matches = re.findall(pattern, text)
            score += len(matches) * 2
        
        return min(score, 100.0)
    
    def extract_iocs(self, findings: Dict) -> List[Dict]:
        """Extrae IOCs de los hallazgos"""
        text = json.dumps(findings, default=str)
        iocs = []
        
        for ioc_type, pattern in self.IOC_PATTERNS.items():
            matches = set(re.findall(pattern, text, re.IGNORECASE))
            for match in matches:
                # Filtrar falsos positivos comunes
                if ioc_type == "domain" and match in ["localhost", "example.com", "test.com"]:
                    continue
                if ioc_type == "ip" and match.startswith("127.") or match.startswith("0."):
                    continue
                    
                iocs.append({
                    "type": ioc_type,
                    "value": match,
                    "source": "ai_extraction",
                    "extracted_at": datetime.utcnow().isoformat()
                })
        
        return iocs
    
    def generate_recommendations(self, findings: Dict) -> Dict:
        """Genera acciones recomendadas basadas en patrones."""
        severity = self.classify_severity(findings)
        text = json.dumps(findings, default=str).lower()
        
        base_recommendations = {
            "low": [
                "Revisar actividad del usuario en los últimos 7 días",
                "Monitorear próximos eventos similares",
                "Documentar en el caso para referencia futura"
            ],
            "medium": [
                "Resetear credenciales del usuario afectado",
                "Validar reglas de reenvío en Exchange",
                "Habilitar MFA si no está activo",
                "Revisar aplicaciones OAuth autorizadas",
                "Notificar al equipo de seguridad"
            ],
            "high": [
                "Revocar sesiones activas inmediatamente",
                "Forzar rotación de claves OAuth",
                "Analizar OAuth apps sospechosas",
                "Bloquear acceso condicional temporal",
                "Iniciar investigación forense",
                "Preservar evidencia antes de remediar"
            ],
            "critical": [
                "Aislar usuario inmediatamente",
                "Iniciar flujo IR crítico",
                "Escalar a CISO y Purple Team",
                "Ejecutar análisis completo M365",
                "Bloquear IPs sospechosas en firewall",
                "Revocar todos los tokens activos",
                "Notificar a las partes interesadas",
                "Preparar comunicación de incidente"
            ]
        }
        
        # Añadir recomendaciones específicas basadas en contenido
        specific_recs = []
        
        if "forward" in text or "redirect" in text:
            specific_recs.append("Revisar y eliminar reglas de reenvío de correo")
        
        if "oauth" in text or "consent" in text:
            specific_recs.append("Auditar aplicaciones con permisos OAuth")
        
        if "mfa" in text.lower():
            specific_recs.append("Verificar configuración MFA del usuario")
        
        if "admin" in text.lower():
            specific_recs.append("Revisar asignaciones de roles administrativos")
        
        all_recommendations = specific_recs + base_recommendations[severity]
        
        return {
            "severity": severity,
            "actions": all_recommendations[:10],  # Máximo 10 recomendaciones
            "justification": f"Clasificado como {severity.upper()} según patrones detectados en el hallazgo."
        }
    
    async def generate_with_llm(self, prompt: str) -> Optional[str]:
        """Genera respuesta usando el modelo LLM real"""
        self._init_llm()
        
        if not self.use_llm or _model is None:
            return None
        
        try:
            inputs = _tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
            
            if hasattr(_model, "device"):
                inputs = inputs.to(_model.device)
            
            outputs = await asyncio.to_thread(
                _model.generate,
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
                top_p=0.9
            )
            
            response = _tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
            
        except Exception as e:
            logger.error(f"Error generando con LLM: {e}")
            return None
    
    async def analyze_with_llm(self, findings: Dict[str, Any]) -> Optional[Dict]:
        """Análisis profundo usando LLM real"""
        self._init_llm()
        
        if not self.use_llm:
            return None
        
        prompt = f"""Analiza el siguiente hallazgo de seguridad y proporciona:
1. Clasificación de severidad (critical/high/medium/low)
2. Resumen ejecutivo (máximo 100 palabras)
3. IOCs identificados
4. Recomendaciones de respuesta

Hallazgo:
{json.dumps(findings, indent=2, default=str)[:3000]}

Responde en formato JSON válido."""

        response = await self.generate_with_llm(prompt)
        
        if response:
            try:
                # Extraer JSON de la respuesta
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def analyze(self, findings: Dict[str, Any]) -> Dict[str, Any]:
        """Output completo para el SOAR Engine (síncrono, heurístico)."""
        severity = self.classify_severity(findings)
        recommendations = self.generate_recommendations(findings)
        iocs = self.extract_iocs(findings)
        confidence = self.calculate_confidence_score(findings)
        
        return {
            "input": findings,
            "classification": severity,
            "confidence_score": confidence,
            "iocs_extracted": iocs,
            "recommendations": recommendations,
            "analyzed_at": datetime.utcnow().isoformat(),
            "llm_used": self.use_llm
        }
    
    async def analyze_async(self, findings: Dict[str, Any]) -> Dict[str, Any]:
        """Análisis asíncrono con intento de usar LLM"""
        # Primero intentar análisis con LLM
        llm_result = await self.analyze_with_llm(findings)
        
        if llm_result:
            # Enriquecer resultado LLM con datos adicionales
            llm_result["llm_used"] = True
            llm_result["analyzed_at"] = datetime.utcnow().isoformat()
            return llm_result
        
        # Fallback a análisis heurístico
        return self.analyze(findings)


# Instancia singleton
llm_local = Phi4LocalLLM()
