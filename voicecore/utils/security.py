"""
Security utilities for VoiceCore AI.

Provides security-related functions including data sanitization,
encryption, and privacy compliance utilities.
"""

import re
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from voicecore.config import settings
from voicecore.logging import get_logger


logger = get_logger(__name__)


class SecurityUtils:
    """
    Security utilities for data protection and privacy compliance.
    
    CRITICAL: This class ensures no IP addresses, geolocation, or
    location data is stored or logged per security requirements.
    """
    
    # Sensitive data patterns that must be redacted
    SENSITIVE_PATTERNS = {
        'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        'ipv6_address': r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
        'phone_number': r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'coordinates': r'\b-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+\b'
    }
    
    # Location-related keywords that indicate sensitive data
    LOCATION_KEYWORDS = [
        'latitude', 'longitude', 'lat', 'lng', 'coordinates',
        'geolocation', 'location', 'address', 'city', 'state',
        'country', 'zip', 'postal', 'gps', 'position'
    ]
    
    @staticmethod
    def sanitize_data(data: Union[Dict, List, str, Any]) -> Union[Dict, List, str, Any]:
        """
        Sanitize data to remove sensitive information.
        
        CRITICAL: This function ensures compliance with privacy requirements
        by removing IP addresses, geolocation, and other sensitive data.
        
        Args:
            data: Data to sanitize (dict, list, string, or other)
            
        Returns:
            Sanitized data with sensitive information redacted
        """
        if isinstance(data, dict):
            return SecurityUtils._sanitize_dict(data)
        elif isinstance(data, list):
            return [SecurityUtils.sanitize_data(item) for item in data]
        elif isinstance(data, str):
            return SecurityUtils._sanitize_string(data)
        else:
            return data
    
    @staticmethod
    def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary data."""
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key indicates sensitive data
            if any(keyword in key_lower for keyword in SecurityUtils.LOCATION_KEYWORDS):
                sanitized[key] = "[REDACTED_LOCATION]"
            elif 'ip' in key_lower or 'addr' in key_lower:
                sanitized[key] = "[REDACTED_IP]"
            elif 'password' in key_lower or 'secret' in key_lower or 'token' in key_lower:
                sanitized[key] = "[REDACTED_SECRET]"
            else:
                sanitized[key] = SecurityUtils.sanitize_data(value)
        
        return sanitized
    
    @staticmethod
    def _sanitize_string(text: str) -> str:
        """Sanitize string data by removing sensitive patterns."""
        if not isinstance(text, str):
            return text
        
        sanitized = text
        
        # Remove sensitive patterns
        for pattern_name, pattern in SecurityUtils.SENSITIVE_PATTERNS.items():
            if pattern_name in ['ip_address', 'ipv6_address', 'coordinates']:
                # These are completely redacted for privacy compliance
                sanitized = re.sub(pattern, '[REDACTED_LOCATION]', sanitized)
            elif pattern_name == 'phone_number':
                # Partially redact phone numbers
                sanitized = re.sub(pattern, 'XXX-XXX-XXXX', sanitized)
            elif pattern_name == 'email':
                # Partially redact emails
                sanitized = re.sub(pattern, 'user@domain.com', sanitized)
            else:
                sanitized = re.sub(pattern, f'[REDACTED_{pattern_name.upper()}]', sanitized)
        
        return sanitized
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a secure correlation ID for request tracking."""
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def hash_phone_number(phone_number: str) -> str:
        """
        Create a privacy-compliant hash of a phone number.
        
        This allows for duplicate detection and analytics without
        storing the actual phone number.
        """
        # Normalize phone number (remove non-digits)
        normalized = re.sub(r'\D', '', phone_number)
        
        # Create hash with salt
        salt = settings.secret_key.encode()
        hash_obj = hashlib.pbkdf2_hmac('sha256', normalized.encode(), salt, 100000)
        return base64.b64encode(hash_obj).decode()
    
    @staticmethod
    def encrypt_sensitive_data(data: str) -> str:
        """
        Encrypt sensitive data for storage.
        
        Uses Fernet symmetric encryption for secure data storage.
        """
        try:
            # Derive key from settings
            password = settings.secret_key.encode()
            salt = b'voicecore_salt_2024'  # In production, use random salt per record
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Encrypt data
            f = Fernet(key)
            encrypted_data = f.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error("Failed to encrypt sensitive data", error=str(e))
            raise
    
    @staticmethod
    def decrypt_sensitive_data(encrypted_data: str) -> str:
        """
        Decrypt sensitive data from storage.
        
        Decrypts data that was encrypted with encrypt_sensitive_data.
        """
        try:
            # Derive same key
            password = settings.secret_key.encode()
            salt = b'voicecore_salt_2024'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Decrypt data
            f = Fernet(key)
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = f.decrypt(decoded_data)
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error("Failed to decrypt sensitive data", error=str(e))
            raise
    
    @staticmethod
    def validate_phone_number(phone_number: str) -> bool:
        """
        Validate phone number format without storing the actual number.
        
        Returns True if the phone number appears to be valid.
        """
        if not phone_number:
            return False
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone_number)
        
        # Check if it's a valid length (10-15 digits)
        if len(digits_only) < 10 or len(digits_only) > 15:
            return False
        
        # Check if it starts with valid country codes
        if len(digits_only) == 11 and digits_only.startswith('1'):
            return True  # US/Canada number
        elif len(digits_only) == 10:
            return True  # US number without country code
        elif len(digits_only) >= 10:
            return True  # International number
        
        return False
    
    @staticmethod
    def is_request_from_trusted_source(request_headers: Dict[str, str]) -> bool:
        """
        Check if request comes from a trusted source without logging IP.
        
        This function validates requests without storing or logging
        IP addresses or location data.
        """
        # Check for required headers that indicate legitimate requests
        required_headers = ['user-agent', 'accept']
        
        for header in required_headers:
            if header not in request_headers:
                return False
        
        # Check for suspicious patterns in user agent
        user_agent = request_headers.get('user-agent', '').lower()
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'scanner'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in user_agent:
                return False
        
        return True
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """
        Compare two strings in constant time to prevent timing attacks.
        """
        return secrets.compare_digest(a.encode(), b.encode())


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize data before logging to ensure privacy compliance.
    
    This is a convenience function that wraps SecurityUtils.sanitize_data
    specifically for logging purposes.
    """
    return SecurityUtils.sanitize_data(data)


def generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return SecurityUtils.generate_correlation_id()


def hash_identifier(identifier: str) -> str:
    """
    Hash an identifier for privacy-compliant storage.
    
    Useful for phone numbers, emails, or other identifiers that need
    to be stored for analytics but not in plain text.
    """
    return SecurityUtils.hash_phone_number(identifier)