"""
Knowledge base and spam detection models for VoiceCore AI.

Defines knowledge base entries for AI training and spam detection
rules for call filtering with tenant-specific configurations.
"""

import enum
from typing import Optional
from sqlalchemy import Column, String, Integer, Boolean, Enum, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel, TimestampMixin, TenantMixin


class KnowledgeCategory(enum.Enum):
    """Knowledge base category enumeration."""
    GENERAL = "general"
    COMPANY_INFO = "company_info"
    SERVICES = "services"
    POLICIES = "policies"
    PROCEDURES = "procedures"
    FAQ = "faq"
    TROUBLESHOOTING = "troubleshooting"
    EMERGENCY = "emergency"


class KnowledgeBase(BaseModel, TimestampMixin, TenantMixin):
    """
    Knowledge base entries for AI training and responses.
    
    Stores question-answer pairs and contextual information
    that the AI uses to provide intelligent responses to callers.
    """
    
    # Question and answer content
    question = Column(
        Text,
        nullable=False,
        doc="Question or trigger phrase"
    )
    
    answer = Column(
        Text,
        nullable=False,
        doc="AI response or answer"
    )
    
    # Categorization and organization
    category = Column(
        Enum(KnowledgeCategory),
        default=KnowledgeCategory.GENERAL,
        nullable=False,
        doc="Knowledge category"
    )
    
    subcategory = Column(
        String(100),
        nullable=True,
        doc="Subcategory for more specific classification"
    )
    
    tags = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Tags for searchability and organization"
    )
    
    # Priority and relevance
    priority = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Priority level (higher = more important)"
    )
    
    confidence_threshold = Column(
        Float,
        default=0.7,
        nullable=False,
        doc="Minimum confidence required to use this answer"
    )
    
    # Status and lifecycle
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this knowledge entry is active"
    )
    
    is_approved = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this entry has been approved by admin"
    )
    
    # Language and localization
    language = Column(
        String(10),
        default="en",
        nullable=False,
        doc="Language of the question and answer"
    )
    
    # Context and conditions
    context_conditions = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Conditions when this knowledge should be used"
    )
    
    department_specific = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this knowledge is department-specific"
    )
    
    departments = Column(
        JSON,
        default=list,
        nullable=False,
        doc="List of departments this knowledge applies to"
    )
    
    # Usage tracking and analytics
    usage_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times this knowledge was used"
    )
    
    success_rate = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Success rate when this knowledge was used (0-1)"
    )
    
    last_used_at = Column(
        TimestampMixin.created_at.type,
        nullable=True,
        doc="When this knowledge was last used"
    )
    
    # Alternative phrasings and synonyms
    alternative_questions = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Alternative ways to ask the same question"
    )
    
    keywords = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Keywords that should trigger this knowledge"
    )
    
    # Follow-up and related information
    follow_up_questions = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Suggested follow-up questions"
    )
    
    related_entries = Column(
        JSON,
        default=list,
        nullable=False,
        doc="IDs of related knowledge entries"
    )
    
    # Metadata
    source = Column(
        String(255),
        nullable=True,
        doc="Source of this knowledge (manual, imported, learned)"
    )
    
    created_by = Column(
        String(255),
        nullable=True,
        doc="Who created this knowledge entry"
    )
    
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional metadata"
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, category={self.category.value}, active={self.is_active})>"
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the knowledge entry."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def add_keyword(self, keyword: str) -> None:
        """Add a keyword to the knowledge entry."""
        if self.keywords is None:
            self.keywords = []
        if keyword.lower() not in [k.lower() for k in self.keywords]:
            self.keywords.append(keyword.lower())
    
    def increment_usage(self, success: bool = True) -> None:
        """Increment usage count and update success rate."""
        self.usage_count += 1
        if success:
            # Update success rate using exponential moving average
            alpha = 0.1  # Learning rate
            self.success_rate = (1 - alpha) * self.success_rate + alpha * 1.0
        else:
            self.success_rate = (1 - alpha) * self.success_rate + alpha * 0.0


class SpamRule(BaseModel, TimestampMixin, TenantMixin):
    """
    Spam detection rules for filtering unwanted calls.
    
    Configurable rules that identify and handle spam calls
    based on various criteria and patterns.
    """
    
    # Rule identification
    name = Column(
        String(255),
        nullable=False,
        doc="Human-readable name for the rule"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Description of what this rule detects"
    )
    
    # Rule type and pattern
    rule_type = Column(
        String(50),
        nullable=False,
        doc="Type of rule (keyword, pattern, number, behavior)"
    )
    
    pattern = Column(
        Text,
        nullable=False,
        doc="Pattern or keyword to match"
    )
    
    is_regex = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the pattern is a regular expression"
    )
    
    case_sensitive = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether matching should be case sensitive"
    )
    
    # Scoring and weighting
    weight = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Weight of this rule in spam scoring (1-100)"
    )
    
    threshold = Column(
        Float,
        default=0.8,
        nullable=False,
        doc="Confidence threshold for triggering this rule"
    )
    
    # Actions and responses
    action = Column(
        String(20),
        default="flag",
        nullable=False,
        doc="Action to take when rule matches (block, flag, challenge, log)"
    )
    
    response_message = Column(
        Text,
        nullable=True,
        doc="Message to play to caller when rule triggers"
    )
    
    # Conditions and context
    apply_to_numbers = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Phone number patterns this rule applies to"
    )
    
    exclude_numbers = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Phone number patterns to exclude from this rule"
    )
    
    time_conditions = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Time-based conditions for when rule applies"
    )
    
    # Status and lifecycle
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this rule is active"
    )
    
    is_global = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is a global rule (shared across tenants)"
    )
    
    # Performance tracking
    match_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times this rule has matched"
    )
    
    false_positive_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of reported false positives"
    )
    
    last_matched_at = Column(
        TimestampMixin.created_at.type,
        nullable=True,
        doc="When this rule last matched"
    )
    
    # Learning and adaptation
    auto_learn = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this rule should auto-adapt based on feedback"
    )
    
    confidence_score = Column(
        Float,
        default=1.0,
        nullable=False,
        doc="Confidence in this rule's accuracy (0-1)"
    )
    
    # Metadata
    source = Column(
        String(100),
        nullable=True,
        doc="Source of this rule (manual, imported, learned)"
    )
    
    created_by = Column(
        String(255),
        nullable=True,
        doc="Who created this rule"
    )
    
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional rule metadata"
    )
    
    def __repr__(self) -> str:
        return f"<SpamRule(id={self.id}, name='{self.name}', type='{self.rule_type}')>"
    
    def increment_match(self, is_false_positive: bool = False) -> None:
        """Increment match count and update confidence."""
        self.match_count += 1
        
        if is_false_positive:
            self.false_positive_count += 1
            # Decrease confidence for false positives
            self.confidence_score = max(0.1, self.confidence_score - 0.05)
        else:
            # Increase confidence for successful matches
            self.confidence_score = min(1.0, self.confidence_score + 0.01)
    
    @property
    def accuracy_rate(self) -> float:
        """Calculate accuracy rate based on matches and false positives."""
        if self.match_count == 0:
            return 1.0
        return 1.0 - (self.false_positive_count / self.match_count)
    
    @property
    def is_effective(self) -> bool:
        """Check if rule is effective based on accuracy and usage."""
        return self.accuracy_rate >= 0.8 and self.confidence_score >= 0.5


class SpamReport(BaseModel, TimestampMixin, TenantMixin):
    """
    Spam detection reports and feedback for rule improvement.
    
    Tracks spam detection events and user feedback to improve
    the accuracy of spam detection rules over time.
    """
    
    # Call reference
    call_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Reference to the call (if available)"
    )
    
    phone_number = Column(
        String(20),
        nullable=False,
        doc="Phone number that was reported/detected"
    )
    
    # Detection details
    spam_score = Column(
        Float,
        nullable=False,
        doc="Calculated spam score (0-1)"
    )
    
    triggered_rules = Column(
        JSON,
        default=list,
        nullable=False,
        doc="List of rule IDs that triggered"
    )
    
    detection_method = Column(
        String(50),
        nullable=False,
        doc="How spam was detected (automatic, manual, reported)"
    )
    
    # Action taken
    action_taken = Column(
        String(50),
        nullable=False,
        doc="Action that was taken (blocked, flagged, allowed)"
    )
    
    # User feedback
    is_confirmed_spam = Column(
        Boolean,
        nullable=True,
        doc="User confirmation of spam status (null = no feedback)"
    )
    
    feedback_notes = Column(
        Text,
        nullable=True,
        doc="Additional feedback notes"
    )
    
    reported_by = Column(
        String(255),
        nullable=True,
        doc="Who reported this as spam"
    )
    
    # Context information
    call_content = Column(
        Text,
        nullable=True,
        doc="Content/transcript that triggered spam detection"
    )
    
    caller_behavior = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Observed caller behavior patterns"
    )
    
    # Metadata
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional detection metadata"
    )
    
    def __repr__(self) -> str:
        return f"<SpamReport(id={self.id}, phone='{self.phone_number}', score={self.spam_score})>"