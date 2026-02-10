"""
Business Intelligence Dashboard API routes for VoiceCore AI 2.0.

Provides comprehensive BI dashboards with real-time metrics, KPI tracking,
executive summary views, and customizable dashboard widgets.

Implements Requirement 3.2: Business intelligence dashboards with real-time metrics
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from voicecore.services.bi_dashboard_service import BIDashboardService
from voicecore.middleware import get_current_tenant_id
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/bi", tags=["Business Intelligence"])


# Pydantic models
class KPIMetric(BaseModel):
    """KPI metric model."""
    name: str
    value: float
    unit: str
    change_percentage: Optional[float] = None
    trend: Optional[str] = None  # "up", "down", "stable"
    target: Optional[float] = None
    status: Optional[str] = None  # "good", "warning", "critical"


class DashboardWidget(BaseModel):
    """Dashboard widget configuration."""
    widget_id: str
    widget_type: str  # "kpi", "chart", "table", "metric"
    title: str
    position: Dict[str, int]  # x, y, width, height
    config: Dict[str, Any]
    data_source: str


class DashboardLayout(BaseModel):
    """Dashboard layout configuration."""
    dashboard_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    widgets: List[DashboardWidget]
    is_default: bool = False


class ExecutiveSummary(BaseModel):
    """Executive summary response model."""
    period: Dict[str, str]
    key_metrics: Dict[str, Any]
    performance_indicators: List[KPIMetric]
    trends: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]


@router.get("/dashboard/executive", response_model=ExecutiveSummary)
async def get_executive_dashboard(
    period: str = Query("today", description="Period: today, week, month, quarter, year"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get executive dashboard with high-level KPIs and insights.
    
    Returns comprehensive executive summary with key performance indicators,
    trends, and actionable insights for business decision-making.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        executive_data = await bi_service.get_executive_dashboard(
            tenant_id=tenant_id,
            period=period
        )
        
        logger.info(
            "Executive dashboard retrieved",
            tenant_id=str(tenant_id),
            period=period
        )
        
        return executive_data
        
    except Exception as e:
        logger.error("Failed to get executive dashboard", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/dashboard/realtime")
async def get_realtime_dashboard(
    refresh_interval: int = Query(30, ge=5, le=300, description="Refresh interval in seconds"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get real-time dashboard with live metrics.
    
    Returns live dashboard data optimized for real-time monitoring
    with automatic refresh capabilities.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        realtime_data = await bi_service.get_realtime_dashboard(
            tenant_id=tenant_id,
            refresh_interval=refresh_interval
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "refresh_interval": refresh_interval,
            "next_refresh": (datetime.utcnow() + timedelta(seconds=refresh_interval)).isoformat(),
            "data": realtime_data
        }
        
    except Exception as e:
        logger.error("Failed to get realtime dashboard", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/kpis")
async def get_kpis(
    period: str = Query("today", description="Period: today, week, month, quarter, year"),
    category: Optional[str] = Query(None, description="KPI category: calls, revenue, satisfaction, efficiency"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get Key Performance Indicators (KPIs) with trends.
    
    Returns comprehensive KPI metrics with historical comparisons,
    trend analysis, and target tracking.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        kpis = await bi_service.get_kpis(
            tenant_id=tenant_id,
            period=period,
            category=category
        )
        
        return {
            "period": period,
            "category": category or "all",
            "kpis": kpis,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get KPIs", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/metrics/business")
async def get_business_metrics(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    granularity: str = Query("day", description="Granularity: hour, day, week, month"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get detailed business metrics with time-series data.
    
    Returns comprehensive business metrics including revenue,
    call volume, conversion rates, and operational efficiency.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        metrics = await bi_service.get_business_metrics(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get business metrics", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/dashboard/layout")
async def save_dashboard_layout(
    layout: DashboardLayout,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Save custom dashboard layout configuration.
    
    Allows users to create and save custom dashboard layouts
    with personalized widget arrangements and configurations.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        saved_layout = await bi_service.save_dashboard_layout(
            tenant_id=tenant_id,
            layout=layout.dict()
        )
        
        logger.info(
            "Dashboard layout saved",
            tenant_id=str(tenant_id),
            dashboard_name=layout.name
        )
        
        return {
            "status": "success",
            "dashboard_id": saved_layout["dashboard_id"],
            "message": "Dashboard layout saved successfully"
        }
        
    except Exception as e:
        logger.error("Failed to save dashboard layout", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/dashboard/layouts")
async def get_dashboard_layouts(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get all saved dashboard layouts for the tenant.
    
    Returns list of all custom dashboard layouts created by the tenant.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        layouts = await bi_service.get_dashboard_layouts(tenant_id=tenant_id)
        
        return {
            "layouts": layouts,
            "count": len(layouts)
        }
        
    except Exception as e:
        logger.error("Failed to get dashboard layouts", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/dashboard/layout/{dashboard_id}")
async def get_dashboard_layout(
    dashboard_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get specific dashboard layout by ID.
    
    Returns the configuration for a specific dashboard layout.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        layout = await bi_service.get_dashboard_layout(
            tenant_id=tenant_id,
            dashboard_id=dashboard_id
        )
        
        if not layout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard layout not found"
            )
        
        return layout
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get dashboard layout", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/dashboard/layout/{dashboard_id}")
async def delete_dashboard_layout(
    dashboard_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Delete a dashboard layout.
    
    Removes a custom dashboard layout configuration.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        success = await bi_service.delete_dashboard_layout(
            tenant_id=tenant_id,
            dashboard_id=dashboard_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard layout not found"
            )
        
        logger.info(
            "Dashboard layout deleted",
            tenant_id=str(tenant_id),
            dashboard_id=dashboard_id
        )
        
        return {"status": "success", "message": "Dashboard layout deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete dashboard layout", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/insights")
async def get_business_insights(
    period: str = Query("week", description="Period: today, week, month, quarter"),
    insight_type: Optional[str] = Query(None, description="Type: performance, trends, anomalies, recommendations"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get AI-powered business insights and recommendations.
    
    Returns intelligent insights based on data analysis including
    performance trends, anomaly detection, and actionable recommendations.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        insights = await bi_service.get_business_insights(
            tenant_id=tenant_id,
            period=period,
            insight_type=insight_type
        )
        
        return {
            "period": period,
            "insight_type": insight_type or "all",
            "insights": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get business insights", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/comparison")
async def get_comparative_analysis(
    metric: str = Query(..., description="Metric to compare: calls, revenue, satisfaction, efficiency"),
    period1: str = Query("this_week", description="First period"),
    period2: str = Query("last_week", description="Second period"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get comparative analysis between two time periods.
    
    Returns side-by-side comparison of metrics between two periods
    with percentage changes and trend analysis.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        comparison = await bi_service.get_comparative_analysis(
            tenant_id=tenant_id,
            metric=metric,
            period1=period1,
            period2=period2
        )
        
        return comparison
        
    except Exception as e:
        logger.error("Failed to get comparative analysis", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/widgets/available")
async def get_available_widgets(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get list of available dashboard widgets.
    
    Returns catalog of all available widget types that can be
    added to custom dashboards.
    
    **Validates: Requirements 3.2**
    """
    try:
        bi_service = BIDashboardService()
        
        widgets = await bi_service.get_available_widgets()
        
        return {
            "widgets": widgets,
            "count": len(widgets)
        }
        
    except Exception as e:
        logger.error("Failed to get available widgets", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/health")
async def bi_dashboard_health_check():
    """Health check endpoint for BI dashboard service."""
    try:
        return {
            "status": "healthy",
            "service": "bi-dashboard",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error("BI dashboard health check failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unavailable")
