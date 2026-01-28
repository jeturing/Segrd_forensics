"""
Encryption Service - Fernet-based encryption for secrets
=========================================================
Encripta valores sensibles en la base de datos usando Fernet (AES-128-CBC).
"""

import os
import base64
import logging
from typing import Optional
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Servicio de encriptación para valores sensibles en BD.
    Usa Fernet (simétrica) con clave derivada de ENCRYPTION_KEY.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Inicializa el servicio de encriptación.
        
        Args:
            encryption_key: Clave de encriptación. Si no se proporciona,
                           se lee de ENCRYPTION_KEY en .env
        """
        self._key = encryption_key or os.getenv("ENCRYPTION_KEY")
        self._fernet: Optional[Fernet] = None
        
        if self._key:
            self._fernet = self._create_fernet(self._key)
            logger.info("🔐 Encryption service initialized")
        else:
            logger.warning("⚠️ ENCRYPTION_KEY not set - secrets will NOT be encrypted")
    
    def _create_fernet(self, key: str) -> Fernet:
        """
        Crea instancia Fernet derivando clave con PBKDF2.
        Esto permite usar cualquier string como clave.
        """
        # Derivar clave de 32 bytes usando PBKDF2
        salt = b'mcp-kali-forensics-v4.7'  # Salt fijo (OK para este uso)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(derived_key)
    
    @property
    def is_enabled(self) -> bool:
        """Retorna True si la encriptación está habilitada."""
        return self._fernet is not None
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encripta un string.
        
        Args:
            plaintext: Texto a encriptar
            
        Returns:
            Texto encriptado en base64, prefijado con 'enc:'
        """
        if not self._fernet:
            logger.warning("Encryption disabled - storing plaintext")
            return plaintext
        
        if not plaintext:
            return plaintext
            
        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return f"enc:{encrypted.decode()}"
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return plaintext
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Desencripta un string.
        
        Args:
            ciphertext: Texto encriptado (prefijado con 'enc:')
            
        Returns:
            Texto desencriptado
        """
        if not self._fernet:
            return ciphertext
        
        if not ciphertext:
            return ciphertext
            
        # Si no tiene prefijo, no está encriptado
        if not ciphertext.startswith("enc:"):
            return ciphertext
        
        try:
            encrypted_data = ciphertext[4:]  # Quitar 'enc:'
            decrypted = self._fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed - invalid token or wrong key")
            return "[DECRYPTION_ERROR]"
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ciphertext
    
    def is_encrypted(self, value: str) -> bool:
        """Verifica si un valor está encriptado."""
        return bool(value) and value.startswith("enc:")
    
    def mask_secret(self, value: str, visible_chars: int = 4) -> str:
        """
        Enmascara un valor secreto mostrando solo los últimos N caracteres.
        
        Args:
            value: Valor a enmascarar
            visible_chars: Cantidad de caracteres visibles al final
            
        Returns:
            Valor enmascarado: "••••••••xxxx"
        """
        if not value:
            return ""
        
        # Desencriptar primero si es necesario
        plaintext = self.decrypt(value) if self.is_encrypted(value) else value
        
        if len(plaintext) <= visible_chars:
            return "•" * len(plaintext)
        
        return "•" * (len(plaintext) - visible_chars) + plaintext[-visible_chars:]


# Singleton
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Obtiene la instancia singleton del servicio de encriptación."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_value(value: str) -> str:
    """Atajo para encriptar un valor."""
    return get_encryption_service().encrypt(value)


def decrypt_value(value: str) -> str:
    """Atajo para desencriptar un valor."""
    return get_encryption_service().decrypt(value)


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Atajo para enmascarar un secreto."""
    return get_encryption_service().mask_secret(value, visible_chars)
