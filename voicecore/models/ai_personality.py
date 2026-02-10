"""
AI Personality models for VoiceCore AI 2.0.

Defines custom AI personalities, training data, and conversation templates
for tenant-specific AI customization.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, 
    ForeignKey, JSON, Index, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from voicecore.models.base import BaseModel


class AIPersonality(BaseModel):
    __tablename__ = "a_i_personality"
    """
    AI personality configuration for custom AI behavior per tenant.
    
    Allows tenants to customize AI voice, personality, knowledge base,
    and conversation style for their specific business needs.
    """
    __tablename__ = "ai_personalities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Basic configuration
    name = Column(String(255), nullable=False, doc="Name of the AI personality")
    description = Column(Text, nullable=True, doc="Description of this personality")
    is_active = Column(Boolean, default=True, nullable=False, doc="Whether this personality is active")
    is_default = Column(Boolean, default=False, nullable=False, doc="Whether this is the default personality for the tenant")
    
    # Voice settings
    voice_settings = Column(JSON, nullable=False, default=dict, doc="Voice configuration (voice_id, gender, speed, pitch)")
    language = Column(String(10), nullable=False, default="en", doc="Primary language code")
    supported_languages = Column(JSON, nullable=False, default=list, doc="List of supported language codes")
    
    # Personality configuration
    conversation_style = Column(Text, nullable=False, doc="Conversation style and personality instructions")
    greeting_message = Column(Text, nullable=True, doc="Custom greeting message")
    fallback_message = Column(Text, nullable=True, doc="Message when AI doesn't understand")
    transfer_message = Column(Text, nullable=True, doc="Message before transferring to human")
    
    # Knowledge base
    knowledge_base = Column(JSON, default=dict, nullable=False, doc="Structured knowledge base for AI responses")
    company_info = Column(JSON, default=dict, nullable=False, doc="Company information for context")
    faq_data = Column(JSON, default=list, nullable=False, doc="Frequently asked questions and answers")
    
    # Training configuration
    training_data = Column(JSON, default=dict, nullable=False, doc="Custom training data and examples")
    fine_tuning_model_id = Column(String(100), nullable=True, doc="OpenAI fine-tuned model ID")
    training_status = Column(String(50), default="not_trained", nullable=False, doc="Training status")
    last_trained_at = Column(DateTime, nullable=True, doc="Last training timestamp")
    
    # Behavior settings
    max_conversation_turns = Column(Integer, default=10, nullable=False, doc="Maximum conversation turns before transfer")
    confidence_threshold = Column(Float, default=0.7, nullable=False, doc="Minimum confidence for AI responses")
    enable_sentiment_analysis = Column(Boolean, default=True, nullable=False, doc="Enable sentiment analysis")
    enable_emotion_detection = Column(Boolean, default=True, nullable=False, doc="Enable emotion detection")
    
    # Performance metrics
    total_conversations = Column(Integer, default=0, nullable=False, doc="Total conversations handled")
    successful_resolutions = Column(Integer, default=0, nullable=False, doc="Conversations resolved without transfer")
    average_satisfaction_score = Column(Float, nullable=True, doc="Average customer satisfaction score")
    
    # Metadata
    personality_metadata = Column("metadata", JSON, default=dict, nullable=False, doc="Additional metadata")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="ai_personalities")
    conversation_templates = relationship("ConversationTemplate", back_populates="ai_personality", cascade="all, delete-orphan")
    training_sessions = relationship("AITrainingSession", back_populates="ai_personality", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_ai_personality_tenant", "tenant_id"),
        Index("idx_ai_personality_active", "is_active"),
        Index("idx_ai_personality_default", "tenant_id", "is_default"),
    )
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of AI resolutions."""
        if self.total_conversations == 0:
            return 0.0
        return (self.successful_resolutions / self.total_conversations) * 100
    
    def __repr__(self):
        return f"<AIPersonality(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"


class ConversationTemplate(BaseModel):
    """
    Conversation templates for structured AI interactions.
    
    Defines conversation flows, intents, and responses for
    specific scenarios and use cases.
    """
    __tablename__ = "conversation_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_personality_id = Column(UUID(as_uuid=True), ForeignKey("ai_personalities.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Template configuration
    name = Column(String(255), nullable=False, doc="Template name")
    description = Column(Text, nullable=True, doc="Template description")
    intent = Column(String(100), nullable=False, doc="Intent this template handles")
    category = Column(String(50), nullable=False, doc="Template category")
    
    # Template content
    trigger_phrases = Column(JSON, default=list, nullable=False, doc="Phrases that trigger this template")
    response_template = Column(Text, nullable=False, doc="Response template with variables")
    follow_up_questions = Column(JSON, default=list, nullable=False, doc="Follow-up questions to ask")
    required_information = Column(JSON, default=list, nullable=False, doc="Required information to collect")
    
    # Behavior
    priority = Column(Integer, default=0, nullable=False, doc="Template priority (higher = more important)")
    is_active = Column(Boolean, default=True, nullable=False, doc="Whether template is active")
    requires_confirmation = Column(Boolean, default=False, nullable=False, doc="Whether to confirm before executing")
    
    # Actions
    actions = Column(JSON, default=list, nullable=False, doc="Actions to perform when template is used")
    escalation_rules = Column(JSON, default=dict, nullable=False, doc="Rules for escalating to human")
    
    # Usage statistics
    usage_count = Column(Integer, default=0, nullable=False, doc="Number of times used")
    success_count = Column(Integer, default=0, nullable=False, doc="Number of successful uses")
    last_used_at = Column(DateTime, nullable=True, doc="Last usage timestamp")
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ai_personality = relationship("AIPersonality", back_populates="conversation_templates")
    
    # Indexes
    __table_args__ = (
        Index("idx_conversation_template_personality", "ai_personality_id"),
        Index("idx_conversation_template_intent", "intent"),
        Index("idx_conversation_template_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<ConversationTemplate(id={self.id}, name='{self.name}', intent='{self.intent}')>"


class AITrainingSession(BaseModel):
    """
    AI training session tracking for continuous learning.
    
    Records training sessions, feedback, and performance improvements
    for AI personalities.
    """
    __tablename__ = "ai_training_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_personality_id = Column(UUID(as_uuid=True), ForeignKey("ai_personalities.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Training configuration
    training_type = Column(String(50), nullable=False, doc="Type of training (fine_tuning, feedback, manual)")
    status = Column(String(50), nullable=False, default="pending", doc="Training status")
    
    # Training data
    training_data_size = Column(Integer, default=0, nullable=False, doc="Number of training examples")
    training_data_source = Column(String(100), nullable=True, doc="Source of training data")
    training_parameters = Column(JSON, default=dict, nullable=False, doc="Training parameters")
    
    # Results
    model_id = Column(String(100), nullable=True, doc="Trained model ID")
    performance_metrics = Column(JSON, default=dict, nullable=False, doc="Performance metrics")
    improvement_percentage = Column(Float, nullable=True, doc="Performance improvement percentage")
    
    # Timestamps
    started_at = Column(DateTime, nullable=True, doc="Training start time")
    completed_at = Column(DateTime, nullable=True, doc="Training completion time")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ai_personality = relationship("AIPersonality", back_populates="training_sessions")
    
    # Indexes
    __table_args__ = (
        Index("idx_ai_training_personality", "ai_personality_id"),
        Index("idx_ai_training_status", "status"),
        Index("idx_ai_training_type", "training_type"),
    )
    
    def __repr__(self):
        return f"<AITrainingSession(id={self.id}, type='{self.training_type}', status='{self.status}')>"


class AIFeedback(BaseModel):
    """
    AI feedback for continuous improvement.
    
    Collects feedback on AI responses for training and optimization.
    """
    __tablename__ = "ai_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_personality_id = Column(UUID(as_uuid=True), ForeignKey("ai_personalities.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Feedback context
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=True)
    conversation_id = Column(String(100), nullable=True, doc="Conversation identifier")
    message_id = Column(String(100), nullable=True, doc="Specific message identifier")
    
    # Feedback content
    feedback_type = Column(String(50), nullable=False, doc="Type of feedback (positive, negative, correction)")
    rating = Column(Integer, nullable=True, doc="Rating (1-5)")
    comment = Column(Text, nullable=True, doc="Feedback comment")
    
    # Context
    user_message = Column(Text, nullable=True, doc="User's message")
    ai_response = Column(Text, nullable=True, doc="AI's response")
    expected_response = Column(Text, nullable=True, doc="Expected/corrected response")
    
    # Metadata
    provided_by = Column(String(100), nullable=True, doc="Who provided the feedback")
    is_processed = Column(Boolean, default=False, nullable=False, doc="Whether feedback has been processed")
    processed_at = Column(DateTime, nullable=True, doc="When feedback was processed")
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_ai_feedback_personality", "ai_personality_id"),
        Index("idx_ai_feedback_type", "feedback_type"),
        Index("idx_ai_feedback_processed", "is_processed"),
    )
    
    def __repr__(self):
        return f"<AIFeedback(id={self.id}, type='{self.feedback_type}', rating={self.rating})>"
