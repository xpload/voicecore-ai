"""
Emotion Detection Service for VoiceCore AI.

Implements text-based emotion analysis, sentiment tracking,
and emotion-based routing per Requirement 8.6.
"""

import uuid
import asyncio
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import Call, Agent
from voicecore.logging import get_logger
from voicecore.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class EmotionType(Enum):
    """Types of emotions detected."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"
    FRUSTRATION = "frustration"
    EXCITEMENT = "excitement"
    ANXIETY = "anxiety"


class SentimentPolarity(Enum):
    """Sentiment polarity levels."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class EscalationLevel(Enum):
    """Escalation levels based on emotion."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class EmotionAnalysis:
    """Emotion analysis result."""
    id: str
    text: str
    primary_emotion: EmotionType
    emotion_scores: Dict[EmotionType, float]
    sentiment_polarity: SentimentPolarity
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    escalation_level: EscalationLevel
    keywords_detected: List[str]
    timestamp: datetime
    call_id: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None


@dataclass
class EmotionTrend:
    """Emotion trend over time."""
    emotion: EmotionType
    frequency: int
    average_intensity: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    time_period: str


@dataclass
class SentimentReport:
    """Sentiment analysis report."""
    total_analyses: int
    sentiment_distribution: Dict[SentimentPolarity, int]
    average_sentiment_score: float
    emotion_distribution: Dict[EmotionType, int]
    escalation_triggers: int
    most_common_emotions: List[Tuple[EmotionType, int]]
    time_period: str


class EmotionDetectionService:
    """
    Comprehensive emotion detection and sentiment analysis service.
    
    Implements text-based emotion analysis, sentiment tracking,
    and emotion-based routing per Requirement 8.6.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Emotion analysis storage
        self.emotion_analyses: Dict[str, EmotionAnalysis] = {}
        
        # Emotion keywords and patterns
        self.emotion_keywords = {
            EmotionType.JOY: [
                "happy", "joy", "excited", "great", "wonderful", "amazing", 
                "fantastic", "excellent", "pleased", "delighted", "thrilled"
            ],
            EmotionType.SADNESS: [
                "sad", "disappointed", "upset", "down", "depressed", "unhappy",
                "miserable", "heartbroken", "devastated", "gloomy"
            ],
            EmotionType.ANGER: [
                "angry", "mad", "furious", "rage", "irritated", "annoyed",
                "outraged", "livid", "irate", "pissed", "hate"
            ],
            EmotionType.FEAR: [
                "scared", "afraid", "terrified", "worried", "anxious", "nervous",
                "frightened", "panic", "concerned", "alarmed"
            ],
            EmotionType.SURPRISE: [
                "surprised", "shocked", "amazed", "astonished", "stunned",
                "bewildered", "confused", "unexpected"
            ],
            EmotionType.DISGUST: [
                "disgusted", "revolted", "sick", "nauseated", "repulsed",
                "appalled", "horrified"
            ],
            EmotionType.FRUSTRATION: [
                "frustrated", "annoyed", "irritated", "fed up", "tired of",
                "can't stand", "enough", "ridiculous", "stupid"
            ],
            EmotionType.EXCITEMENT: [
                "excited", "thrilled", "pumped", "enthusiastic", "eager",
                "can't wait", "looking forward"
            ],
            EmotionType.ANXIETY: [
                "anxious", "worried", "stressed", "nervous", "tense",
                "uneasy", "restless", "on edge"
            ]
        }
        
        # Sentiment patterns
        self.positive_patterns = [
            r"\b(love|like|enjoy|appreciate|thank|grateful)\b",
            r"\b(good|great|excellent|amazing|wonderful|fantastic)\b",
            r"\b(happy|pleased|satisfied|delighted)\b"
        ]
        
        self.negative_patterns = [
            r"\b(hate|dislike|terrible|awful|horrible|disgusting)\b",
            r"\b(bad|poor|worst|useless|pathetic)\b",
            r"\b(angry|mad|frustrated|annoyed|upset)\b"
        ]
        
        # Escalation triggers
        self.escalation_keywords = {
            EscalationLevel.HIGH: [
                "lawsuit", "lawyer", "sue", "legal action", "complaint",
                "manager", "supervisor", "cancel", "refund"
            ],
            EscalationLevel.URGENT: [
                "emergency", "urgent", "immediate", "crisis", "critical",
                "life threatening", "danger", "help me"
            ]
        }
        
        # Configuration
        self.config = {
            "min_confidence_threshold": 0.6,
            "escalation_sentiment_threshold": -0.7,
            "high_emotion_intensity_threshold": 0.8,
            "enable_emotion_routing": True,
            "enable_sentiment_tracking": True
        }
    
    async def analyze_text_emotion(
        self,
        text: str,
        call_id: Optional[str] = None,
        tenant_id: Optional[uuid.UUID] = None
    ) -> EmotionAnalysis:
        """
        Analyze emotion and sentiment from text.
        
        Args:
            text: Text to analyze
            call_id: Optional call ID
            tenant_id: Optional tenant ID
            
        Returns:
            EmotionAnalysis object
        """
        try:
            analysis_id = str(uuid.uuid4())
            
            # Clean and normalize text
            normalized_text = self._normalize_text(text)
            
            # Detect emotions
            emotion_scores = self._calculate_emotion_scores(normalized_text)
            primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
            
            # Calculate sentiment
            sentiment_score = self._calculate_sentiment_score(normalized_text)
            sentiment_polarity = self._determine_sentiment_polarity(sentiment_score)
            
            # Determine escalation level
            escalation_level = self._determine_escalation_level(
                normalized_text, primary_emotion, sentiment_score
            )
            
            # Extract keywords
            keywords_detected = self._extract_emotion_keywords(normalized_text)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(emotion_scores, sentiment_score)
            
            analysis = EmotionAnalysis(
                id=analysis_id,
                text=text,
                primary_emotion=primary_emotion,
                emotion_scores=emotion_scores,
                sentiment_polarity=sentiment_polarity,
                sentiment_score=sentiment_score,
                confidence=confidence,
                escalation_level=escalation_level,
                keywords_detected=keywords_detected,
                timestamp=datetime.utcnow(),
                call_id=call_id,
                tenant_id=tenant_id
            )
            
            # Store analysis
            self.emotion_analyses[analysis_id] = analysis
            
            # Store in database if tenant provided
            if tenant_id:
                await self._store_analysis_in_database(analysis)
            
            self.logger.info(
                "Emotion analysis completed",
                analysis_id=analysis_id,
                primary_emotion=primary_emotion.value,
                sentiment_polarity=sentiment_polarity.value,
                escalation_level=escalation_level.value,
                confidence=confidence
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error("Failed to analyze text emotion", error=str(e))
            # Return neutral analysis on error
            return EmotionAnalysis(
                id=str(uuid.uuid4()),
                text=text,
                primary_emotion=EmotionType.NEUTRAL,
                emotion_scores={EmotionType.NEUTRAL: 1.0},
                sentiment_polarity=SentimentPolarity.NEUTRAL,
                sentiment_score=0.0,
                confidence=0.0,
                escalation_level=EscalationLevel.NONE,
                keywords_detected=[],
                timestamp=datetime.utcnow(),
                call_id=call_id,
                tenant_id=tenant_id
            )
    
    async def analyze_conversation_emotion(
        self,
        conversation_segments: List[Dict[str, Any]],
        call_id: str,
        tenant_id: uuid.UUID
    ) -> List[EmotionAnalysis]:
        """
        Analyze emotion throughout a conversation.
        
        Args:
            conversation_segments: List of conversation segments with speaker and text
            call_id: Call ID
            tenant_id: Tenant ID
            
        Returns:
            List of EmotionAnalysis objects
        """
        try:
            analyses = []
            
            for i, segment in enumerate(conversation_segments):
                if segment.get("speaker") == "caller" and segment.get("text"):
                    analysis = await self.analyze_text_emotion(
                        text=segment["text"],
                        call_id=call_id,
                        tenant_id=tenant_id
                    )
                    
                    # Add segment metadata
                    analysis.metadata = {
                        "segment_index": i,
                        "timestamp_in_call": segment.get("timestamp"),
                        "speaker": segment.get("speaker")
                    }
                    
                    analyses.append(analysis)
            
            # Analyze emotion progression
            if len(analyses) > 1:
                emotion_progression = self._analyze_emotion_progression(analyses)
                
                # Update analyses with progression data
                for analysis in analyses:
                    analysis.metadata = analysis.metadata or {}
                    analysis.metadata["emotion_progression"] = emotion_progression
            
            self.logger.info(
                "Conversation emotion analysis completed",
                call_id=call_id,
                segments_analyzed=len(analyses),
                tenant_id=str(tenant_id)
            )
            
            return analyses
            
        except Exception as e:
            self.logger.error("Failed to analyze conversation emotion", error=str(e))
            return []
    
    async def get_emotion_based_routing_recommendation(
        self,
        analysis: EmotionAnalysis,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get routing recommendation based on emotion analysis.
        
        Args:
            analysis: Emotion analysis result
            tenant_id: Tenant ID
            
        Returns:
            Dict containing routing recommendation
        """
        try:
            recommendation = {
                "should_escalate": False,
                "escalation_level": analysis.escalation_level.value,
                "recommended_action": "continue",
                "target_department": None,
                "priority_level": "normal",
                "special_instructions": []
            }
            
            # Check for escalation triggers
            if analysis.escalation_level in [EscalationLevel.HIGH, EscalationLevel.URGENT]:
                recommendation["should_escalate"] = True
                recommendation["recommended_action"] = "escalate"
                recommendation["target_department"] = "management"
                
                if analysis.escalation_level == EscalationLevel.URGENT:
                    recommendation["priority_level"] = "urgent"
                else:
                    recommendation["priority_level"] = "high"
            
            # Emotion-based routing
            if analysis.primary_emotion == EmotionType.ANGER:
                recommendation["special_instructions"].append("Handle with extra patience")
                recommendation["target_department"] = "customer_service"
                if analysis.sentiment_score < -0.5:
                    recommendation["priority_level"] = "high"
            
            elif analysis.primary_emotion == EmotionType.SADNESS:
                recommendation["special_instructions"].append("Show empathy and understanding")
                recommendation["target_department"] = "support"
            
            elif analysis.primary_emotion == EmotionType.FEAR:
                recommendation["special_instructions"].append("Provide reassurance and clear information")
                recommendation["target_department"] = "support"
            
            elif analysis.primary_emotion == EmotionType.FRUSTRATION:
                recommendation["special_instructions"].append("Focus on quick resolution")
                recommendation["target_department"] = "technical_support"
                if analysis.confidence > 0.8:
                    recommendation["priority_level"] = "high"
            
            # Sentiment-based adjustments
            if analysis.sentiment_score < self.config["escalation_sentiment_threshold"]:
                recommendation["should_escalate"] = True
                recommendation["special_instructions"].append("Very negative sentiment detected")
            
            return recommendation
            
        except Exception as e:
            self.logger.error("Failed to get emotion-based routing recommendation", error=str(e))
            return {
                "should_escalate": False,
                "recommended_action": "continue",
                "priority_level": "normal"
            }
    
    async def track_emotion_trends(
        self,
        tenant_id: uuid.UUID,
        days: int = 7
    ) -> List[EmotionTrend]:
        """
        Track emotion trends over time.
        
        Args:
            tenant_id: Tenant ID
            days: Number of days to analyze
            
        Returns:
            List of EmotionTrend objects
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get analyses for the period
            analyses = [
                analysis for analysis in self.emotion_analyses.values()
                if (analysis.tenant_id == tenant_id and 
                    analysis.timestamp > cutoff_date)
            ]
            
            if not analyses:
                return []
            
            trends = []
            
            for emotion in EmotionType:
                emotion_analyses = [
                    a for a in analyses 
                    if a.primary_emotion == emotion
                ]
                
                if emotion_analyses:
                    frequency = len(emotion_analyses)
                    average_intensity = sum(
                        a.emotion_scores.get(emotion, 0.0) 
                        for a in emotion_analyses
                    ) / frequency
                    
                    # Calculate trend direction (simplified)
                    recent_analyses = [
                        a for a in emotion_analyses
                        if (datetime.utcnow() - a.timestamp).days <= days // 2
                    ]
                    older_analyses = [
                        a for a in emotion_analyses
                        if (datetime.utcnow() - a.timestamp).days > days // 2
                    ]
                    
                    if len(recent_analyses) > len(older_analyses):
                        trend_direction = "increasing"
                    elif len(recent_analyses) < len(older_analyses):
                        trend_direction = "decreasing"
                    else:
                        trend_direction = "stable"
                    
                    trend = EmotionTrend(
                        emotion=emotion,
                        frequency=frequency,
                        average_intensity=average_intensity,
                        trend_direction=trend_direction,
                        time_period=f"{days} days"
                    )
                    
                    trends.append(trend)
            
            # Sort by frequency
            trends.sort(key=lambda x: x.frequency, reverse=True)
            
            return trends
            
        except Exception as e:
            self.logger.error("Failed to track emotion trends", error=str(e))
            return []
    
    async def generate_sentiment_report(
        self,
        tenant_id: uuid.UUID,
        days: int = 30
    ) -> SentimentReport:
        """
        Generate comprehensive sentiment analysis report.
        
        Args:
            tenant_id: Tenant ID
            days: Number of days to analyze
            
        Returns:
            SentimentReport object
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get analyses for the period
            analyses = [
                analysis for analysis in self.emotion_analyses.values()
                if (analysis.tenant_id == tenant_id and 
                    analysis.timestamp > cutoff_date)
            ]
            
            if not analyses:
                return SentimentReport(
                    total_analyses=0,
                    sentiment_distribution={},
                    average_sentiment_score=0.0,
                    emotion_distribution={},
                    escalation_triggers=0,
                    most_common_emotions=[],
                    time_period=f"{days} days"
                )
            
            # Calculate sentiment distribution
            sentiment_distribution = {}
            for polarity in SentimentPolarity:
                count = len([a for a in analyses if a.sentiment_polarity == polarity])
                sentiment_distribution[polarity] = count
            
            # Calculate emotion distribution
            emotion_distribution = {}
            for emotion in EmotionType:
                count = len([a for a in analyses if a.primary_emotion == emotion])
                emotion_distribution[emotion] = count
            
            # Calculate average sentiment score
            average_sentiment = sum(a.sentiment_score for a in analyses) / len(analyses)
            
            # Count escalation triggers
            escalation_triggers = len([
                a for a in analyses 
                if a.escalation_level in [EscalationLevel.HIGH, EscalationLevel.URGENT]
            ])
            
            # Get most common emotions
            emotion_counts = [(emotion, count) for emotion, count in emotion_distribution.items() if count > 0]
            emotion_counts.sort(key=lambda x: x[1], reverse=True)
            most_common_emotions = emotion_counts[:5]
            
            return SentimentReport(
                total_analyses=len(analyses),
                sentiment_distribution=sentiment_distribution,
                average_sentiment_score=average_sentiment,
                emotion_distribution=emotion_distribution,
                escalation_triggers=escalation_triggers,
                most_common_emotions=most_common_emotions,
                time_period=f"{days} days"
            )
            
        except Exception as e:
            self.logger.error("Failed to generate sentiment report", error=str(e))
            return SentimentReport(
                total_analyses=0,
                sentiment_distribution={},
                average_sentiment_score=0.0,
                emotion_distribution={},
                escalation_triggers=0,
                most_common_emotions=[],
                time_period=f"{days} days"
            )
    
    async def get_real_time_emotion_alerts(
        self,
        tenant_id: uuid.UUID,
        minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get real-time emotion alerts for recent high-priority emotions.
        
        Args:
            tenant_id: Tenant ID
            minutes: Minutes to look back for alerts
            
        Returns:
            List of emotion alerts
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            # Get recent high-priority analyses
            recent_analyses = [
                analysis for analysis in self.emotion_analyses.values()
                if (analysis.tenant_id == tenant_id and 
                    analysis.timestamp > cutoff_time and
                    (analysis.escalation_level in [EscalationLevel.HIGH, EscalationLevel.URGENT] or
                     analysis.sentiment_score < -0.7 or
                     analysis.primary_emotion in [EmotionType.ANGER, EmotionType.FRUSTRATION]))
            ]
            
            alerts = []
            for analysis in recent_analyses:
                alert = {
                    "analysis_id": analysis.id,
                    "call_id": analysis.call_id,
                    "timestamp": analysis.timestamp.isoformat(),
                    "primary_emotion": analysis.primary_emotion.value,
                    "sentiment_score": analysis.sentiment_score,
                    "escalation_level": analysis.escalation_level.value,
                    "confidence": analysis.confidence,
                    "alert_reason": self._determine_alert_reason(analysis),
                    "recommended_action": "immediate_attention" if analysis.escalation_level == EscalationLevel.URGENT else "monitor_closely"
                }
                alerts.append(alert)
            
            # Sort by urgency and recency
            alerts.sort(key=lambda x: (
                x["escalation_level"] == "urgent",
                x["sentiment_score"] < -0.8,
                x["timestamp"]
            ), reverse=True)
            
            return alerts
            
        except Exception as e:
            self.logger.error("Failed to get real-time emotion alerts", error=str(e))
            return []
    
    # Private helper methods
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for analysis."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove special characters but keep punctuation that affects sentiment
        text = re.sub(r'[^\w\s!?.,;:-]', '', text)
        
        return text
    
    def _calculate_emotion_scores(self, text: str) -> Dict[EmotionType, float]:
        """Calculate emotion scores based on keyword matching."""
        scores = {emotion: 0.0 for emotion in EmotionType}
        
        words = text.split()
        total_words = len(words)
        
        if total_words == 0:
            scores[EmotionType.NEUTRAL] = 1.0
            return scores
        
        for emotion, keywords in self.emotion_keywords.items():
            matches = 0
            for keyword in keywords:
                matches += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
            
            # Calculate score as ratio of matches to total words
            scores[emotion] = min(matches / total_words * 10, 1.0)  # Scale and cap at 1.0
        
        # If no emotions detected, set neutral
        if all(score == 0.0 for score in scores.values()):
            scores[EmotionType.NEUTRAL] = 1.0
        
        return scores
    
    def _calculate_sentiment_score(self, text: str) -> float:
        """Calculate sentiment score from -1.0 (very negative) to 1.0 (very positive)."""
        positive_matches = 0
        negative_matches = 0
        
        for pattern in self.positive_patterns:
            positive_matches += len(re.findall(pattern, text, re.IGNORECASE))
        
        for pattern in self.negative_patterns:
            negative_matches += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Simple sentiment calculation
        total_matches = positive_matches + negative_matches
        if total_matches == 0:
            return 0.0
        
        sentiment = (positive_matches - negative_matches) / total_matches
        return max(-1.0, min(1.0, sentiment))
    
    def _determine_sentiment_polarity(self, sentiment_score: float) -> SentimentPolarity:
        """Determine sentiment polarity from score."""
        if sentiment_score >= 0.6:
            return SentimentPolarity.VERY_POSITIVE
        elif sentiment_score >= 0.2:
            return SentimentPolarity.POSITIVE
        elif sentiment_score >= -0.2:
            return SentimentPolarity.NEUTRAL
        elif sentiment_score >= -0.6:
            return SentimentPolarity.NEGATIVE
        else:
            return SentimentPolarity.VERY_NEGATIVE
    
    def _determine_escalation_level(
        self,
        text: str,
        primary_emotion: EmotionType,
        sentiment_score: float
    ) -> EscalationLevel:
        """Determine escalation level based on text analysis."""
        # Check for urgent keywords
        for keyword in self.escalation_keywords[EscalationLevel.URGENT]:
            if keyword in text:
                return EscalationLevel.URGENT
        
        # Check for high escalation keywords
        for keyword in self.escalation_keywords[EscalationLevel.HIGH]:
            if keyword in text:
                return EscalationLevel.HIGH
        
        # Check emotion and sentiment combination
        if primary_emotion == EmotionType.ANGER and sentiment_score < -0.6:
            return EscalationLevel.HIGH
        
        if primary_emotion in [EmotionType.FRUSTRATION, EmotionType.ANGER] and sentiment_score < -0.4:
            return EscalationLevel.MEDIUM
        
        if sentiment_score < -0.7:
            return EscalationLevel.HIGH
        
        if sentiment_score < -0.4:
            return EscalationLevel.LOW
        
        return EscalationLevel.NONE
    
    def _extract_emotion_keywords(self, text: str) -> List[str]:
        """Extract emotion-related keywords from text."""
        keywords = []
        
        for emotion, emotion_keywords in self.emotion_keywords.items():
            for keyword in emotion_keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                    keywords.append(keyword)
        
        return keywords
    
    def _calculate_confidence(
        self,
        emotion_scores: Dict[EmotionType, float],
        sentiment_score: float
    ) -> float:
        """Calculate overall confidence in the analysis."""
        # Base confidence on the strength of emotion detection
        max_emotion_score = max(emotion_scores.values())
        
        # Factor in sentiment strength
        sentiment_strength = abs(sentiment_score)
        
        # Combine factors
        confidence = (max_emotion_score + sentiment_strength) / 2
        
        return min(1.0, confidence)
    
    def _analyze_emotion_progression(
        self,
        analyses: List[EmotionAnalysis]
    ) -> Dict[str, Any]:
        """Analyze how emotions change throughout a conversation."""
        if len(analyses) < 2:
            return {"progression": "insufficient_data"}
        
        # Track sentiment progression
        sentiment_scores = [a.sentiment_score for a in analyses]
        
        # Calculate trend
        if sentiment_scores[-1] > sentiment_scores[0]:
            sentiment_trend = "improving"
        elif sentiment_scores[-1] < sentiment_scores[0]:
            sentiment_trend = "declining"
        else:
            sentiment_trend = "stable"
        
        # Track emotion changes
        emotions = [a.primary_emotion for a in analyses]
        emotion_changes = len(set(emotions))
        
        return {
            "progression": "analyzed",
            "sentiment_trend": sentiment_trend,
            "initial_sentiment": sentiment_scores[0],
            "final_sentiment": sentiment_scores[-1],
            "sentiment_change": sentiment_scores[-1] - sentiment_scores[0],
            "emotion_changes": emotion_changes,
            "dominant_emotion": max(set(emotions), key=emotions.count).value
        }
    
    def _determine_alert_reason(self, analysis: EmotionAnalysis) -> str:
        """Determine the reason for an emotion alert."""
        reasons = []
        
        if analysis.escalation_level == EscalationLevel.URGENT:
            reasons.append("Urgent escalation keywords detected")
        elif analysis.escalation_level == EscalationLevel.HIGH:
            reasons.append("High escalation level")
        
        if analysis.sentiment_score < -0.7:
            reasons.append("Very negative sentiment")
        
        if analysis.primary_emotion in [EmotionType.ANGER, EmotionType.FRUSTRATION]:
            reasons.append(f"Strong {analysis.primary_emotion.value} detected")
        
        return "; ".join(reasons) if reasons else "Emotion threshold exceeded"
    
    async def _store_analysis_in_database(self, analysis: EmotionAnalysis):
        """Store emotion analysis in database."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(analysis.tenant_id))
                
                # Store in call metadata if call_id provided
                if analysis.call_id:
                    stmt = (
                        select(Call)
                        .where(
                            and_(
                                Call.tenant_id == analysis.tenant_id,
                                Call.id == analysis.call_id
                            )
                        )
                    )
                    
                    result = await session.execute(stmt)
                    call = result.scalar_one_or_none()
                    
                    if call:
                        # Add emotion analysis to call metadata
                        metadata = call.metadata or {}
                        metadata["emotion_analysis"] = {
                            "analysis_id": analysis.id,
                            "primary_emotion": analysis.primary_emotion.value,
                            "sentiment_score": analysis.sentiment_score,
                            "escalation_level": analysis.escalation_level.value,
                            "confidence": analysis.confidence,
                            "timestamp": analysis.timestamp.isoformat()
                        }
                        
                        call.metadata = metadata
                        await session.commit()
                
        except Exception as e:
            self.logger.error("Failed to store emotion analysis in database", error=str(e))


# Singleton instance
emotion_detection_service = EmotionDetectionService()