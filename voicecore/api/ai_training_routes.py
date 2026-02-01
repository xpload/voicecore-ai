"""
API routes for AI training and optimization.

Provides endpoints for training mode, custom response scripts,
and A/B testing per Requirements 12.1, 12.2, and 12.4.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from voicecore.services.ai_training_service import (
    ai_training_service, ResponseStrategy, TrainingMode, TestStatus
)
from voicecore.services.auth_service import get_current_tenant
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/ai-training", tags=["AI Training"])


# Request/Response Models

class CreateScriptRequest(BaseModel):
    """Request model for creating custom response script."""
    name: str = Field(..., description="Script name")
    description: str = Field(..., description="Script description")
    trigger_keywords: List[str] = Field(..., description="Keywords that trigger this script")
    response_template: str = Field(..., description="Response template with variables")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variable definitions")
    strategy: ResponseStrategy = Field(default=ResponseStrategy.DEFAULT, description="Response strategy")
    priority: int = Field(default=1, description="Script priority")


class UpdateScriptRequest(BaseModel):
    """Request model for updating response script."""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None
    response_template: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    strategy: Optional[ResponseStrategy] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class StartTrainingRequest(BaseModel):
    """Request model for starting training session."""
    mode: TrainingMode = Field(default=TrainingMode.TRAINING, description="Training mode")
    script_id: Optional[str] = Field(None, description="Optional script ID for testing")
    test_id: Optional[str] = Field(None, description="Optional A/B test ID")


class TrainingInteractionRequest(BaseModel):
    """Request model for training interaction."""
    user_input: str = Field(..., description="User's input")
    ai_response: str = Field(..., description="AI's response")
    success: bool = Field(..., description="Whether interaction was successful")
    feedback_score: Optional[float] = Field(None, ge=1, le=5, description="Feedback score (1-5)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CreateABTestRequest(BaseModel):
    """Request model for creating A/B test."""
    name: str = Field(..., description="Test name")
    description: str = Field(..., description="Test description")
    strategy_a: ResponseStrategy = Field(..., description="First strategy to test")
    strategy_b: ResponseStrategy = Field(..., description="Second strategy to test")
    traffic_split: float = Field(default=0.5, ge=0.0, le=1.0, description="Traffic split for strategy A")
    success_metric: str = Field(default="transfer_rate", description="Success metric to optimize")
    target_sample_size: int = Field(default=100, ge=10, description="Target sample size")
    duration_days: int = Field(default=7, ge=1, le=30, description="Test duration in days")


class GenerateResponseRequest(BaseModel):
    """Request model for generating response."""
    strategy: ResponseStrategy = Field(..., description="Response strategy")
    response_type: str = Field(..., description="Type of response")
    variables: Dict[str, Any] = Field(..., description="Variables for template")


# Custom Response Scripts Endpoints

@router.post("/scripts")
async def create_response_script(
    request: CreateScriptRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Create a custom response script for AI training.
    
    Creates a new custom response script that can be used to train
    the AI with specific responses for certain keywords or contexts.
    """
    try:
        script = await ai_training_service.create_custom_response_script(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            trigger_keywords=request.trigger_keywords,
            response_template=request.response_template,
            variables=request.variables,
            strategy=request.strategy,
            priority=request.priority
        )
        
        return {
            "success": True,
            "script_id": script.id,
            "message": "Custom response script created successfully",
            "script": {
                "id": script.id,
                "name": script.name,
                "description": script.description,
                "strategy": script.strategy.value,
                "enabled": script.enabled,
                "created_at": script.created_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Failed to create response script", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create response script")


@router.get("/scripts")
async def list_response_scripts(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    enabled_only: bool = Query(False, description="Return only enabled scripts")
):
    """
    List all custom response scripts for the tenant.
    
    Returns a list of all custom response scripts created by the tenant,
    optionally filtered to show only enabled scripts.
    """
    try:
        scripts = [
            script for script in ai_training_service.custom_scripts.values()
            if script.tenant_id == tenant_id and (not enabled_only or script.enabled)
        ]
        
        return {
            "success": True,
            "total_scripts": len(scripts),
            "scripts": [
                {
                    "id": script.id,
                    "name": script.name,
                    "description": script.description,
                    "trigger_keywords": script.trigger_keywords,
                    "strategy": script.strategy.value,
                    "priority": script.priority,
                    "enabled": script.enabled,
                    "created_at": script.created_at.isoformat(),
                    "updated_at": script.updated_at.isoformat()
                }
                for script in sorted(scripts, key=lambda x: x.priority, reverse=True)
            ]
        }
        
    except Exception as e:
        logger.error("Failed to list response scripts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list response scripts")


@router.get("/scripts/{script_id}")
async def get_response_script(
    script_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get details of a specific response script.
    
    Returns detailed information about a custom response script,
    including the template and variables.
    """
    try:
        if script_id not in ai_training_service.custom_scripts:
            raise HTTPException(status_code=404, detail="Script not found")
        
        script = ai_training_service.custom_scripts[script_id]
        
        # Verify tenant ownership
        if script.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "success": True,
            "script": {
                "id": script.id,
                "name": script.name,
                "description": script.description,
                "trigger_keywords": script.trigger_keywords,
                "response_template": script.response_template,
                "variables": script.variables,
                "strategy": script.strategy.value,
                "priority": script.priority,
                "enabled": script.enabled,
                "created_at": script.created_at.isoformat(),
                "updated_at": script.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get response script", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get response script")


@router.put("/scripts/{script_id}")
async def update_response_script(
    script_id: str,
    request: UpdateScriptRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Update an existing response script.
    
    Updates the specified fields of a custom response script.
    Only the script owner (tenant) can update their scripts.
    """
    try:
        # Filter out None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        script = await ai_training_service.update_response_script(
            script_id=script_id,
            tenant_id=tenant_id,
            **updates
        )
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found or access denied")
        
        return {
            "success": True,
            "message": "Response script updated successfully",
            "script": {
                "id": script.id,
                "name": script.name,
                "description": script.description,
                "strategy": script.strategy.value,
                "enabled": script.enabled,
                "updated_at": script.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update response script", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update response script")


@router.delete("/scripts/{script_id}")
async def delete_response_script(
    script_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Delete a response script.
    
    Permanently deletes a custom response script.
    Only the script owner (tenant) can delete their scripts.
    """
    try:
        if script_id not in ai_training_service.custom_scripts:
            raise HTTPException(status_code=404, detail="Script not found")
        
        script = ai_training_service.custom_scripts[script_id]
        
        # Verify tenant ownership
        if script.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete from memory (in production, also delete from database)
        del ai_training_service.custom_scripts[script_id]
        
        return {
            "success": True,
            "message": "Response script deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete response script", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete response script")


# Training Session Endpoints

@router.post("/sessions")
async def start_training_session(
    request: StartTrainingRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Start a new AI training session.
    
    Initiates a training session where AI responses can be tested
    and improved through feedback and interaction analysis.
    """
    try:
        session = await ai_training_service.start_training_mode(
            tenant_id=tenant_id,
            mode=request.mode,
            script_id=request.script_id,
            test_id=request.test_id
        )
        
        return {
            "success": True,
            "session_id": session.id,
            "message": "Training session started successfully",
            "session": {
                "id": session.id,
                "mode": session.mode.value,
                "script_id": session.script_id,
                "test_id": session.test_id,
                "start_time": session.start_time.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Failed to start training session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start training session")


@router.post("/sessions/{session_id}/interactions")
async def process_training_interaction(
    session_id: str,
    request: TrainingInteractionRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Process a training interaction and collect feedback.
    
    Records an interaction during a training session and analyzes
    it for potential improvements to the AI responses.
    """
    try:
        analysis = await ai_training_service.process_training_interaction(
            session_id=session_id,
            user_input=request.user_input,
            ai_response=request.ai_response,
            success=request.success,
            feedback_score=request.feedback_score,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "message": "Training interaction processed successfully",
            "analysis": analysis
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to process training interaction", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process training interaction")


@router.get("/sessions")
async def list_training_sessions(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    limit: int = Query(10, ge=1, le=100, description="Number of sessions to return")
):
    """
    List recent training sessions for the tenant.
    
    Returns a list of recent training sessions with their statistics
    and current status.
    """
    try:
        sessions = [
            session for session in ai_training_service.active_training_sessions.values()
            if session.tenant_id == tenant_id
        ]
        
        # Sort by start time (most recent first)
        sessions.sort(key=lambda x: x.start_time, reverse=True)
        sessions = sessions[:limit]
        
        return {
            "success": True,
            "total_sessions": len(sessions),
            "sessions": [
                {
                    "id": session.id,
                    "mode": session.mode.value,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat() if session.end_time else None,
                    "total_interactions": session.total_interactions,
                    "successful_interactions": session.successful_interactions,
                    "success_rate": (session.successful_interactions / session.total_interactions) if session.total_interactions > 0 else 0,
                    "average_feedback": sum(session.feedback_scores) / len(session.feedback_scores) if session.feedback_scores else None,
                    "improvements_count": len(session.improvements_identified)
                }
                for session in sessions
            ]
        }
        
    except Exception as e:
        logger.error("Failed to list training sessions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list training sessions")


# A/B Testing Endpoints

@router.post("/ab-tests")
async def create_ab_test(
    request: CreateABTestRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Create a new A/B test for response strategies.
    
    Sets up an A/B test to compare two different response strategies
    and determine which performs better based on specified metrics.
    """
    try:
        test_config = await ai_training_service.create_ab_test(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            strategy_a=request.strategy_a,
            strategy_b=request.strategy_b,
            traffic_split=request.traffic_split,
            success_metric=request.success_metric,
            target_sample_size=request.target_sample_size,
            duration_days=request.duration_days
        )
        
        return {
            "success": True,
            "test_id": test_config.id,
            "message": "A/B test created successfully",
            "test": {
                "id": test_config.id,
                "name": test_config.name,
                "description": test_config.description,
                "strategy_a": test_config.strategy_a.value,
                "strategy_b": test_config.strategy_b.value,
                "traffic_split": test_config.traffic_split,
                "status": test_config.status.value,
                "target_sample_size": test_config.target_sample_size,
                "end_date": test_config.end_date.isoformat() if test_config.end_date else None,
                "created_at": test_config.created_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Failed to create A/B test", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create A/B test")


@router.post("/ab-tests/{test_id}/start")
async def start_ab_test(
    test_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Start an A/B test.
    
    Activates an A/B test so that it begins collecting data
    and routing traffic according to the configured split.
    """
    try:
        success = await ai_training_service.start_ab_test(test_id, tenant_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Test not found or access denied")
        
        return {
            "success": True,
            "message": "A/B test started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start A/B test", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start A/B test")


@router.get("/ab-tests")
async def list_ab_tests(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    status: Optional[TestStatus] = Query(None, description="Filter by test status")
):
    """
    List A/B tests for the tenant.
    
    Returns a list of A/B tests, optionally filtered by status.
    """
    try:
        tests = [
            test for test in ai_training_service.ab_tests.values()
            if test.tenant_id == tenant_id and (not status or test.status == status)
        ]
        
        return {
            "success": True,
            "total_tests": len(tests),
            "tests": [
                {
                    "id": test.id,
                    "name": test.name,
                    "description": test.description,
                    "strategy_a": test.strategy_a.value,
                    "strategy_b": test.strategy_b.value,
                    "traffic_split": test.traffic_split,
                    "status": test.status.value,
                    "success_metric": test.success_metric,
                    "target_sample_size": test.target_sample_size,
                    "start_date": test.start_date.isoformat(),
                    "end_date": test.end_date.isoformat() if test.end_date else None,
                    "created_at": test.created_at.isoformat()
                }
                for test in sorted(tests, key=lambda x: x.created_at, reverse=True)
            ]
        }
        
    except Exception as e:
        logger.error("Failed to list A/B tests", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list A/B tests")


@router.get("/ab-tests/{test_id}/results")
async def get_ab_test_results(
    test_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Get A/B test results and analysis.
    
    Returns detailed results for both strategies in the A/B test,
    including statistical analysis and performance metrics.
    """
    try:
        results = await ai_training_service.get_ab_test_results(test_id, tenant_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="Test not found or access denied")
        
        return {
            "success": True,
            "test_id": test_id,
            "results": {
                "strategy_a": {
                    "strategy": results["strategy_a"].strategy.value,
                    "sample_size": results["strategy_a"].sample_size,
                    "success_rate": results["strategy_a"].success_rate,
                    "average_response_time": results["strategy_a"].average_response_time,
                    "transfer_rate": results["strategy_a"].transfer_rate,
                    "satisfaction_score": results["strategy_a"].satisfaction_score,
                    "confidence_interval": results["strategy_a"].confidence_interval,
                    "statistical_significance": results["strategy_a"].statistical_significance
                },
                "strategy_b": {
                    "strategy": results["strategy_b"].strategy.value,
                    "sample_size": results["strategy_b"].sample_size,
                    "success_rate": results["strategy_b"].success_rate,
                    "average_response_time": results["strategy_b"].average_response_time,
                    "transfer_rate": results["strategy_b"].transfer_rate,
                    "satisfaction_score": results["strategy_b"].satisfaction_score,
                    "confidence_interval": results["strategy_b"].confidence_interval,
                    "statistical_significance": results["strategy_b"].statistical_significance
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get A/B test results", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get A/B test results")


# Response Generation Endpoints

@router.post("/generate-response")
async def generate_response(
    request: GenerateResponseRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """
    Generate a response using a specific strategy.
    
    Generates a response using the specified strategy and variables,
    useful for testing different response styles.
    """
    try:
        response = await ai_training_service.generate_response_with_strategy(
            strategy=request.strategy,
            response_type=request.response_type,
            variables=request.variables,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "response": response,
            "strategy": request.strategy.value,
            "response_type": request.response_type
        }
        
    except Exception as e:
        logger.error("Failed to generate response", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate response")


@router.get("/strategies")
async def list_response_strategies():
    """
    List available response strategies.
    
    Returns all available response strategies that can be used
    for custom scripts and A/B testing.
    """
    try:
        strategies = [
            {
                "value": strategy.value,
                "name": strategy.value.replace("_", " ").title(),
                "description": f"{strategy.value.replace('_', ' ').title()} response style"
            }
            for strategy in ResponseStrategy
        ]
        
        return {
            "success": True,
            "strategies": strategies
        }
        
    except Exception as e:
        logger.error("Failed to list response strategies", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list response strategies")


# Analytics Endpoints

@router.get("/analytics")
async def get_training_analytics(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Get training analytics and insights.
    
    Returns comprehensive analytics about training sessions,
    A/B tests, and AI performance improvements.
    """
    try:
        analytics = await ai_training_service.get_training_analytics(tenant_id, days)
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error("Failed to get training analytics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get training analytics")