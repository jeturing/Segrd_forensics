"""
MCP v4.6.0 - SOAR ML Service
Machine Learning para predicción de éxito de playbooks y aprendizaje continuo.
Usa scikit-learn para modelos de clasificación basados en historial de ejecuciones.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import pickle

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("⚠️ scikit-learn not available. SOAR ML features disabled.")

from api.config import settings
from api.database import get_db_context

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

MODEL_DIR = Path(settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else ".") / "models" / "soar_ml"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MIN_TRAINING_SAMPLES = 50  # Mínimo de ejecuciones para entrenar
RETRAIN_INTERVAL_HOURS = 24
PREDICTION_CACHE_TTL = 300  # 5 minutos

# Feature names for model
FEATURE_NAMES = [
    "playbook_type_encoded",      # blue/red/purple
    "category_encoded",           # incident_response, malware_analysis, etc
    "trigger_encoded",            # manual, on_ioc, scheduled
    "num_steps",                   # Número de pasos del playbook
    "has_approval",               # Requiere aprobación
    "hour_of_day",                # Hora de ejecución (0-23)
    "day_of_week",                # Día de la semana (0-6)
    "historical_success_rate",    # Tasa histórica del playbook
    "recent_failures",            # Fallos en últimas 24h
    "avg_execution_time",         # Tiempo promedio de ejecución
    "case_priority_encoded",      # Prioridad del caso
    "tool_availability_score",    # Disponibilidad de herramientas
]


# =============================================================================
# SOAR ML MODEL
# =============================================================================

class SOARMLModel:
    """
    Modelo de Machine Learning para predicción de éxito de playbooks.
    Aprende de ejecuciones históricas para predecir probabilidad de éxito.
    """
    
    def __init__(self):
        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.encoders: Dict[str, LabelEncoder] = {}
        self.is_trained = False
        self.last_trained: Optional[datetime] = None
        self.training_metrics: Dict[str, float] = {}
        self.prediction_cache: Dict[str, Tuple[float, datetime]] = {}
        
        # Cargar modelo existente si existe
        self._load_model()
    
    def _load_model(self):
        """Cargar modelo persistido desde disco."""
        if not SKLEARN_AVAILABLE:
            return
            
        model_path = MODEL_DIR / "playbook_success_model.pkl"
        scaler_path = MODEL_DIR / "scaler.pkl"
        encoders_path = MODEL_DIR / "encoders.pkl"
        metadata_path = MODEL_DIR / "metadata.json"
        
        try:
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                with open(encoders_path, 'rb') as f:
                    self.encoders = pickle.load(f)
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.last_trained = datetime.fromisoformat(metadata["last_trained"])
                    self.training_metrics = metadata.get("metrics", {})
                
                self.is_trained = True
                logger.info(f"✅ SOAR ML model loaded. Last trained: {self.last_trained}")
        except Exception as e:
            logger.warning(f"⚠️ Could not load SOAR ML model: {e}")
    
    def _save_model(self):
        """Persistir modelo a disco."""
        if not self.model:
            return
            
        try:
            with open(MODEL_DIR / "playbook_success_model.pkl", 'wb') as f:
                pickle.dump(self.model, f)
            with open(MODEL_DIR / "scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
            with open(MODEL_DIR / "encoders.pkl", 'wb') as f:
                pickle.dump(self.encoders, f)
            with open(MODEL_DIR / "metadata.json", 'w') as f:
                json.dump({
                    "last_trained": self.last_trained.isoformat() if self.last_trained else None,
                    "metrics": self.training_metrics,
                    "feature_names": FEATURE_NAMES
                }, f, indent=2)
            
            logger.info("💾 SOAR ML model saved to disk")
        except Exception as e:
            logger.error(f"❌ Failed to save SOAR ML model: {e}")
    
    async def extract_features(
        self,
        playbook: Dict,
        case: Optional[Dict] = None,
        execution_context: Optional[Dict] = None
    ) -> np.ndarray:
        """
        Extraer features de un playbook y contexto para predicción.
        
        Args:
            playbook: Datos del playbook
            case: Datos del caso (opcional)
            execution_context: Contexto adicional de ejecución
        
        Returns:
            Array de features normalizados
        """
        now = datetime.utcnow()
        
        # Encode categorical features
        playbook_type = playbook.get("team_type", "blue")
        category = playbook.get("category", "general")
        trigger = playbook.get("trigger", "manual")
        
        # Get or create encoders
        if "playbook_type" not in self.encoders:
            self.encoders["playbook_type"] = LabelEncoder()
            self.encoders["playbook_type"].fit(["blue", "red", "purple"])
        if "category" not in self.encoders:
            self.encoders["category"] = LabelEncoder()
            self.encoders["category"].fit([
                "general", "incident_response", "malware_analysis",
                "reconnaissance", "threat_hunting", "containment"
            ])
        if "trigger" not in self.encoders:
            self.encoders["trigger"] = LabelEncoder()
            self.encoders["trigger"].fit(["manual", "on_ioc_create", "scheduled", "on_alert"])
        if "priority" not in self.encoders:
            self.encoders["priority"] = LabelEncoder()
            self.encoders["priority"].fit(["low", "medium", "high", "critical"])
        
        # Safe encode (handle unknown values)
        def safe_encode(encoder: LabelEncoder, value: str, default: int = 0) -> int:
            try:
                return int(encoder.transform([value])[0])
            except ValueError:
                return default
        
        # Build feature vector
        features = [
            safe_encode(self.encoders["playbook_type"], playbook_type),
            safe_encode(self.encoders["category"], category),
            safe_encode(self.encoders["trigger"], trigger),
            len(playbook.get("steps", [])),
            1 if playbook.get("requires_approval", False) else 0,
            now.hour,
            now.weekday(),
            playbook.get("success_rate", 0.5),
            await self._get_recent_failures(playbook.get("id", "")),
            playbook.get("avg_execution_time_seconds", 300) / 60,  # Convert to minutes
            safe_encode(self.encoders["priority"], case.get("priority", "medium") if case else "medium"),
            await self._check_tool_availability(playbook.get("steps", []))
        ]
        
        return np.array(features).reshape(1, -1)
    
    async def _get_recent_failures(self, playbook_id: str, hours: int = 24) -> int:
        """Contar fallos recientes de un playbook."""
        try:
            with get_db_context() as db:
                from api.models.tools import PlaybookExecution
                
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                count = db.query(PlaybookExecution).filter(
                    PlaybookExecution.playbook_id == playbook_id,
                    PlaybookExecution.status == "failed",
                    PlaybookExecution.started_at >= cutoff
                ).count()
                return count
        except Exception:
            return 0
    
    async def _check_tool_availability(self, steps: List[Dict]) -> float:
        """
        Verificar disponibilidad de herramientas requeridas.
        Retorna score de 0 a 1.
        """
        if not steps:
            return 1.0
        
        tool_steps = [s for s in steps if s.get("action_type") == "tool_execute"]
        if not tool_steps:
            return 1.0
        
        # TODO: Integrar con verificación real de herramientas
        # Por ahora retornar 0.9 como valor por defecto
        return 0.9
    
    async def predict_success(
        self,
        playbook: Dict,
        case: Optional[Dict] = None,
        execution_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Predecir probabilidad de éxito de un playbook.
        
        Args:
            playbook: Datos del playbook
            case: Datos del caso
            execution_context: Contexto adicional
        
        Returns:
            Dict con predicción, probabilidad, y factores de riesgo
        """
        if not SKLEARN_AVAILABLE:
            return {
                "prediction": "unknown",
                "probability": 0.5,
                "confidence": 0.0,
                "risk_factors": ["ML not available"],
                "recommendation": "execute_with_monitoring"
            }
        
        playbook_id = playbook.get("id", "")
        
        # Check cache
        cache_key = f"{playbook_id}_{case.get('id', '') if case else ''}"
        if cache_key in self.prediction_cache:
            prob, cached_at = self.prediction_cache[cache_key]
            if (datetime.utcnow() - cached_at).seconds < PREDICTION_CACHE_TTL:
                return self._format_prediction(prob, playbook)
        
        # Check if model is trained
        if not self.is_trained:
            # Fall back to historical success rate
            historical_rate = playbook.get("success_rate", 0.7)
            return {
                "prediction": "likely_success" if historical_rate > 0.6 else "uncertain",
                "probability": historical_rate,
                "confidence": 0.3,  # Low confidence without ML
                "risk_factors": ["Model not trained yet"],
                "recommendation": "execute_with_monitoring",
                "model_status": "untrained"
            }
        
        try:
            # Extract features
            features = await self.extract_features(playbook, case, execution_context)
            
            # Scale features
            if self.scaler:
                features = self.scaler.transform(features)
            
            # Predict
            prob = self.model.predict_proba(features)[0][1]  # Probability of success
            
            # Cache result
            self.prediction_cache[cache_key] = (prob, datetime.utcnow())
            
            return self._format_prediction(prob, playbook)
            
        except Exception as e:
            logger.error(f"❌ Prediction error: {e}")
            return {
                "prediction": "error",
                "probability": 0.5,
                "confidence": 0.0,
                "risk_factors": [str(e)],
                "recommendation": "manual_review"
            }
    
    def _format_prediction(self, probability: float, playbook: Dict) -> Dict[str, Any]:
        """Formatear predicción con recomendaciones."""
        risk_factors = []
        
        # Analyze risk factors
        if playbook.get("success_rate", 1.0) < 0.5:
            risk_factors.append("Low historical success rate")
        if len(playbook.get("steps", [])) > 10:
            risk_factors.append("Complex playbook (>10 steps)")
        if playbook.get("requires_approval", False):
            risk_factors.append("Requires approval gates")
        if playbook.get("team_type") == "red":
            risk_factors.append("Red team playbook (higher risk)")
        
        # Determine prediction label and recommendation
        if probability >= 0.8:
            prediction = "likely_success"
            recommendation = "auto_execute"
            confidence = 0.9
        elif probability >= 0.6:
            prediction = "moderate_success"
            recommendation = "execute_with_monitoring"
            confidence = 0.7
        elif probability >= 0.4:
            prediction = "uncertain"
            recommendation = "manual_review"
            confidence = 0.5
        else:
            prediction = "likely_failure"
            recommendation = "defer_or_modify"
            confidence = 0.8
        
        return {
            "prediction": prediction,
            "probability": round(probability, 3),
            "confidence": round(confidence, 2),
            "risk_factors": risk_factors,
            "recommendation": recommendation,
            "model_status": "trained",
            "last_trained": self.last_trained.isoformat() if self.last_trained else None
        }
    
    async def train(self, force: bool = False) -> Dict[str, Any]:
        """
        Entrenar modelo con datos históricos de ejecuciones.
        
        Args:
            force: Forzar entrenamiento aunque no haya pasado el intervalo
        
        Returns:
            Métricas de entrenamiento
        """
        if not SKLEARN_AVAILABLE:
            return {"status": "error", "message": "scikit-learn not available"}
        
        # Check if retraining is needed
        if not force and self.last_trained:
            hours_since = (datetime.utcnow() - self.last_trained).seconds / 3600
            if hours_since < RETRAIN_INTERVAL_HOURS:
                return {
                    "status": "skipped",
                    "message": f"Model trained {hours_since:.1f}h ago. Next training in {RETRAIN_INTERVAL_HOURS - hours_since:.1f}h"
                }
        
        logger.info("🎓 Starting SOAR ML model training...")
        
        try:
            # Fetch training data
            X, y = await self._prepare_training_data()
            
            if len(X) < MIN_TRAINING_SAMPLES:
                return {
                    "status": "insufficient_data",
                    "message": f"Need {MIN_TRAINING_SAMPLES} samples, have {len(X)}",
                    "samples_available": len(X)
                }
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model (Random Forest with optimized hyperparameters)
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            
            self.training_metrics = {
                "accuracy": round(accuracy_score(y_test, y_pred), 3),
                "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
                "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
                "f1": round(f1_score(y_test, y_pred, zero_division=0), 3),
                "training_samples": len(X_train),
                "test_samples": len(X_test)
            }
            
            # Feature importance
            feature_importance = dict(zip(
                FEATURE_NAMES,
                [round(imp, 3) for imp in self.model.feature_importances_]
            ))
            self.training_metrics["feature_importance"] = feature_importance
            
            # Update state
            self.is_trained = True
            self.last_trained = datetime.utcnow()
            self.prediction_cache.clear()
            
            # Save model
            self._save_model()
            
            logger.info(f"✅ SOAR ML model trained. Accuracy: {self.training_metrics['accuracy']}")
            
            return {
                "status": "success",
                "metrics": self.training_metrics,
                "trained_at": self.last_trained.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Preparar datos de entrenamiento desde historial de ejecuciones."""
        X = []
        y = []
        
        with get_db_context() as db:
            from api.models.tools import PlaybookExecution, Playbook
            
            # Fetch completed executions (both success and failure)
            executions = db.query(PlaybookExecution).filter(
                PlaybookExecution.status.in_(["completed", "failed"])
            ).limit(10000).all()
            
            playbook_cache = {}
            
            for exec_record in executions:
                try:
                    # Get playbook data
                    if exec_record.playbook_id not in playbook_cache:
                        playbook = db.query(Playbook).filter(
                            Playbook.id == exec_record.playbook_id
                        ).first()
                        if playbook:
                            playbook_cache[exec_record.playbook_id] = {
                                "id": playbook.id,
                                "team_type": playbook.team_type or "blue",
                                "category": playbook.category or "general",
                                "trigger": playbook.trigger or "manual",
                                "steps": playbook.steps or [],
                                "requires_approval": playbook.requires_approval,
                                "success_rate": playbook.success_rate or 0.5
                            }
                    
                    playbook_data = playbook_cache.get(exec_record.playbook_id)
                    if not playbook_data:
                        continue
                    
                    # Extract features (sync version for training)
                    started_at = exec_record.started_at or datetime.utcnow()
                    
                    features = [
                        self._safe_encode_sync("playbook_type", playbook_data.get("team_type", "blue")),
                        self._safe_encode_sync("category", playbook_data.get("category", "general")),
                        self._safe_encode_sync("trigger", playbook_data.get("trigger", "manual")),
                        len(playbook_data.get("steps", [])),
                        1 if playbook_data.get("requires_approval") else 0,
                        started_at.hour,
                        started_at.weekday(),
                        playbook_data.get("success_rate", 0.5),
                        0,  # Recent failures (simplified for training)
                        5,  # Default execution time
                        1,  # Default priority (medium)
                        0.9  # Default tool availability
                    ]
                    
                    X.append(features)
                    y.append(1 if exec_record.status == "completed" else 0)
                    
                except Exception as e:
                    logger.debug(f"Skipping execution {exec_record.id}: {e}")
                    continue
        
        return np.array(X), np.array(y)
    
    def _safe_encode_sync(self, encoder_name: str, value: str) -> int:
        """Sync version of safe encoding for training."""
        encoder_map = {
            "playbook_type": ["blue", "red", "purple"],
            "category": ["general", "incident_response", "malware_analysis", "reconnaissance", "threat_hunting", "containment"],
            "trigger": ["manual", "on_ioc_create", "scheduled", "on_alert"],
            "priority": ["low", "medium", "high", "critical"]
        }
        
        if encoder_name not in self.encoders:
            self.encoders[encoder_name] = LabelEncoder()
            self.encoders[encoder_name].fit(encoder_map.get(encoder_name, [value]))
        
        try:
            return int(self.encoders[encoder_name].transform([value])[0])
        except ValueError:
            return 0


# =============================================================================
# PLAYBOOK RECOMMENDER
# =============================================================================

class PlaybookRecommender:
    """
    Sistema de recomendación de playbooks basado en contexto del caso.
    Usa ML para sugerir playbooks óptimos según historial y características.
    """
    
    def __init__(self, ml_model: SOARMLModel):
        self.ml_model = ml_model
    
    async def recommend(
        self,
        case: Dict,
        available_playbooks: List[Dict],
        max_recommendations: int = 5
    ) -> List[Dict]:
        """
        Recomendar playbooks para un caso.
        
        Args:
            case: Datos del caso
            available_playbooks: Lista de playbooks disponibles
            max_recommendations: Máximo de recomendaciones
        
        Returns:
            Lista de playbooks recomendados con scores
        """
        recommendations = []
        
        for playbook in available_playbooks:
            # Get ML prediction
            prediction = await self.ml_model.predict_success(playbook, case)
            
            # Calculate relevance score
            relevance = self._calculate_relevance(playbook, case)
            
            # Combined score (60% ML prediction, 40% relevance)
            combined_score = (
                prediction["probability"] * 0.6 +
                relevance * 0.4
            )
            
            recommendations.append({
                "playbook_id": playbook.get("id"),
                "playbook_name": playbook.get("name"),
                "score": round(combined_score, 3),
                "ml_prediction": prediction,
                "relevance_score": round(relevance, 3),
                "reasoning": self._generate_reasoning(playbook, case, prediction)
            })
        
        # Sort by score descending
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations[:max_recommendations]
    
    def _calculate_relevance(self, playbook: Dict, case: Dict) -> float:
        """Calcular relevancia del playbook para el caso."""
        score = 0.5  # Base score
        
        playbook_tags = set(playbook.get("tags", []))
        case_type = case.get("threat_type", "").lower()
        case_tags = set(case.get("tags", []))
        
        # Tag overlap
        if playbook_tags & case_tags:
            score += 0.2 * len(playbook_tags & case_tags)
        
        # Threat type matching
        if case_type:
            if case_type in playbook.get("name", "").lower():
                score += 0.15
            if case_type in playbook.get("description", "").lower():
                score += 0.1
        
        # Priority alignment
        case_priority = case.get("priority", "medium")
        if case_priority in ["high", "critical"] and playbook.get("team_type") == "blue":
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_reasoning(
        self,
        playbook: Dict,
        case: Dict,
        prediction: Dict
    ) -> str:
        """Generar explicación de la recomendación."""
        reasons = []
        
        prob = prediction.get("probability", 0.5)
        if prob >= 0.8:
            reasons.append(f"High success probability ({prob:.0%})")
        elif prob >= 0.6:
            reasons.append(f"Moderate success probability ({prob:.0%})")
        
        if prediction.get("risk_factors"):
            reasons.append(f"Risk factors: {', '.join(prediction['risk_factors'][:2])}")
        
        # Tag matching
        playbook_tags = set(playbook.get("tags", []))
        case_tags = set(case.get("tags", []))
        matching_tags = playbook_tags & case_tags
        if matching_tags:
            reasons.append(f"Matching tags: {', '.join(matching_tags)}")
        
        return " | ".join(reasons) if reasons else "General recommendation"


# =============================================================================
# OUTCOME TRACKER
# =============================================================================

class OutcomeTracker:
    """
    Rastrea outcomes de ejecuciones para feedback al modelo.
    Registra éxitos, fallos, y métricas para reentrenamiento.
    """
    
    def __init__(self, ml_model: SOARMLModel):
        self.ml_model = ml_model
    
    async def record_outcome(
        self,
        execution_id: str,
        playbook_id: str,
        success: bool,
        execution_time_seconds: float,
        steps_completed: int,
        steps_failed: int,
        error_message: Optional[str] = None,
        user_feedback: Optional[str] = None
    ):
        """
        Registrar outcome de una ejecución para aprendizaje.
        
        Args:
            execution_id: ID de la ejecución
            playbook_id: ID del playbook
            success: Si fue exitosa
            execution_time_seconds: Tiempo de ejecución
            steps_completed: Pasos completados
            steps_failed: Pasos fallidos
            error_message: Mensaje de error si aplica
            user_feedback: Feedback del usuario (opcional)
        """
        try:
            with get_db_context() as db:
                from api.models.tools import Playbook, PlaybookExecution
                
                # Update playbook success rate
                playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
                if playbook:
                    # Weighted moving average
                    total = playbook.execution_count or 0
                    current_rate = playbook.success_rate or 0.5
                    
                    if total > 0:
                        new_rate = ((current_rate * total) + (1.0 if success else 0.0)) / (total + 1)
                    else:
                        new_rate = 1.0 if success else 0.0
                    
                    playbook.success_rate = new_rate
                    playbook.execution_count = total + 1
                    playbook.last_executed_at = datetime.utcnow()
                    
                    # Update avg execution time
                    if not hasattr(playbook, 'avg_execution_time_seconds') or not playbook.avg_execution_time_seconds:
                        playbook.avg_execution_time_seconds = execution_time_seconds
                    else:
                        playbook.avg_execution_time_seconds = (
                            (playbook.avg_execution_time_seconds * total + execution_time_seconds) / (total + 1)
                        )
                    
                    db.commit()
                    
                    logger.info(
                        f"📊 Outcome recorded for {playbook_id}: "
                        f"{'✅ success' if success else '❌ failed'}, "
                        f"new rate: {new_rate:.2%}"
                    )
                
                # Clear prediction cache for this playbook
                cache_keys_to_remove = [
                    k for k in self.ml_model.prediction_cache
                    if k.startswith(playbook_id)
                ]
                for key in cache_keys_to_remove:
                    del self.ml_model.prediction_cache[key]
                
        except Exception as e:
            logger.error(f"❌ Failed to record outcome: {e}")
    
    async def trigger_retraining_if_needed(self):
        """Verificar si es necesario reentrenar el modelo."""
        if not self.ml_model.last_trained:
            await self.ml_model.train()
            return
        
        hours_since = (datetime.utcnow() - self.ml_model.last_trained).total_seconds() / 3600
        if hours_since >= RETRAIN_INTERVAL_HOURS:
            logger.info("🔄 Triggering scheduled model retraining...")
            await self.ml_model.train()


# =============================================================================
# SINGLETON INSTANCES
# =============================================================================

_ml_model: Optional[SOARMLModel] = None
_recommender: Optional[PlaybookRecommender] = None
_tracker: Optional[OutcomeTracker] = None


def get_soar_ml_model() -> SOARMLModel:
    """Get or create SOAR ML model singleton."""
    global _ml_model
    if _ml_model is None:
        _ml_model = SOARMLModel()
    return _ml_model


def get_playbook_recommender() -> PlaybookRecommender:
    """Get or create playbook recommender singleton."""
    global _recommender
    if _recommender is None:
        _recommender = PlaybookRecommender(get_soar_ml_model())
    return _recommender


def get_outcome_tracker() -> OutcomeTracker:
    """Get or create outcome tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = OutcomeTracker(get_soar_ml_model())
    return _tracker


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def predict_playbook_success(
    playbook: Dict,
    case: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convenience function to predict playbook success.
    
    Args:
        playbook: Playbook data
        case: Case data (optional)
    
    Returns:
        Prediction result
    """
    model = get_soar_ml_model()
    return await model.predict_success(playbook, case)


async def recommend_playbooks_for_case(
    case: Dict,
    available_playbooks: List[Dict],
    max_recommendations: int = 5
) -> List[Dict]:
    """
    Convenience function to get playbook recommendations.
    
    Args:
        case: Case data
        available_playbooks: List of available playbooks
        max_recommendations: Max number of recommendations
    
    Returns:
        List of recommended playbooks with scores
    """
    recommender = get_playbook_recommender()
    return await recommender.recommend(case, available_playbooks, max_recommendations)


async def record_execution_outcome(
    execution_id: str,
    playbook_id: str,
    success: bool,
    execution_time_seconds: float,
    steps_completed: int = 0,
    steps_failed: int = 0,
    error_message: Optional[str] = None
):
    """
    Convenience function to record execution outcome.
    
    Args:
        execution_id: Execution ID
        playbook_id: Playbook ID
        success: Whether execution succeeded
        execution_time_seconds: How long it took
        steps_completed: Number of steps completed
        steps_failed: Number of steps failed
        error_message: Error message if failed
    """
    tracker = get_outcome_tracker()
    await tracker.record_outcome(
        execution_id=execution_id,
        playbook_id=playbook_id,
        success=success,
        execution_time_seconds=execution_time_seconds,
        steps_completed=steps_completed,
        steps_failed=steps_failed,
        error_message=error_message
    )
    await tracker.trigger_retraining_if_needed()


async def train_soar_ml_model(force: bool = False) -> Dict[str, Any]:
    """
    Convenience function to train the ML model.
    
    Args:
        force: Force training even if recently trained
    
    Returns:
        Training result
    """
    model = get_soar_ml_model()
    return await model.train(force=force)
