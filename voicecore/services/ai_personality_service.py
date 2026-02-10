"""
AI Personality Management Service for VoiceCore AI 2.0.

Manages custom AI personalities per tenant with voice settings,
conversation styles, and knowledge base management.
"""

import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from voicecore.config import settings
from voicecore.database import get_db_session, set_tenant_context
from voicecore.models.ai_personality import AIPersonality, ConversationTemplate
from voicecore.logging import get_logger
from voicecore.services.cache_service import cache_service

logger = get_logger(__name__)


class AIPersonalityService:
    """
    Service for managing custom AI personalities.
    
    Enables tenants to create and manage custom AI personalities with
    unique voice settings, conversation styles, and knowledge bases.
    """
    
    def __init__(self):
        self.logger = logger
    
    async def create_personality(
        self,
        tenant_id: uuid.UUID,
        name: str,
        description: str,
        voice_settings: Dict[str, Any],
        conversation_style: str,
        knowledge_base: Optional[List[str]] = None,
        is_default: bool = False
    ) -> Optional[uuid.UUID]:
        """
        Create a new AI personality.
        
        Args:
            tenant_id: Tenant UUID
            name: Personality name
            description: Personality description
            voice_settings: Voice configuration (language, voice, speed, pitch)
            conversation_style: Conversation style description
            knowledge_base: Optional list of knowledge base entries
            is_default: Whether this is the default personality
            
        Returns:
            UUID of created personality or None
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # If setting as default, unset other defaults
                if is_default:
                    await session.execute(
                        """
                        UPDATE ai_personalities
                        SET is_default = FALSE
                        WHERE tenant_id = :tenant_id
                        """,
                        {"tenant_id": tenant_id}
                    )
                
                # Create personality
                personality_id = uuid.uuid4()
                personality = AIPersonality(
                    id=personality_id,
                    tenant_id=tenant_id,
                    name=name,
                    description=description,
                    voice_settings=voice_settings,
                    conversation_style=conversation_style,
                    knowledge_base=knowledge_base or [],
                    is_default=is_default,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                
                session.add(personality)
                await session.commit()
                
                # Clear cache
                await self._clear_personality_cache(tenant_id)
                
                self.logger.info(
                    "AI personality created",
                    tenant_id=str(tenant_id),
                    personality_id=str(personality_id),
                    name=name
                )
                
                return personality_id
                
        except Exception as e:
            self.logger.error("Failed to create AI personality", error=str(e))
            return None
    
    async def get_personality(
        self,
        personality_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI personality by ID.
        
        Args:
            personality_id: Personality UUID
            
        Returns:
            Dict with personality details or None
        """
        try:
            # Check cache
            cache_key = f"personality:{personality_id}"
            cached = await cache_service.get(cache_key)
            if cached:
                return json.loads(cached)
            
            async with get_db_session() as session:
                result = await session.execute(
                    """
                    SELECT id, tenant_id, name, description, voice_settings,
                           conversation_style, knowledge_base, is_default, is_active,
                           created_at, updated_at
                    FROM ai_personalities
                    WHERE id = :personality_id
                    """,
                    {"personality_id": personality_id}
                )
                
                row = result.fetchone()
                
                if not row:
                    return None
                
                personality = {
                    "id": str(row[0]),
                    "tenant_id": str(row[1]),
                    "name": row[2],
                    "description": row[3],
                    "voice_settings": row[4],
                    "conversation_style": row[5],
                    "knowledge_base": row[6],
                    "is_default": row[7],
                    "is_active": row[8],
                    "created_at": row[9].isoformat() if row[9] else None,
                    "updated_at": row[10].isoformat() if row[10] else None
                }
                
                # Cache for 30 minutes
                await cache_service.set(cache_key, json.dumps(personality), ttl=1800)
                
                return personality
                
        except Exception as e:
            self.logger.error("Failed to get AI personality", error=str(e))
            return None
    
    async def get_tenant_personalities(
        self,
        tenant_id: uuid.UUID,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all personalities for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            include_inactive: Whether to include inactive personalities
            
        Returns:
            List of personality dicts
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                query = """
                    SELECT id, name, description, voice_settings, conversation_style,
                           is_default, is_active, created_at
                    FROM ai_personalities
                    WHERE tenant_id = :tenant_id
                """
                
                if not include_inactive:
                    query += " AND is_active = TRUE"
                
                query += " ORDER BY is_default DESC, created_at DESC"
                
                result = await session.execute(query, {"tenant_id": tenant_id})
                
                personalities = []
                for row in result.fetchall():
                    personalities.append({
                        "id": str(row[0]),
                        "name": row[1],
                        "description": row[2],
                        "voice_settings": row[3],
                        "conversation_style": row[4],
                        "is_default": row[5],
                        "is_active": row[6],
                        "created_at": row[7].isoformat() if row[7] else None
                    })
                
                return personalities
                
        except Exception as e:
            self.logger.error("Failed to get tenant personalities", error=str(e))
            return []
    
    async def get_default_personality(
        self,
        tenant_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get default personality for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Dict with personality details or None
        """
        try:
            # Check cache
            cache_key = f"default_personality:{tenant_id}"
            cached = await cache_service.get(cache_key)
            if cached:
                return json.loads(cached)
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    """
                    SELECT id, name, description, voice_settings, conversation_style,
                           knowledge_base
                    FROM ai_personalities
                    WHERE tenant_id = :tenant_id
                      AND is_default = TRUE
                      AND is_active = TRUE
                    LIMIT 1
                    """,
                    {"tenant_id": tenant_id}
                )
                
                row = result.fetchone()
                
                if not row:
                    return None
                
                personality = {
                    "id": str(row[0]),
                    "name": row[1],
                    "description": row[2],
                    "voice_settings": row[3],
                    "conversation_style": row[4],
                    "knowledge_base": row[5]
                }
                
                # Cache for 30 minutes
                await cache_service.set(cache_key, json.dumps(personality), ttl=1800)
                
                return personality
                
        except Exception as e:
            self.logger.error("Failed to get default personality", error=str(e))
            return None
    
    async def update_personality(
        self,
        personality_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update AI personality.
        
        Args:
            personality_id: Personality UUID
            updates: Dict of fields to update
            
        Returns:
            bool: True if successful
        """
        try:
            async with get_db_session() as session:
                # Build update query
                set_clauses = []
                params = {"personality_id": personality_id, "updated_at": datetime.utcnow()}
                
                for key, value in updates.items():
                    if key in ["name", "description", "conversation_style", "is_active"]:
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value
                    elif key in ["voice_settings", "knowledge_base"]:
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
                
                if not set_clauses:
                    return False
                
                set_clauses.append("updated_at = :updated_at")
                
                query = f"""
                    UPDATE ai_personalities
                    SET {', '.join(set_clauses)}
                    WHERE id = :personality_id
                """
                
                await session.execute(query, params)
                await session.commit()
                
                # Clear cache
                await cache_service.delete(f"personality:{personality_id}")
                
                # Get tenant_id to clear tenant cache
                result = await session.execute(
                    "SELECT tenant_id FROM ai_personalities WHERE id = :personality_id",
                    {"personality_id": personality_id}
                )
                row = result.fetchone()
                if row:
                    await self._clear_personality_cache(row[0])
                
                self.logger.info("AI personality updated", personality_id=str(personality_id))
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to update AI personality", error=str(e))
            return False
    
    async def delete_personality(
        self,
        personality_id: uuid.UUID
    ) -> bool:
        """
        Delete (deactivate) AI personality.
        
        Args:
            personality_id: Personality UUID
            
        Returns:
            bool: True if successful
        """
        try:
            async with get_db_session() as session:
                # Soft delete by setting is_active = FALSE
                await session.execute(
                    """
                    UPDATE ai_personalities
                    SET is_active = FALSE, updated_at = :updated_at
                    WHERE id = :personality_id
                    """,
                    {"personality_id": personality_id, "updated_at": datetime.utcnow()}
                )
                await session.commit()
                
                # Clear cache
                await cache_service.delete(f"personality:{personality_id}")
                
                self.logger.info("AI personality deleted", personality_id=str(personality_id))
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to delete AI personality", error=str(e))
            return False
    
    async def add_knowledge_entry(
        self,
        personality_id: uuid.UUID,
        entry: str
    ) -> bool:
        """
        Add entry to personality knowledge base.
        
        Args:
            personality_id: Personality UUID
            entry: Knowledge entry text
            
        Returns:
            bool: True if successful
        """
        try:
            async with get_db_session() as session:
                # Get current knowledge base
                result = await session.execute(
                    "SELECT knowledge_base FROM ai_personalities WHERE id = :personality_id",
                    {"personality_id": personality_id}
                )
                row = result.fetchone()
                
                if not row:
                    return False
                
                knowledge_base = row[0] or []
                knowledge_base.append(entry)
                
                # Update
                await session.execute(
                    """
                    UPDATE ai_personalities
                    SET knowledge_base = :knowledge_base, updated_at = :updated_at
                    WHERE id = :personality_id
                    """,
                    {
                        "knowledge_base": json.dumps(knowledge_base),
                        "updated_at": datetime.utcnow(),
                        "personality_id": personality_id
                    }
                )
                await session.commit()
                
                # Clear cache
                await cache_service.delete(f"personality:{personality_id}")
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to add knowledge entry", error=str(e))
            return False
    
    async def test_personality(
        self,
        personality_id: uuid.UUID,
        test_input: str
    ) -> Dict[str, Any]:
        """
        Test personality with sample input.
        
        Args:
            personality_id: Personality UUID
            test_input: Test input text
            
        Returns:
            Dict with test results
        """
        try:
            personality = await self.get_personality(personality_id)
            
            if not personality:
                return {"error": "Personality not found"}
            
            # This would integrate with OpenAI to test the personality
            # For now, return personality details
            return {
                "personality_id": str(personality_id),
                "test_input": test_input,
                "personality_name": personality["name"],
                "voice_settings": personality["voice_settings"],
                "conversation_style": personality["conversation_style"],
                "status": "test_mode"
            }
            
        except Exception as e:
            self.logger.error("Failed to test personality", error=str(e))
            return {"error": str(e)}
    
    async def _clear_personality_cache(self, tenant_id: uuid.UUID):
        """Clear personality cache for tenant."""
        await cache_service.delete(f"default_personality:{tenant_id}")


# Global instance
ai_personality_service = AIPersonalityService()
