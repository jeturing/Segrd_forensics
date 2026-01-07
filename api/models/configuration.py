"""
MCP Kali Forensics - Configuration Model
Modelo para guardar configuraciones de API en base de datos
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
import enum

from api.database import Base


class ConfigCategory(str, enum.Enum):
    """Categorías de configuración"""
    THREAT_INTEL = "threat_intel"
    IDENTITY = "identity"
    MALWARE = "malware"
    NETWORK = "network"
    CREDENTIALS = "credentials"
    CLOUD = "cloud"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"
    GENERAL = "general"


class ApiConfiguration(Base):
    """
    Modelo para almacenar configuraciones de API
    Solo configuraciones OPCIONALES - las requeridas vienen del .env
    """
    __tablename__ = "api_configurations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identificación
    key = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Categoría
    category = Column(SQLEnum(ConfigCategory), default=ConfigCategory.GENERAL)
    
    # Valor (encriptado en producción)
    value = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=True)  # Si es API key/secret
    
    # Metadatos
    service_name = Column(String(100), nullable=True)  # Shodan, VirusTotal, etc.
    service_url = Column(String(500), nullable=True)   # URL de documentación
    
    # Estado
    is_enabled = Column(Boolean, default=True)
    is_configured = Column(Boolean, default=False)
    last_validated = Column(DateTime, nullable=True)
    validation_status = Column(String(50), nullable=True)  # valid, invalid, unknown
    
    # Auditoría
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<ApiConfiguration(key='{self.key}', service='{self.service_name}')>"

    def to_dict(self, include_value: bool = False):
        """Convertir a diccionario, ocultando valores secretos por defecto"""
        result = {
            "id": self.id,
            "key": self.key,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value if self.category else None,
            "service_name": self.service_name,
            "service_url": self.service_url,
            "is_secret": self.is_secret,
            "is_enabled": self.is_enabled,
            "is_configured": self.is_configured,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "validation_status": self.validation_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_value and not self.is_secret:
            result["value"] = self.value
        elif include_value and self.is_secret and self.value:
            # Mostrar solo últimos 4 caracteres para secretos
            result["value"] = "•" * 20 + self.value[-4:] if len(self.value) > 4 else "••••"
            result["has_value"] = True
        else:
            result["has_value"] = bool(self.value)
            
        return result


class SystemSetting(Base):
    """
    Configuraciones del sistema que NO son API keys
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, bool, json
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general")
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemSetting(key='{self.key}')>"

    def get_typed_value(self):
        """Obtener valor con tipo correcto"""
        if self.value is None:
            return None
        if self.value_type == "int":
            return int(self.value)
        if self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        if self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value
