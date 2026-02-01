"""
Tests for security utilities.

Validates that security functions work correctly and maintain
privacy compliance by not storing sensitive data.
"""

import pytest
from voicecore.utils.security import SecurityUtils, sanitize_log_data


class TestSecurityUtils:
    """Test security utility functions."""
    
    def test_sanitize_ip_addresses(self):
        """Test that IP addresses are properly redacted."""
        data = {
            "client_ip": "192.168.1.1",
            "remote_addr": "10.0.0.1",
            "message": "User from 172.16.0.1 connected"
        }
        
        sanitized = SecurityUtils.sanitize_data(data)
        
        assert sanitized["client_ip"] == "[REDACTED_IP]"
        assert sanitized["remote_addr"] == "[REDACTED_IP]"
        assert "172.16.0.1" not in sanitized["message"]
        assert "[REDACTED_LOCATION]" in sanitized["message"]
    
    def test_sanitize_location_data(self):
        """Test that location data is properly redacted."""
        data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "geolocation": "New York, NY",
            "coordinates": "40.7128, -74.0060"
        }
        
        sanitized = SecurityUtils.sanitize_data(data)
        
        assert sanitized["latitude"] == "[REDACTED_LOCATION]"
        assert sanitized["longitude"] == "[REDACTED_LOCATION]"
        assert sanitized["geolocation"] == "[REDACTED_LOCATION]"
        assert "40.7128" not in str(sanitized["coordinates"])
    
    def test_sanitize_phone_numbers(self):
        """Test that phone numbers are properly sanitized."""
        text = "Call me at +1-555-123-4567 or 555.987.6543"
        sanitized = SecurityUtils._sanitize_string(text)
        
        assert "555-123-4567" not in sanitized
        assert "555.987.6543" not in sanitized
        assert "XXX-XXX-XXXX" in sanitized
    
    def test_hash_phone_number(self):
        """Test phone number hashing for privacy compliance."""
        phone1 = "+1-555-123-4567"
        phone2 = "5551234567"  # Same number, different format
        phone3 = "+1-555-987-6543"  # Different number
        
        hash1 = SecurityUtils.hash_phone_number(phone1)
        hash2 = SecurityUtils.hash_phone_number(phone2)
        hash3 = SecurityUtils.hash_phone_number(phone3)
        
        # Same number should produce same hash
        assert hash1 == hash2
        
        # Different numbers should produce different hashes
        assert hash1 != hash3
        
        # Hash should not contain original number
        assert "555" not in hash1
        assert "123" not in hash1
    
    def test_validate_phone_number(self):
        """Test phone number validation."""
        valid_numbers = [
            "+1-555-123-4567",
            "555-123-4567",
            "5551234567",
            "+44 20 7946 0958"  # UK number
        ]
        
        invalid_numbers = [
            "123",  # Too short
            "abc-def-ghij",  # Not numeric
            "",  # Empty
            "555-123-456789012345"  # Too long
        ]
        
        for number in valid_numbers:
            assert SecurityUtils.validate_phone_number(number), f"Should be valid: {number}"
        
        for number in invalid_numbers:
            assert not SecurityUtils.validate_phone_number(number), f"Should be invalid: {number}"
    
    def test_encryption_decryption(self):
        """Test data encryption and decryption."""
        original_data = "sensitive information"
        
        # Encrypt data
        encrypted = SecurityUtils.encrypt_sensitive_data(original_data)
        assert encrypted != original_data
        assert original_data not in encrypted
        
        # Decrypt data
        decrypted = SecurityUtils.decrypt_sensitive_data(encrypted)
        assert decrypted == original_data
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = SecurityUtils.generate_secure_token()
        token2 = SecurityUtils.generate_secure_token()
        
        # Tokens should be different
        assert token1 != token2
        
        # Tokens should be reasonable length
        assert len(token1) > 20
        assert len(token2) > 20
    
    def test_constant_time_compare(self):
        """Test constant time string comparison."""
        string1 = "secret_value"
        string2 = "secret_value"
        string3 = "different_value"
        
        assert SecurityUtils.constant_time_compare(string1, string2)
        assert not SecurityUtils.constant_time_compare(string1, string3)
    
    def test_sanitize_log_data_function(self):
        """Test the convenience function for log data sanitization."""
        data = {
            "user_id": "12345",
            "client_ip": "192.168.1.1",
            "action": "login"
        }
        
        sanitized = sanitize_log_data(data)
        
        assert sanitized["user_id"] == "12345"  # Should be preserved
        assert sanitized["client_ip"] == "[REDACTED_IP]"  # Should be redacted
        assert sanitized["action"] == "login"  # Should be preserved


if __name__ == "__main__":
    pytest.main([__file__])