"""
Real-time translation service for VoiceCore AI 2.0.

Provides real-time translation during active calls with caching
and quality monitoring.
"""

import uuid
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime

from voicecore.config import settings
from voicecore.logging import get_logger
from voicecore.services.cache_service import cache_service

logger = get_logger(__name__)


class TranslationService:
    """
    Service for real-time translation during calls.
    
    Provides translation with caching for common phrases and
    quality monitoring for translation accuracy.
    """
    
    def __init__(self):
        self.logger = logger
        self.translation_cache_ttl = 86400  # 24 hours
        
        # Common phrases cache (pre-populated)
        self.common_phrases = {
            "en": {
                "hello": {"es": "hola", "fr": "bonjour", "de": "hallo", "it": "ciao", "pt": "olá"},
                "thank you": {"es": "gracias", "fr": "merci", "de": "danke", "it": "grazie", "pt": "obrigado"},
                "goodbye": {"es": "adiós", "fr": "au revoir", "de": "auf wiedersehen", "it": "arrivederci", "pt": "adeus"},
                "yes": {"es": "sí", "fr": "oui", "de": "ja", "it": "sì", "pt": "sim"},
                "no": {"es": "no", "fr": "non", "de": "nein", "it": "no", "pt": "não"},
                "please": {"es": "por favor", "fr": "s'il vous plaît", "de": "bitte", "it": "per favore", "pt": "por favor"},
                "help": {"es": "ayuda", "fr": "aide", "de": "hilfe", "it": "aiuto", "pt": "ajuda"}
            }
        }
    
    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate text from source to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context for better translation
            
        Returns:
            Dict with translation result
        """
        try:
            # Check if same language
            if source_lang == target_lang:
                return {
                    "translated_text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "cached": False,
                    "confidence": 1.0
                }
            
            # Check cache first
            cache_key = self._get_cache_key(text, source_lang, target_lang)
            cached = await cache_service.get(cache_key)
            
            if cached:
                import json
                result = json.loads(cached)
                result["cached"] = True
                return result
            
            # Check common phrases
            text_lower = text.lower().strip()
            if source_lang in self.common_phrases:
                if text_lower in self.common_phrases[source_lang]:
                    if target_lang in self.common_phrases[source_lang][text_lower]:
                        translated = self.common_phrases[source_lang][text_lower][target_lang]
                        result = {
                            "translated_text": translated,
                            "source_lang": source_lang,
                            "target_lang": target_lang,
                            "cached": True,
                            "confidence": 1.0,
                            "method": "common_phrase"
                        }
                        return result
            
            # Perform translation (placeholder - integrate with Google Translate or DeepL API)
            translated_text = await self._perform_translation(
                text, source_lang, target_lang, context
            )
            
            result = {
                "translated_text": translated_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "cached": False,
                "confidence": 0.95,  # Would come from translation API
                "method": "api"
            }
            
            # Cache the result
            import json
            await cache_service.set(
                cache_key,
                json.dumps(result),
                ttl=self.translation_cache_ttl
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Translation failed", error=str(e))
            return {
                "translated_text": text,  # Return original on error
                "source_lang": source_lang,
                "target_lang": target_lang,
                "cached": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def translate_conversation_turn(
        self,
        turn: Dict[str, Any],
        target_lang: str
    ) -> Dict[str, Any]:
        """
        Translate a conversation turn.
        
        Args:
            turn: Conversation turn with role and content
            target_lang: Target language code
            
        Returns:
            Dict with translated turn
        """
        try:
            content = turn.get("content", "")
            source_lang = turn.get("language", "en")
            
            translation = await self.translate_text(
                content,
                source_lang,
                target_lang
            )
            
            return {
                "role": turn.get("role"),
                "content": translation["translated_text"],
                "original_content": content,
                "language": target_lang,
                "original_language": source_lang,
                "translation_confidence": translation.get("confidence", 0.0),
                "timestamp": turn.get("timestamp", datetime.utcnow().isoformat())
            }
            
        except Exception as e:
            self.logger.error("Failed to translate conversation turn", error=str(e))
            return turn
    
    async def translate_transcript(
        self,
        transcript: List[Dict[str, Any]],
        target_lang: str
    ) -> List[Dict[str, Any]]:
        """
        Translate entire conversation transcript.
        
        Args:
            transcript: List of conversation turns
            target_lang: Target language code
            
        Returns:
            List of translated turns
        """
        try:
            translated_transcript = []
            
            for turn in transcript:
                translated_turn = await self.translate_conversation_turn(
                    turn,
                    target_lang
                )
                translated_transcript.append(translated_turn)
            
            return translated_transcript
            
        except Exception as e:
            self.logger.error("Failed to translate transcript", error=str(e))
            return transcript
    
    async def get_translation_quality_metrics(
        self,
        call_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get translation quality metrics for a call.
        
        Args:
            call_id: Call UUID
            
        Returns:
            Dict with quality metrics
        """
        try:
            # This would track translation quality during the call
            # For now, return placeholder metrics
            return {
                "call_id": str(call_id),
                "translations_count": 0,
                "avg_confidence": 0.0,
                "cached_translations": 0,
                "api_translations": 0,
                "failed_translations": 0
            }
            
        except Exception as e:
            self.logger.error("Failed to get translation metrics", error=str(e))
            return {}
    
    async def add_common_phrase(
        self,
        phrase: str,
        source_lang: str,
        translations: Dict[str, str]
    ) -> bool:
        """
        Add a common phrase to the cache.
        
        Args:
            phrase: Phrase in source language
            source_lang: Source language code
            translations: Dict of target_lang: translation
            
        Returns:
            bool: True if successful
        """
        try:
            if source_lang not in self.common_phrases:
                self.common_phrases[source_lang] = {}
            
            phrase_lower = phrase.lower().strip()
            self.common_phrases[source_lang][phrase_lower] = translations
            
            self.logger.info(
                "Common phrase added",
                phrase=phrase,
                source_lang=source_lang,
                target_langs=list(translations.keys())
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to add common phrase", error=str(e))
            return False
    
    def _get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key for translation."""
        content = f"{text}:{source_lang}:{target_lang}"
        return f"translation:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def _perform_translation(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ) -> str:
        """
        Perform actual translation using external API.
        
        This is a placeholder - integrate with Google Translate API or DeepL API.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context
            
        Returns:
            str: Translated text
        """
        # TODO: Integrate with Google Translate API or DeepL API
        # For now, return a placeholder
        
        # Example Google Translate API integration:
        # from google.cloud import translate_v2 as translate
        # translate_client = translate.Client()
        # result = translate_client.translate(
        #     text,
        #     source_language=source_lang,
        #     target_language=target_lang
        # )
        # return result['translatedText']
        
        # Placeholder: return original text with language indicator
        return f"[{target_lang}] {text}"
    
    async def get_supported_translation_pairs(self) -> List[Dict[str, str]]:
        """
        Get list of supported translation language pairs.
        
        Returns:
            List of language pair dicts
        """
        # All combinations of supported languages
        languages = ["en", "es", "fr", "de", "it", "pt"]
        pairs = []
        
        for source in languages:
            for target in languages:
                if source != target:
                    pairs.append({
                        "source": source,
                        "target": target
                    })
        
        return pairs


# Global instance
translation_service = TranslationService()
