"""
API routes for emotion detection and sentiment analysis.

Provides endpoints for text-based emotion analysis, sentiment tracking,
and emotion-based routing per Requirement 8.6.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from voicecore.services.emotion_detection_service import (
    emotion_detection_service, EmotionType, SentimentPolarity, EscalationLevel
)
from voicecore.services.auth_service import get_current_tenant
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/emotion", tags=["Emotion Detection"])


# Request/Response Models

class AnalyzeTextRequest(BaseModel):
    """Request model for text emotion analysis."""
    text: str = Field(..., description="Text to analyze for emotions")
    call_id: Optional[str] = Field(None, description="Optional call ID")


class AnalyzeConversationRequest(BaseModel):
    """Request model for conversation emotion analysis."""
    conversation_segments: List[Dict[str, Any]] = Field(
        ..., 
        description="List of conversation segments with speaker and text"
    )
    call_id: str = Field(..., description="Call ID")


class EmotionRoutingRequest(BaseModel):
    """Request model for emotion-based routing recommendation."""
    analysis_id: str = Field(..., description="Emotion analysis ID")


# Emotion Analysis Endpoints

@router.post("/analyze/text")
async def analyze_text_emotion(
    request: AnalyzeTextRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Analyze emotion and sentiment from text.
    
    Performs comprehensive emotion detection and sentiment analysis
    on the provided text, returning detailed emotional insights.
    """
    try:
        analysis = await emotion_detection_service.analyze_text_emotion(
            text=request.text,
            call_id=request.call_id,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "analysis_id": analysis.id,
            "analysis": {
                "id": analysis.id,
                "text": analysis.text,
                "primary_emotion": analysis.primary_emotion.value,
                "emotion_scores": {
                    emotion.value: score 
                    for emotion, score in analysis.emotion_scores.items()
                },
                "sentiment_polarity": analysis.sentiment_polarity.value,
                "sentiment_score": analysis.sentiment_score,
                "confidence": analysis.confidence,
                "escalation_level": analysis.escalation_level.value,
                "keywords_detected": analysis.keywords_detected,
                "timestamp": analysis.timestamp.isoformat(),
                "call_id": analysis.call_id
            }
        }
        
    except Exception as e:
        logger.error("Failed to analyze text emotion", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to analyze text emotion")


@router.post("/analyze/conversation")
async def analyze_conversation_emotion(
    request: AnalyzeConversationRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Analyze emotion throughout a conversation.
    
    Analyzes emotion and sentiment changes throughout a conversation,
    providing insights into emotional progression and patterns.
    """
    try:
        analyses = await emotion_detection_service.analyze_conversation_emotion(
            conversation_segments=request.conversation_segments,
            call_id=request.call_id,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "call_id": request.call_id,
            "segments_analyzed": len(analyses),
            "analyses": [
                {
                    "id": analysis.id,
                    "primary_emotion": analysis.primary_emotion.value,
                    "sentiment_score": analysis.sentiment_score,
                    "sentiment_polarity": analysis.sentiment_polarity.value,
                    "escalation_level": analysis.escalation_level.value,
                    "confidence": analysis.confidence,
                    "keywords_detected": analysis.keywords_detected,
                    "timestamp": analysis.timestamp.isoformat(),
                    "metadata": getattr(analysis, 'metadata', {})
                }
                for analysis in analyses
            ]
        }
        
    except Exception as e:
        logger.error("Failed to analyze conversation emotion", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to analyze conversation emotion")


@router.get("/analysis/{analysis_id}")
async def get_emotion_analysis(
    analysis_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get details of a specific emotion analysis.
    
    Returns detailed information about a previously performed
    emotion analysis including all detected emotions and sentiment data.
    """
    try:
        if analysis_id not in emotion_detection_service.emotion_analyses:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis = emotion_detection_service.emotion_analyses[analysis_id]
        
        # Verify tenant ownership
        if analysis.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "success": True,
            "analysis": {
                "id": analysis.id,
                "text": analysis.text,
                "primary_emotion": analysis.primary_emotion.value,
                "emotion_scores": {
                    emotion.value: score 
                    for emotion, score in analysis.emotion_scores.items()
                },
                "sentiment_polarity": analysis.sentiment_polarity.value,
                "sentiment_score": analysis.sentiment_score,
                "confidence": analysis.confidence,
                "escalation_level": analysis.escalation_level.value,
                "keywords_detected": analysis.keywords_detected,
                "timestamp": analysis.timestamp.isoformat(),
                "call_id": analysis.call_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get emotion analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get emotion analysis")


# Emotion-Based Routing Endpoints

@router.post("/routing/recommendation")
async def get_emotion_routing_recommendation(
    request: EmotionRoutingRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get routing recommendation based on emotion analysis.
    
    Provides intelligent routing recommendations based on detected
    emotions and sentiment to ensure appropriate call handling.
    """
    try:
        if request.analysis_id not in emotion_detection_service.emotion_analyses:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis = emotion_detection_service.emotion_analyses[request.analysis_id]
        
        # Verify tenant ownership
        if analysis.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        recommendation = await emotion_detection_service.get_emotion_based_routing_recommendation(
            analysis=analysis,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "analysis_id": request.analysis_id,
            "recommendation": recommendation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get emotion routing recommendation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get emotion routing recommendation")


@router.get("/routing/alerts")
async def get_real_time_emotion_alerts(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    minutes: int = Query(5, ge=1, le=60, description="Minutes to look back for alerts")
):
    """
    Get real-time emotion alerts for high-priority emotions.
    
    Returns alerts for recent calls with high emotional intensity
    or escalation triggers that require immediate attention.
    """
    try:
        alerts = await emotion_detection_service.get_real_time_emotion_alerts(
            tenant_id=tenant_id,
            minutes=minutes
        )
        
        return {
            "success": True,
            "alert_period_minutes": minutes,
            "total_alerts": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error("Failed to get real-time emotion alerts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get real-time emotion alerts")


# Sentiment Tracking and Analytics Endpoints

@router.get("/trends")
async def get_emotion_trends(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze")
):
    """
    Get emotion trends over time.
    
    Analyzes emotion patterns and trends over the specified time period
    to identify changes in customer sentiment and emotional patterns.
    """
    try:
        trends = await emotion_detection_service.track_emotion_trends(
            tenant_id=tenant_id,
            days=days
        )
        
        return {
            "success": True,
            "analysis_period": f"{days} days",
            "total_trends": len(trends),
            "trends": [
                {
                    "emotion": trend.emotion.value,
                    "frequency": trend.frequency,
                    "average_intensity": trend.average_intensity,
                    "trend_direction": trend.trend_direction,
                    "time_period": trend.time_period
                }
                for trend in trends
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get emotion trends", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get emotion trends")


@router.get("/sentiment/report")
async def get_sentiment_report(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Generate comprehensive sentiment analysis report.
    
    Provides detailed sentiment analytics including distribution,
    trends, and escalation patterns over the specified time period.
    """
    try:
        report = await emotion_detection_service.generate_sentiment_report(
            tenant_id=tenant_id,
            days=days
        )
        
        return {
            "success": True,
            "report": {
                "time_period": report.time_period,
                "total_analyses": report.total_analyses,
                "average_sentiment_score": round(report.average_sentiment_score, 3),
                "escalation_triggers": report.escalation_triggers,
                "sentiment_distribution": {
                    polarity.value: count 
                    for polarity, count in report.sentiment_distribution.items()
                },
                "emotion_distribution": {
                    emotion.value: count 
                    for emotion, count in report.emotion_distribution.items()
                },
                "most_common_emotions": [
                    {
                        "emotion": emotion.value,
                        "count": count
                    }
                    for emotion, count in report.most_common_emotions
                ]
            }
        }
        
    except Exception as e:
        logger.error("Failed to get sentiment report", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get sentiment report")


@router.get("/analytics/dashboard")
async def get_emotion_analytics_dashboard(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(7, ge=1, le=30, description="Number of days for dashboard data")
):
    """
    Get emotion analytics dashboard data.
    
    Returns comprehensive dashboard data including recent trends,
    alerts, sentiment distribution, and key metrics.
    """
    try:
        # Get recent trends
        trends = await emotion_detection_service.track_emotion_trends(
            tenant_id=tenant_id,
            days=days
        )
        
        # Get sentiment report
        report = await emotion_detection_service.generate_sentiment_report(
            tenant_id=tenant_id,
            days=days
        )
        
        # Get recent alerts
        alerts = await emotion_detection_service.get_real_time_emotion_alerts(
            tenant_id=tenant_id,
            minutes=60  # Last hour
        )
        
        # Calculate key metrics
        total_analyses = report.total_analyses
        escalation_rate = (report.escalation_triggers / total_analyses * 100) if total_analyses > 0 else 0
        
        # Get top emotions
        top_emotions = [
            {"emotion": emotion.value, "count": count}
            for emotion, count in report.most_common_emotions[:3]
        ]
        
        return {
            "success": True,
            "dashboard": {
                "period": {
                    "days": days,
                    "end_date": datetime.utcnow().isoformat()
                },
                "key_metrics": {
                    "total_analyses": total_analyses,
                    "average_sentiment": round(report.average_sentiment_score, 2),
                    "escalation_rate": round(escalation_rate, 1),
                    "recent_alerts": len(alerts)
                },
                "sentiment_distribution": {
                    polarity.value: count 
                    for polarity, count in report.sentiment_distribution.items()
                },
                "top_emotions": top_emotions,
                "emotion_trends": [
                    {
                        "emotion": trend.emotion.value,
                        "frequency": trend.frequency,
                        "trend_direction": trend.trend_direction
                    }
                    for trend in trends[:5]
                ],
                "recent_alerts": alerts[:10]  # Last 10 alerts
            }
        }
        
    except Exception as e:
        logger.error("Failed to get emotion analytics dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get emotion analytics dashboard")


# Configuration and Utility Endpoints

@router.get("/emotions")
async def list_emotion_types():
    """
    List available emotion types.
    
    Returns all emotion types that can be detected by the system
    along with their descriptions.
    """
    try:
        emotions = [
            {
                "value": emotion.value,
                "name": emotion.value.replace("_", " ").title(),
                "description": f"{emotion.value.replace('_', ' ').title()} emotion"
            }
            for emotion in EmotionType
        ]
        
        return {
            "success": True,
            "emotions": emotions
        }
        
    except Exception as e:
        logger.error("Failed to list emotion types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list emotion types")


@router.get("/sentiment/polarities")
async def list_sentiment_polarities():
    """
    List available sentiment polarities.
    
    Returns all sentiment polarity levels that can be detected
    by the sentiment analysis system.
    """
    try:
        polarities = [
            {
                "value": polarity.value,
                "name": polarity.value.replace("_", " ").title(),
                "description": f"{polarity.value.replace('_', ' ').title()} sentiment"
            }
            for polarity in SentimentPolarity
        ]
        
        return {
            "success": True,
            "polarities": polarities
        }
        
    except Exception as e:
        logger.error("Failed to list sentiment polarities", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sentiment polarities")


@router.get("/escalation/levels")
async def list_escalation_levels():
    """
    List available escalation levels.
    
    Returns all escalation levels that can be triggered
    based on emotion and sentiment analysis.
    """
    try:
        levels = [
            {
                "value": level.value,
                "name": level.value.replace("_", " ").title(),
                "description": f"{level.value.replace('_', ' ').title()} escalation level"
            }
            for level in EscalationLevel
        ]
        
        return {
            "success": True,
            "escalation_levels": levels
        }
        
    except Exception as e:
        logger.error("Failed to list escalation levels", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list escalation levels")


@router.get("/config")
async def get_emotion_detection_config(
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get emotion detection configuration.
    
    Returns current configuration settings for emotion detection
    and sentiment analysis thresholds.
    """
    try:
        config = emotion_detection_service.config.copy()
        
        return {
            "success": True,
            "config": config
        }
        
    except Exception as e:
        logger.error("Failed to get emotion detection config", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get emotion detection config")


@router.put("/config")
async def update_emotion_detection_config(
    config_updates: Dict[str, Any],
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Update emotion detection configuration.
    
    Updates configuration settings for emotion detection thresholds
    and behavior customization.
    """
    try:
        # Validate config updates
        valid_keys = {
            "min_confidence_threshold",
            "escalation_sentiment_threshold", 
            "high_emotion_intensity_threshold",
            "enable_emotion_routing",
            "enable_sentiment_tracking"
        }
        
        invalid_keys = set(config_updates.keys()) - valid_keys
        if invalid_keys:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid configuration keys: {list(invalid_keys)}"
            )
        
        # Update configuration
        for key, value in config_updates.items():
            if key in emotion_detection_service.config:
                emotion_detection_service.config[key] = value
        
        return {
            "success": True,
            "message": "Emotion detection configuration updated successfully",
            "updated_config": emotion_detection_service.config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update emotion detection config", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update emotion detection config")