"""
Analytics API routes for VoiceCore AI.

Provides REST API endpoints for analytics data collection,
real-time dashboard metrics, and performance reporting.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from voicecore.services.analytics_service import AnalyticsService, AnalyticsServiceError
from voicecore.models import MetricType
from voicecore.middleware import get_current_tenant_id
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics & Reporting"])


# Pydantic models for request/response
class CallMetricsData(BaseModel):
    """Request model for call metrics collection."""
    call_id: uuid.UUID = Field(..., description="Call UUID")
    direction: str = Field(..., description="Call direction (inbound/outbound)")
    status: str = Field(..., description="Call status")
    duration: int = Field(0, description="Call duration in seconds")
    wait_time: Optional[int] = Field(None, description="Wait time in seconds")
    handled_by_ai: bool = Field(False, description="Whether call was handled by AI")
    resolved_by_ai: bool = Field(False, description="Whether call was resolved by AI")
    transferred_by_ai: bool = Field(False, description="Whether call was transferred by AI")
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5, description="Customer satisfaction score")
    is_spam: bool = Field(False, description="Whether call was identified as spam")
    spam_blocked: bool = Field(False, description="Whether spam call was blocked")
    is_vip: bool = Field(False, description="Whether caller is VIP")
    is_priority: bool = Field(False, description="Whether call is priority")
    is_escalated: bool = Field(False, description="Whether call was escalated")
    cost_cents: Optional[int] = Field(None, description="Call cost in cents")
    first_call_resolution: bool = Field(False, description="Whether issue was resolved on first call")
    transferred_in: bool = Field(False, description="Whether call was transferred in")
    transferred_out: bool = Field(False, description="Whether call was transferred out")


class AgentActivityData(BaseModel):
    """Request model for agent activity collection."""
    agent_id: uuid.UUID = Field(..., description="Agent UUID")
    activity_type: str = Field(..., description="Type of activity (login, available, busy, break, call_handled)")
    duration: int = Field(0, description="Duration in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional activity metadata")


class SystemMetricsData(BaseModel):
    """Request model for system metrics collection."""
    metric_type: MetricType = Field(..., description="Type of metric")
    concurrent_calls: Optional[int] = Field(None, description="Current concurrent calls")
    peak_concurrent_calls: Optional[int] = Field(None, description="Peak concurrent calls")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    api_response_time: Optional[float] = Field(None, description="API response time in ms")
    api_error_rate: Optional[float] = Field(None, description="API error rate")
    api_rps: Optional[float] = Field(None, description="API requests per second")
    twilio_latency: Optional[float] = Field(None, description="Twilio API latency in ms")
    openai_latency: Optional[float] = Field(None, description="OpenAI API latency in ms")
    db_query_time: Optional[float] = Field(None, description="Database query time in ms")
    uptime: Optional[float] = Field(None, description="System uptime percentage")
    error_count: Optional[int] = Field(None, description="Number of errors")
    warning_count: Optional[int] = Field(None, description="Number of warnings")
    storage_usage: Optional[float] = Field(None, description="Storage usage in GB")
    bandwidth_usage: Optional[float] = Field(None, description="Bandwidth usage in Mbps")
    active_tenants: Optional[int] = Field(None, description="Number of active tenants")
    active_agents: Optional[int] = Field(None, description="Number of active agents")
    revenue_cents: Optional[int] = Field(None, description="Revenue in cents")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics data")


class DashboardResponse(BaseModel):
    """Response model for dashboard data."""
    timestamp: str
    time_range_hours: int
    call_metrics: Dict[str, Any]
    agent_metrics: Dict[str, Any]
    system_metrics: Dict[str, Any]
    trends: Dict[str, Any]


class AgentPerformanceResponse(BaseModel):
    """Response model for agent performance data."""
    period: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None
    agent: Optional[Dict[str, Any]] = None
    agents: Optional[Dict[str, Dict[str, Any]]] = None
    trends: list = Field(default_factory=list)


# API endpoints
@router.post("/calls/metrics", status_code=status.HTTP_201_CREATED)
async def collect_call_metrics(
    metrics_data: CallMetricsData,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Collect call metrics for analytics.
    
    Records call metrics including duration, status, AI performance,
    and quality metrics for dashboard and reporting purposes.
    """
    try:
        analytics_service = AnalyticsService()
        
        success = await analytics_service.collect_call_metrics(
            tenant_id=tenant_id,
            call_id=metrics_data.call_id,
            call_data=metrics_data.dict(exclude={"call_id"})
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to collect call metrics"
            )
        
        logger.info(
            "Call metrics collected via API",
            tenant_id=str(tenant_id),
            call_id=str(metrics_data.call_id)
        )
        
        return {"status": "success", "message": "Call metrics collected successfully"}
        
    except Exception as e:
        logger.error("Failed to collect call metrics via API", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/agents/activity", status_code=status.HTTP_201_CREATED)
async def collect_agent_activity(
    activity_data: AgentActivityData,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Collect agent activity metrics.
    
    Records agent activity including login time, status changes,
    and call handling for performance monitoring.
    """
    try:
        analytics_service = AnalyticsService()
        
        success = await analytics_service.collect_agent_activity(
            tenant_id=tenant_id,
            agent_id=activity_data.agent_id,
            activity_data=activity_data.dict(exclude={"agent_id"})
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to collect agent activity"
            )
        
        logger.debug(
            "Agent activity collected via API",
            tenant_id=str(tenant_id),
            agent_id=str(activity_data.agent_id),
            activity_type=activity_data.activity_type
        )
        
        return {"status": "success", "message": "Agent activity collected successfully"}
        
    except Exception as e:
        logger.error("Failed to collect agent activity via API", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/system/metrics", status_code=status.HTTP_201_CREATED)
async def collect_system_metrics(
    metrics_data: SystemMetricsData,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Collect system performance metrics.
    
    Records system-wide performance metrics including resource usage,
    API performance, and operational statistics.
    """
    try:
        analytics_service = AnalyticsService()
        
        success = await analytics_service.collect_system_metrics(
            tenant_id=tenant_id,
            metric_type=metrics_data.metric_type,
            metrics_data=metrics_data.dict(exclude={"metric_type"})
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to collect system metrics"
            )
        
        logger.debug(
            "System metrics collected via API",
            tenant_id=str(tenant_id),
            metric_type=metrics_data.metric_type.value
        )
        
        return {"status": "success", "message": "System metrics collected successfully"}
        
    except Exception as e:
        logger.error("Failed to collect system metrics via API", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_data(
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range in hours (max 7 days)"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get real-time dashboard data.
    
    Returns comprehensive dashboard metrics including call volume,
    agent performance, system status, and trend data for the specified time range.
    """
    try:
        analytics_service = AnalyticsService()
        
        dashboard_data = await analytics_service.get_real_time_dashboard_data(
            tenant_id=tenant_id,
            time_range_hours=time_range_hours
        )
        
        if "error" in dashboard_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=dashboard_data["error"]
            )
        
        return DashboardResponse(**dashboard_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get dashboard data", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/agents/performance", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    agent_id: Optional[uuid.UUID] = Query(None, description="Specific agent ID (optional)"),
    start_date: Optional[date] = Query(None, description="Start date for metrics"),
    end_date: Optional[date] = Query(None, description="End date for metrics"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get agent performance statistics.
    
    Returns detailed agent performance metrics including call handling,
    availability, quality scores, and efficiency metrics.
    """
    try:
        analytics_service = AnalyticsService()
        
        performance_data = await analytics_service.get_agent_performance_stats(
            tenant_id=tenant_id,
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if "error" in performance_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=performance_data["error"]
            )
        
        return AgentPerformanceResponse(**performance_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get agent performance data", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/summary")
async def get_analytics_summary(
    period: str = Query("today", description="Period: today, yesterday, this_week, last_week, this_month, last_month"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get analytics summary for a specific period.
    
    Returns high-level analytics summary including key performance indicators
    and comparative metrics for the specified time period.
    """
    try:
        analytics_service = AnalyticsService()
        
        # Calculate date range based on period
        today = date.today()
        
        if period == "today":
            start_date = end_date = today
        elif period == "yesterday":
            start_date = end_date = today - timedelta(days=1)
        elif period == "this_week":
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == "last_week":
            start_date = today - timedelta(days=today.weekday() + 7)
            end_date = today - timedelta(days=today.weekday() + 1)
        elif period == "this_month":
            start_date = today.replace(day=1)
            end_date = today
        elif period == "last_month":
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                start_date = date(today.year, today.month - 1, 1)
                # Last day of previous month
                end_date = date(today.year, today.month, 1) - timedelta(days=1)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period. Use: today, yesterday, this_week, last_week, this_month, last_month"
            )
        
        # Get dashboard data for the period
        hours_diff = int((datetime.combine(end_date, datetime.max.time()) - 
                         datetime.combine(start_date, datetime.min.time())).total_seconds() / 3600)
        
        dashboard_data = await analytics_service.get_real_time_dashboard_data(
            tenant_id=tenant_id,
            time_range_hours=min(hours_diff, 168)  # Max 7 days
        )
        
        # Get agent performance for the period
        agent_performance = await analytics_service.get_agent_performance_stats(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        summary = {
            "period": period,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "call_summary": dashboard_data.get("call_metrics", {}),
            "agent_summary": agent_performance.get("summary", {}),
            "system_summary": dashboard_data.get("system_metrics", {}),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analytics summary", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/health")
async def analytics_health_check():
    """
    Health check endpoint for analytics service.
    
    Returns the current status of the analytics collection system.
    """
    try:
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("Analytics health check failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unavailable")


# Additional reporting endpoints for Task 13.2

@router.get("/reports/calls")
async def get_call_reports(
    start_date: Optional[date] = Query(None, description="Start date for report"),
    end_date: Optional[date] = Query(None, description="End date for report"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    agent_id: Optional[uuid.UUID] = Query(None, description="Filter by agent"),
    call_status: Optional[str] = Query(None, description="Filter by call status"),
    format: str = Query("json", description="Report format: json, csv"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Generate detailed call reports.
    
    Returns comprehensive call reports with filtering options
    and export capabilities for business analysis.
    """
    try:
        analytics_service = AnalyticsService()
        
        # Set default date range if not provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
            
        report_data = await analytics_service.generate_call_report(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            agent_id=agent_id,
            call_status=call_status
        )
        
        if format.lower() == "csv":
            # Return CSV format
            from fastapi.responses import StreamingResponse
            import io
            import csv
            
            output = io.StringIO()
            if report_data.get("calls"):
                writer = csv.DictWriter(output, fieldnames=report_data["calls"][0].keys())
                writer.writeheader()
                writer.writerows(report_data["calls"])
            
            response = StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=call_report_{start_date}_{end_date}.csv"}
            )
            return response
        
        return report_data
        
    except Exception as e:
        logger.error("Failed to generate call report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/reports/agents")
async def get_agent_reports(
    start_date: Optional[date] = Query(None, description="Start date for report"),
    end_date: Optional[date] = Query(None, description="End date for report"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    include_inactive: bool = Query(False, description="Include inactive agents"),
    format: str = Query("json", description="Report format: json, csv"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Generate detailed agent performance reports.
    
    Returns comprehensive agent performance reports with
    productivity metrics and comparative analysis.
    """
    try:
        analytics_service = AnalyticsService()
        
        # Set default date range if not provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
            
        report_data = await analytics_service.generate_agent_report(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            include_inactive=include_inactive
        )
        
        if format.lower() == "csv":
            # Return CSV format
            from fastapi.responses import StreamingResponse
            import io
            import csv
            
            output = io.StringIO()
            if report_data.get("agents"):
                writer = csv.DictWriter(output, fieldnames=report_data["agents"][0].keys())
                writer.writeheader()
                writer.writerows(report_data["agents"])
            
            response = StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=agent_report_{start_date}_{end_date}.csv"}
            )
            return response
        
        return report_data
        
    except Exception as e:
        logger.error("Failed to generate agent report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/reports/conversation-analytics")
async def get_conversation_analytics(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    include_transcripts: bool = Query(False, description="Include call transcripts"),
    sentiment_filter: Optional[str] = Query(None, description="Filter by sentiment: positive, negative, neutral"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Generate conversation analytics and insights.
    
    Returns detailed conversation analytics including AI performance,
    sentiment analysis, and transcript insights per Requirement 9.2.
    """
    try:
        analytics_service = AnalyticsService()
        
        # Set default date range if not provided
        if not start_date:
            start_date = date.today() - timedelta(days=7)
        if not end_date:
            end_date = date.today()
            
        analytics_data = await analytics_service.generate_conversation_analytics(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            include_transcripts=include_transcripts,
            sentiment_filter=sentiment_filter
        )
        
        return analytics_data
        
    except Exception as e:
        logger.error("Failed to generate conversation analytics", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/dashboard/real-time")
async def get_real_time_dashboard(
    refresh_interval: int = Query(30, ge=5, le=300, description="Refresh interval in seconds"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get real-time dashboard data with live updates.
    
    Returns live dashboard metrics optimized for real-time monitoring
    with configurable refresh intervals per Requirement 9.1.
    """
    try:
        analytics_service = AnalyticsService()
        
        dashboard_data = await analytics_service.get_live_dashboard_data(
            tenant_id=tenant_id,
            refresh_interval=refresh_interval
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "refresh_interval": refresh_interval,
            "next_refresh": (datetime.utcnow() + timedelta(seconds=refresh_interval)).isoformat(),
            "data": dashboard_data
        }
        
    except Exception as e:
        logger.error("Failed to get real-time dashboard data", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/trends/call-volume")
async def get_call_volume_trends(
    period: str = Query("7d", description="Period: 1d, 7d, 30d, 90d"),
    granularity: str = Query("hour", description="Granularity: hour, day, week"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get call volume trends and patterns.
    
    Returns historical call volume trends with configurable
    time periods and granularity for trend analysis.
    """
    try:
        analytics_service = AnalyticsService()
        
        # Parse period
        period_days = {
            "1d": 1,
            "7d": 7,
            "30d": 30,
            "90d": 90
        }.get(period, 7)
        
        trends_data = await analytics_service.get_call_volume_trends(
            tenant_id=tenant_id,
            days=period_days,
            granularity=granularity
        )
        
        return trends_data
        
    except Exception as e:
        logger.error("Failed to get call volume trends", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/insights/ai-performance")
async def get_ai_performance_insights(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get AI performance insights and analytics.
    
    Returns detailed AI performance metrics including resolution rates,
    transfer patterns, and conversation quality metrics.
    """
    try:
        analytics_service = AnalyticsService()
        
        # Set default date range if not provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
            
        ai_insights = await analytics_service.get_ai_performance_insights(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return ai_insights
        
    except Exception as e:
        logger.error("Failed to get AI performance insights", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/reports/custom")
async def generate_custom_report(
    report_config: Dict[str, Any],
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Generate custom reports with flexible configuration.
    
    Allows creation of custom reports with user-defined metrics,
    filters, and formatting options for advanced analytics.
    """
    try:
        analytics_service = AnalyticsService()
        
        custom_report = await analytics_service.generate_custom_report(
            tenant_id=tenant_id,
            config=report_config
        )
        
        return custom_report
        
    except Exception as e:
        logger.error("Failed to generate custom report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/export/data")
async def export_analytics_data(
    data_type: str = Query(..., description="Data type: calls, agents, metrics, all"),
    start_date: Optional[date] = Query(None, description="Start date for export"),
    end_date: Optional[date] = Query(None, description="End date for export"),
    format: str = Query("json", description="Export format: json, csv, xlsx"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Export analytics data in various formats.
    
    Provides data export capabilities in multiple formats
    for external analysis and integration per Requirement 10.4.
    """
    try:
        analytics_service = AnalyticsService()
        
        # Set default date range if not provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
            
        export_data = await analytics_service.export_analytics_data(
            tenant_id=tenant_id,
            data_type=data_type,
            start_date=start_date,
            end_date=end_date,
            format=format
        )
        
        if format.lower() in ["csv", "xlsx"]:
            # Return file download
            from fastapi.responses import StreamingResponse
            import io
            
            if format.lower() == "csv":
                media_type = "text/csv"
                extension = "csv"
            else:
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                extension = "xlsx"
            
            response = StreamingResponse(
                io.BytesIO(export_data),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename=analytics_export_{data_type}_{start_date}_{end_date}.{extension}"}
            )
            return response
        
        return export_data
        
    except Exception as e:
        logger.error("Failed to export analytics data", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")