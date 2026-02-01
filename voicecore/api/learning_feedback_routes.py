"""
API routes for learning and feedback system.

Provides endpoints for feedback collection, learning insights,
and improvement recommendations per Requirements 12.3 and 12.5.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from voicecore.services.learning_feedback_service import (
    learning_feedback_service, FeedbackType, LearningPattern, ImprovementType
)
from voicecore.services.auth_service import get_current_tenant
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/learning", tags=["Learning & Feedback"])


# Request/Response Models

class CallFeedbackRequest(BaseModel):
    """Request model for call feedback."""
    call_id: str = Field(..., description="Call ID")
    rating: float = Field(..., ge=1, le=5, description="Rating (1-5 scale)")
    comments: Optional[str] = Field(None, description="Optional feedback comments")
    source: str = Field(default="caller", description="Feedback source")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AgentFeedbackRequest(BaseModel):
    """Request model for agent feedback."""
    agent_id: str = Field(..., description="Agent ID")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    rating: float = Field(..., ge=1, le=5, description="Rating (1-5 scale)")
    comments: Optional[str] = Field(None, description="Optional feedback comments")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ImplementImprovementRequest(BaseModel):
    """Request model for implementing improvement."""
    auto_implement: bool = Field(default=False, description="Whether this is automatic implementation")


# Feedback Collection Endpoints

@router.post("/feedback/calls")
async def submit_call_feedback(
    request: CallFeedbackRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Submit feedback for a specific call.
    
    Collects caller or agent feedback about call quality, resolution,
    and overall satisfaction to improve AI performance.
    """
    try:
        feedback = await learning_feedback_service.collect_call_feedback(
            tenant_id=tenant_id,
            call_id=request.call_id,
            rating=request.rating,
            comments=request.comments,
            source=request.source,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "feedback_id": feedback.id,
            "message": "Call feedback submitted successfully",
            "feedback": {
                "id": feedback.id,
                "call_id": feedback.call_id,
                "rating": feedback.rating,
                "source": feedback.source,
                "timestamp": feedback.timestamp.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Failed to submit call feedback", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit call feedback")


@router.post("/feedback/agents")
async def submit_agent_feedback(
    request: AgentFeedbackRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Submit feedback from agents about system performance.
    
    Collects agent feedback about AI responses, system usability,
    and operational efficiency to identify improvement areas.
    """
    try:
        feedback = await learning_feedback_service.collect_agent_feedback(
            tenant_id=tenant_id,
            agent_id=request.agent_id,
            feedback_type=request.feedback_type,
            rating=request.rating,
            comments=request.comments,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "feedback_id": feedback.id,
            "message": "Agent feedback submitted successfully",
            "feedback": {
                "id": feedback.id,
                "agent_id": request.agent_id,
                "feedback_type": feedback.feedback_type.value,
                "rating": feedback.rating,
                "timestamp": feedback.timestamp.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Failed to submit agent feedback", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit agent feedback")


@router.get("/feedback/summary")
async def get_feedback_summary(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    feedback_type: Optional[FeedbackType] = Query(None, description="Filter by feedback type")
):
    """
    Get feedback summary and analysis.
    
    Returns comprehensive feedback analytics including ratings distribution,
    trends, and common themes from feedback comments.
    """
    try:
        summary = await learning_feedback_service.get_feedback_summary(
            tenant_id=tenant_id,
            days=days,
            feedback_type=feedback_type
        )
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        logger.error("Failed to get feedback summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get feedback summary")


# Learning Analysis Endpoints

@router.post("/analyze/patterns")
async def analyze_successful_patterns(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze")
):
    """
    Analyze successful call patterns to identify learning opportunities.
    
    Examines successful calls to identify patterns that can be used
    to improve AI responses and system performance.
    """
    try:
        insights = await learning_feedback_service.analyze_successful_patterns(
            tenant_id=tenant_id,
            days=days
        )
        
        return {
            "success": True,
            "insights_found": len(insights),
            "analysis_period": f"{days} days",
            "insights": [
                {
                    "id": insight.id,
                    "pattern_type": insight.pattern_type.value,
                    "description": insight.description,
                    "confidence_score": insight.confidence_score,
                    "frequency": insight.frequency,
                    "last_observed": insight.last_observed.isoformat(),
                    "created_at": insight.created_at.isoformat()
                }
                for insight in insights
            ]
        }
        
    except Exception as e:
        logger.error("Failed to analyze successful patterns", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to analyze successful patterns")


@router.get("/insights")
async def list_learning_insights(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    pattern_type: Optional[LearningPattern] = Query(None, description="Filter by pattern type"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score")
):
    """
    List learning insights discovered from successful patterns.
    
    Returns insights about successful call patterns that can be used
    to improve AI performance and system efficiency.
    """
    try:
        insights = [
            insight for insight in learning_feedback_service.learning_insights.values()
            if (insight.tenant_id == tenant_id and
                (not pattern_type or insight.pattern_type == pattern_type) and
                insight.confidence_score >= min_confidence)
        ]
        
        # Sort by confidence and recency
        insights.sort(key=lambda x: (x.confidence_score, x.created_at), reverse=True)
        
        return {
            "success": True,
            "total_insights": len(insights),
            "insights": [
                {
                    "id": insight.id,
                    "pattern_type": insight.pattern_type.value,
                    "description": insight.description,
                    "confidence_score": insight.confidence_score,
                    "frequency": insight.frequency,
                    "supporting_data": insight.supporting_data,
                    "last_observed": insight.last_observed.isoformat(),
                    "created_at": insight.created_at.isoformat()
                }
                for insight in insights
            ]
        }
        
    except Exception as e:
        logger.error("Failed to list learning insights", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list learning insights")


# Improvement Recommendations Endpoints

@router.post("/recommendations/generate")
async def generate_improvement_recommendations(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    insight_ids: Optional[List[str]] = Query(None, description="Specific insight IDs to use")
):
    """
    Generate improvement recommendations based on learning insights.
    
    Creates actionable improvement recommendations based on identified
    patterns and learning insights from successful calls.
    """
    try:
        # Get specific insights if provided
        insights = None
        if insight_ids:
            insights = [
                learning_feedback_service.learning_insights[insight_id]
                for insight_id in insight_ids
                if (insight_id in learning_feedback_service.learning_insights and
                    learning_feedback_service.learning_insights[insight_id].tenant_id == tenant_id)
            ]
        
        recommendations = await learning_feedback_service.generate_improvement_recommendations(
            tenant_id=tenant_id,
            insights=insights
        )
        
        return {
            "success": True,
            "recommendations_generated": len(recommendations),
            "message": "Improvement recommendations generated successfully",
            "recommendations": [
                {
                    "id": rec.id,
                    "improvement_type": rec.improvement_type.value,
                    "title": rec.title,
                    "description": rec.description,
                    "expected_impact": rec.expected_impact,
                    "confidence": rec.confidence,
                    "priority": rec.priority,
                    "implementation_effort": rec.implementation_effort,
                    "supporting_evidence": rec.supporting_evidence,
                    "created_at": rec.created_at.isoformat(),
                    "implemented": rec.implemented
                }
                for rec in recommendations
            ]
        }
        
    except Exception as e:
        logger.error("Failed to generate improvement recommendations", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate improvement recommendations")


@router.get("/recommendations")
async def list_improvement_recommendations(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    improvement_type: Optional[ImprovementType] = Query(None, description="Filter by improvement type"),
    implemented: Optional[bool] = Query(None, description="Filter by implementation status"),
    min_priority: int = Query(1, ge=1, le=5, description="Minimum priority level")
):
    """
    List improvement recommendations for the tenant.
    
    Returns a list of improvement recommendations with filtering options
    for type, implementation status, and priority level.
    """
    try:
        recommendations = [
            rec for rec in learning_feedback_service.improvement_recommendations.values()
            if (rec.tenant_id == tenant_id and
                (improvement_type is None or rec.improvement_type == improvement_type) and
                (implemented is None or rec.implemented == implemented) and
                rec.priority >= min_priority)
        ]
        
        # Sort by priority and confidence
        recommendations.sort(key=lambda x: (x.priority, x.confidence), reverse=True)
        
        return {
            "success": True,
            "total_recommendations": len(recommendations),
            "recommendations": [
                {
                    "id": rec.id,
                    "improvement_type": rec.improvement_type.value,
                    "title": rec.title,
                    "description": rec.description,
                    "expected_impact": rec.expected_impact,
                    "confidence": rec.confidence,
                    "priority": rec.priority,
                    "implementation_effort": rec.implementation_effort,
                    "supporting_evidence": rec.supporting_evidence,
                    "created_at": rec.created_at.isoformat(),
                    "implemented": rec.implemented
                }
                for rec in recommendations
            ]
        }
        
    except Exception as e:
        logger.error("Failed to list improvement recommendations", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list improvement recommendations")


@router.post("/recommendations/{recommendation_id}/implement")
async def implement_improvement_recommendation(
    recommendation_id: str,
    request: ImplementImprovementRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Implement an improvement recommendation.
    
    Executes the specified improvement recommendation, applying
    the suggested changes to improve system performance.
    """
    try:
        success = await learning_feedback_service.implement_improvement(
            recommendation_id=recommendation_id,
            tenant_id=tenant_id,
            auto_implement=request.auto_implement
        )
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Recommendation not found, access denied, or implementation failed"
            )
        
        return {
            "success": True,
            "message": "Improvement recommendation implemented successfully",
            "recommendation_id": recommendation_id,
            "auto_implement": request.auto_implement
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to implement improvement recommendation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to implement improvement recommendation")


@router.get("/recommendations/{recommendation_id}")
async def get_improvement_recommendation(
    recommendation_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get details of a specific improvement recommendation.
    
    Returns detailed information about an improvement recommendation
    including implementation status and supporting evidence.
    """
    try:
        if recommendation_id not in learning_feedback_service.improvement_recommendations:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        recommendation = learning_feedback_service.improvement_recommendations[recommendation_id]
        
        # Verify tenant ownership
        if recommendation.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "success": True,
            "recommendation": {
                "id": recommendation.id,
                "improvement_type": recommendation.improvement_type.value,
                "title": recommendation.title,
                "description": recommendation.description,
                "expected_impact": recommendation.expected_impact,
                "confidence": recommendation.confidence,
                "priority": recommendation.priority,
                "implementation_effort": recommendation.implementation_effort,
                "supporting_evidence": recommendation.supporting_evidence,
                "created_at": recommendation.created_at.isoformat(),
                "implemented": recommendation.implemented
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get improvement recommendation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get improvement recommendation")


# Learning Metrics and Analytics Endpoints

@router.get("/metrics")
async def get_learning_metrics(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Get learning system metrics and performance indicators.
    
    Returns comprehensive metrics about the learning system performance,
    including feedback statistics, improvements implemented, and impact measurements.
    """
    try:
        metrics = await learning_feedback_service.get_learning_metrics(
            tenant_id=tenant_id,
            days=days
        )
        
        return {
            "success": True,
            "period": {
                "days": days,
                "end_date": datetime.utcnow().isoformat()
            },
            "metrics": {
                "total_feedback_entries": metrics.total_feedback_entries,
                "average_satisfaction": round(metrics.average_satisfaction, 2),
                "learning_insights_count": metrics.learning_insights_count,
                "improvements_implemented": metrics.improvements_implemented,
                "success_rate_improvement": round(metrics.success_rate_improvement, 1),
                "response_time_improvement": round(metrics.response_time_improvement, 1),
                "knowledge_base_growth": metrics.knowledge_base_growth
            }
        }
        
    except Exception as e:
        logger.error("Failed to get learning metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get learning metrics")


@router.get("/dashboard")
async def get_learning_dashboard(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(7, ge=1, le=30, description="Number of days for dashboard data")
):
    """
    Get learning system dashboard data.
    
    Returns a comprehensive dashboard view of the learning system
    including recent feedback, insights, recommendations, and metrics.
    """
    try:
        # Get recent feedback summary
        feedback_summary = await learning_feedback_service.get_feedback_summary(
            tenant_id=tenant_id,
            days=days
        )
        
        # Get recent insights
        recent_insights = [
            insight for insight in learning_feedback_service.learning_insights.values()
            if (insight.tenant_id == tenant_id and
                (datetime.utcnow() - insight.created_at).days <= days)
        ]
        
        # Get pending recommendations
        pending_recommendations = [
            rec for rec in learning_feedback_service.improvement_recommendations.values()
            if (rec.tenant_id == tenant_id and not rec.implemented)
        ]
        
        # Get learning metrics
        metrics = await learning_feedback_service.get_learning_metrics(
            tenant_id=tenant_id,
            days=days
        )
        
        return {
            "success": True,
            "dashboard": {
                "period": {
                    "days": days,
                    "end_date": datetime.utcnow().isoformat()
                },
                "feedback_summary": feedback_summary,
                "recent_insights": {
                    "count": len(recent_insights),
                    "insights": [
                        {
                            "pattern_type": insight.pattern_type.value,
                            "confidence_score": insight.confidence_score,
                            "frequency": insight.frequency
                        }
                        for insight in sorted(recent_insights, key=lambda x: x.confidence_score, reverse=True)[:5]
                    ]
                },
                "pending_recommendations": {
                    "count": len(pending_recommendations),
                    "high_priority": len([r for r in pending_recommendations if r.priority >= 4]),
                    "recommendations": [
                        {
                            "title": rec.title,
                            "priority": rec.priority,
                            "confidence": rec.confidence,
                            "implementation_effort": rec.implementation_effort
                        }
                        for rec in sorted(pending_recommendations, key=lambda x: x.priority, reverse=True)[:5]
                    ]
                },
                "metrics": {
                    "average_satisfaction": round(metrics.average_satisfaction, 2),
                    "improvements_implemented": metrics.improvements_implemented,
                    "success_rate_improvement": round(metrics.success_rate_improvement, 1),
                    "knowledge_base_growth": metrics.knowledge_base_growth
                }
            }
        }
        
    except Exception as e:
        logger.error("Failed to get learning dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get learning dashboard")


# System Control Endpoints

@router.post("/system/start")
async def start_learning_system(
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Start the learning and feedback processing system.
    
    Initiates the background processing for learning insights
    and automatic improvement implementation.
    """
    try:
        await learning_feedback_service.start_learning_system()
        
        return {
            "success": True,
            "message": "Learning and feedback system started successfully"
        }
        
    except Exception as e:
        logger.error("Failed to start learning system", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start learning system")


@router.post("/system/stop")
async def stop_learning_system(
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Stop the learning and feedback processing system.
    
    Stops the background processing for learning insights
    and automatic improvement implementation.
    """
    try:
        await learning_feedback_service.stop_learning_system()
        
        return {
            "success": True,
            "message": "Learning and feedback system stopped successfully"
        }
        
    except Exception as e:
        logger.error("Failed to stop learning system", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to stop learning system")


# Utility Endpoints

@router.get("/feedback-types")
async def list_feedback_types():
    """
    List available feedback types.
    
    Returns all available feedback types that can be used
    when submitting feedback to the system.
    """
    try:
        feedback_types = [
            {
                "value": feedback_type.value,
                "name": feedback_type.value.replace("_", " ").title(),
                "description": f"{feedback_type.value.replace('_', ' ').title()} feedback"
            }
            for feedback_type in FeedbackType
        ]
        
        return {
            "success": True,
            "feedback_types": feedback_types
        }
        
    except Exception as e:
        logger.error("Failed to list feedback types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list feedback types")


@router.get("/pattern-types")
async def list_learning_pattern_types():
    """
    List available learning pattern types.
    
    Returns all learning pattern types that the system
    can identify and learn from.
    """
    try:
        pattern_types = [
            {
                "value": pattern.value,
                "name": pattern.value.replace("_", " ").title(),
                "description": f"{pattern.value.replace('_', ' ').title()} pattern"
            }
            for pattern in LearningPattern
        ]
        
        return {
            "success": True,
            "pattern_types": pattern_types
        }
        
    except Exception as e:
        logger.error("Failed to list learning pattern types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list learning pattern types")