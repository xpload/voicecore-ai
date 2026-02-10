"""
Business Intelligence Dashboard Service for VoiceCore AI 2.0.

Provides comprehensive BI capabilities including real-time metrics,
KPI tracking, executive dashboards, and customizable widgets.

Implements Requirement 3.2: Business intelligence dashboards with real-time metrics
"""

import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    CallAnalytics, AgentMetrics, SystemMetrics, Tenant,
    Call, Agent, CallStatus
)
from voicecore.services.analytics_service import AnalyticsService
from voicecore.services.cache_service import CacheService
from voicecore.logging import get_logger


logger = get_logger(__name__)


class BIDashboardService:
    """
    Business Intelligence Dashboard Service.
    
    Provides comprehensive BI dashboards with real-time metrics,
    KPI tracking, executive summaries, and customizable widgets.
    """
    
    def __init__(self):
        self.logger = logger
        self.analytics_service = AnalyticsService()
        self.cache_service = CacheService()
        self._dashboard_layouts = {}  # In-memory storage for demo
    
    async def get_executive_dashboard(
        self,
        tenant_id: uuid.UUID,
        period: str = "today"
    ) -> Dict[str, Any]:
        """
        Get executive dashboard with high-level KPIs and insights.
        
        Args:
            tenant_id: Tenant UUID
            period: Time period (today, week, month, quarter, year)
            
        Returns:
            Dict containing executive dashboard data
        """
        try:
            # Calculate date range
            start_date, end_date = self._get_period_dates(period)
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get key metrics
                key_metrics = await self._get_key_metrics(
                    session, tenant_id, start_date, end_date
                )
                
                # Get performance indicators
                kpis = await self._calculate_kpis(
                    session, tenant_id, start_date, end_date, period
                )
                
                # Get trends
                trends = await self._get_trends(
                    session, tenant_id, start_date, end_date
                )
                
                # Generate insights
                insights = await self._generate_insights(
                    key_metrics, kpis, trends
                )
                
                # Generate recommendations
                recommendations = await self._generate_recommendations(
                    key_metrics, kpis, trends
                )
                
                return {
                    "period": {
                        "name": period,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "key_metrics": key_metrics,
                    "performance_indicators": kpis,
                    "trends": trends,
                    "insights": insights,
                    "recommendations": recommendations
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get executive dashboard",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_realtime_dashboard(
        self,
        tenant_id: uuid.UUID,
        refresh_interval: int = 30
    ) -> Dict[str, Any]:
        """Get real-time dashboard with live metrics."""
        try:
            # Check cache first
            cache_key = f"realtime_dashboard:{tenant_id}"
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                current_time = datetime.utcnow()
                
                # Get active calls count
                result = await session.execute(
                    select(func.count(Call.id)).where(
                        and_(
                            Call.tenant_id == tenant_id,
                            Call.status == CallStatus.IN_PROGRESS
                        )
                    )
                )
                active_calls = result.scalar() or 0
                
                # Get today's metrics
                today = date.today()
                result = await session.execute(
                    select(CallAnalytics).where(
                        and_(
                            CallAnalytics.tenant_id == tenant_id,
                            CallAnalytics.date == today
                        )
                    )
                )
                today_analytics = result.scalars().all()
                
                # Aggregate today's data
                total_calls_today = sum(a.total_calls for a in today_analytics)
                answered_calls_today = sum(a.answered_calls for a in today_analytics)
                ai_handled_today = sum(a.ai_handled_calls for a in today_analytics)
                
                # Get active agents
                result = await session.execute(
                    select(func.count(Agent.id)).where(
                        and_(
                            Agent.tenant_id == tenant_id,
                            Agent.is_active == True
                        )
                    )
                )
                active_agents = result.scalar() or 0
                
                realtime_data = {
                    "current_metrics": {
                        "active_calls": active_calls,
                        "active_agents": active_agents,
                        "calls_today": total_calls_today,
                        "answered_today": answered_calls_today,
                        "ai_handled_today": ai_handled_today,
                        "answer_rate_today": answered_calls_today / max(1, total_calls_today)
                    },
                    "timestamp": current_time.isoformat()
                }
                
                # Cache for refresh interval
                await self.cache_service.set(
                    cache_key,
                    json.dumps(realtime_data),
                    ttl=refresh_interval
                )
                
                return realtime_data
                
        except Exception as e:
            self.logger.error(
                "Failed to get realtime dashboard",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_kpis(
        self,
        tenant_id: uuid.UUID,
        period: str = "today",
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get Key Performance Indicators with trends."""
        try:
            start_date, end_date = self._get_period_dates(period)
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                kpis = await self._calculate_kpis(
                    session, tenant_id, start_date, end_date, period
                )
                
                # Filter by category if specified
                if category:
                    kpis = [kpi for kpi in kpis if kpi.get("category") == category]
                
                return kpis
                
        except Exception as e:
            self.logger.error(
                "Failed to get KPIs",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise

    async def get_business_metrics(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        granularity: str = "day"
    ) -> Dict[str, Any]:
        """Get detailed business metrics with time-series data."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get call analytics for the period
                result = await session.execute(
                    select(CallAnalytics).where(
                        and_(
                            CallAnalytics.tenant_id == tenant_id,
                            CallAnalytics.date >= start_date,
                            CallAnalytics.date <= end_date
                        )
                    ).order_by(CallAnalytics.date)
                )
                analytics = result.scalars().all()
                
                # Aggregate by granularity
                time_series = self._aggregate_by_granularity(
                    analytics, granularity
                )
                
                # Calculate summary metrics
                total_calls = sum(a.total_calls for a in analytics)
                total_revenue = sum(a.total_cost_cents for a in analytics) / 100
                avg_satisfaction = sum(
                    a.average_satisfaction_score * a.satisfaction_responses 
                    for a in analytics if a.average_satisfaction_score
                ) / max(1, sum(a.satisfaction_responses for a in analytics))
                
                return {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "granularity": granularity
                    },
                    "summary": {
                        "total_calls": total_calls,
                        "total_revenue": total_revenue,
                        "average_satisfaction": avg_satisfaction
                    },
                    "time_series": time_series
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get business metrics",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def save_dashboard_layout(
        self,
        tenant_id: uuid.UUID,
        layout: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save custom dashboard layout configuration."""
        try:
            dashboard_id = layout.get("dashboard_id") or str(uuid.uuid4())
            
            layout_data = {
                "dashboard_id": dashboard_id,
                "tenant_id": str(tenant_id),
                "name": layout["name"],
                "description": layout.get("description"),
                "widgets": layout["widgets"],
                "is_default": layout.get("is_default", False),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Store in cache and in-memory (for demo)
            cache_key = f"dashboard_layout:{tenant_id}:{dashboard_id}"
            await self.cache_service.set(
                cache_key,
                json.dumps(layout_data),
                ttl=86400 * 30  # 30 days
            )
            
            self._dashboard_layouts[dashboard_id] = layout_data
            
            self.logger.info(
                "Dashboard layout saved",
                tenant_id=str(tenant_id),
                dashboard_id=dashboard_id
            )
            
            return layout_data
            
        except Exception as e:
            self.logger.error(
                "Failed to save dashboard layout",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_dashboard_layouts(
        self,
        tenant_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get all saved dashboard layouts for the tenant."""
        try:
            # Return layouts from in-memory storage (for demo)
            layouts = [
                layout for layout in self._dashboard_layouts.values()
                if layout["tenant_id"] == str(tenant_id)
            ]
            
            return layouts
            
        except Exception as e:
            self.logger.error(
                "Failed to get dashboard layouts",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_dashboard_layout(
        self,
        tenant_id: uuid.UUID,
        dashboard_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific dashboard layout by ID."""
        try:
            # Check cache first
            cache_key = f"dashboard_layout:{tenant_id}:{dashboard_id}"
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            # Check in-memory storage
            layout = self._dashboard_layouts.get(dashboard_id)
            if layout and layout["tenant_id"] == str(tenant_id):
                return layout
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get dashboard layout",
                tenant_id=str(tenant_id),
                dashboard_id=dashboard_id,
                error=str(e)
            )
            raise
    
    async def delete_dashboard_layout(
        self,
        tenant_id: uuid.UUID,
        dashboard_id: str
    ) -> bool:
        """Delete a dashboard layout."""
        try:
            # Remove from cache
            cache_key = f"dashboard_layout:{tenant_id}:{dashboard_id}"
            await self.cache_service.delete(cache_key)
            
            # Remove from in-memory storage
            if dashboard_id in self._dashboard_layouts:
                layout = self._dashboard_layouts[dashboard_id]
                if layout["tenant_id"] == str(tenant_id):
                    del self._dashboard_layouts[dashboard_id]
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to delete dashboard layout",
                tenant_id=str(tenant_id),
                dashboard_id=dashboard_id,
                error=str(e)
            )
            raise

    async def get_business_insights(
        self,
        tenant_id: uuid.UUID,
        period: str = "week",
        insight_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get AI-powered business insights and recommendations."""
        try:
            start_date, end_date = self._get_period_dates(period)
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get metrics for analysis
                key_metrics = await self._get_key_metrics(
                    session, tenant_id, start_date, end_date
                )
                
                kpis = await self._calculate_kpis(
                    session, tenant_id, start_date, end_date, period
                )
                
                trends = await self._get_trends(
                    session, tenant_id, start_date, end_date
                )
                
                # Generate insights
                insights = []
                
                if not insight_type or insight_type == "performance":
                    insights.extend(self._analyze_performance(key_metrics, kpis))
                
                if not insight_type or insight_type == "trends":
                    insights.extend(self._analyze_trends(trends))
                
                if not insight_type or insight_type == "anomalies":
                    insights.extend(self._detect_anomalies(key_metrics, trends))
                
                if not insight_type or insight_type == "recommendations":
                    insights.extend(await self._generate_recommendations(
                        key_metrics, kpis, trends
                    ))
                
                return insights
                
        except Exception as e:
            self.logger.error(
                "Failed to get business insights",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_comparative_analysis(
        self,
        tenant_id: uuid.UUID,
        metric: str,
        period1: str,
        period2: str
    ) -> Dict[str, Any]:
        """Get comparative analysis between two time periods."""
        try:
            # Get date ranges for both periods
            start_date1, end_date1 = self._get_period_dates(period1)
            start_date2, end_date2 = self._get_period_dates(period2)
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get metrics for both periods
                metrics1 = await self._get_key_metrics(
                    session, tenant_id, start_date1, end_date1
                )
                metrics2 = await self._get_key_metrics(
                    session, tenant_id, start_date2, end_date2
                )
                
                # Calculate comparison
                comparison = self._compare_metrics(
                    metrics1, metrics2, metric
                )
                
                return {
                    "metric": metric,
                    "period1": {
                        "name": period1,
                        "start_date": start_date1.isoformat(),
                        "end_date": end_date1.isoformat(),
                        "value": comparison["value1"]
                    },
                    "period2": {
                        "name": period2,
                        "start_date": start_date2.isoformat(),
                        "end_date": end_date2.isoformat(),
                        "value": comparison["value2"]
                    },
                    "change": comparison["change"],
                    "change_percentage": comparison["change_percentage"],
                    "trend": comparison["trend"]
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get comparative analysis",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_available_widgets(self) -> List[Dict[str, Any]]:
        """Get list of available dashboard widgets."""
        return [
            {
                "widget_type": "kpi",
                "name": "KPI Card",
                "description": "Display single KPI metric with trend",
                "config_options": ["metric", "target", "format"]
            },
            {
                "widget_type": "chart_line",
                "name": "Line Chart",
                "description": "Time-series line chart",
                "config_options": ["metrics", "time_range", "granularity"]
            },
            {
                "widget_type": "chart_bar",
                "name": "Bar Chart",
                "description": "Comparison bar chart",
                "config_options": ["metrics", "categories", "orientation"]
            },
            {
                "widget_type": "chart_pie",
                "name": "Pie Chart",
                "description": "Distribution pie chart",
                "config_options": ["metric", "categories", "show_legend"]
            },
            {
                "widget_type": "table",
                "name": "Data Table",
                "description": "Tabular data display",
                "config_options": ["columns", "filters", "pagination"]
            },
            {
                "widget_type": "metric_grid",
                "name": "Metrics Grid",
                "description": "Grid of multiple metrics",
                "config_options": ["metrics", "layout", "refresh_rate"]
            },
            {
                "widget_type": "heatmap",
                "name": "Heatmap",
                "description": "Time-based heatmap visualization",
                "config_options": ["metric", "time_range", "color_scale"]
            },
            {
                "widget_type": "gauge",
                "name": "Gauge Chart",
                "description": "Progress gauge visualization",
                "config_options": ["metric", "min", "max", "target"]
            }
        ]
    
    # Private helper methods
    
    def _get_period_dates(self, period: str) -> tuple[date, date]:
        """Calculate start and end dates for a period."""
        today = date.today()
        
        if period == "today":
            return today, today
        elif period == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif period == "week" or period == "this_week":
            start = today - timedelta(days=today.weekday())
            return start, today
        elif period == "last_week":
            start = today - timedelta(days=today.weekday() + 7)
            end = today - timedelta(days=today.weekday() + 1)
            return start, end
        elif period == "month" or period == "this_month":
            start = today.replace(day=1)
            return start, today
        elif period == "last_month":
            if today.month == 1:
                start = date(today.year - 1, 12, 1)
                end = date(today.year - 1, 12, 31)
            else:
                start = date(today.year, today.month - 1, 1)
                end = date(today.year, today.month, 1) - timedelta(days=1)
            return start, end
        elif period == "quarter" or period == "this_quarter":
            quarter = (today.month - 1) // 3
            start = date(today.year, quarter * 3 + 1, 1)
            return start, today
        elif period == "year" or period == "this_year":
            start = date(today.year, 1, 1)
            return start, today
        else:
            # Default to last 7 days
            return today - timedelta(days=7), today

    async def _get_key_metrics(
        self,
        session,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get key business metrics for the period."""
        # Get call analytics
        result = await session.execute(
            select(CallAnalytics).where(
                and_(
                    CallAnalytics.tenant_id == tenant_id,
                    CallAnalytics.date >= start_date,
                    CallAnalytics.date <= end_date
                )
            )
        )
        analytics = result.scalars().all()
        
        # Calculate metrics
        total_calls = sum(a.total_calls for a in analytics)
        answered_calls = sum(a.answered_calls for a in analytics)
        ai_handled = sum(a.ai_handled_calls for a in analytics)
        ai_resolved = sum(a.ai_resolved_calls for a in analytics)
        total_revenue = sum(a.total_cost_cents for a in analytics) / 100
        
        satisfaction_responses = sum(a.satisfaction_responses for a in analytics)
        avg_satisfaction = 0.0
        if satisfaction_responses > 0:
            avg_satisfaction = sum(
                a.average_satisfaction_score * a.satisfaction_responses 
                for a in analytics if a.average_satisfaction_score
            ) / satisfaction_responses
        
        return {
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "missed_calls": sum(a.missed_calls for a in analytics),
            "answer_rate": answered_calls / max(1, total_calls),
            "ai_handled_calls": ai_handled,
            "ai_resolved_calls": ai_resolved,
            "ai_resolution_rate": ai_resolved / max(1, ai_handled),
            "total_revenue": total_revenue,
            "average_satisfaction": avg_satisfaction,
            "vip_calls": sum(a.vip_calls for a in analytics),
            "escalated_calls": sum(a.escalated_calls for a in analytics)
        }
    
    async def _calculate_kpis(
        self,
        session,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        period: str
    ) -> List[Dict[str, Any]]:
        """Calculate KPIs with trends and targets."""
        # Get current period metrics
        current_metrics = await self._get_key_metrics(
            session, tenant_id, start_date, end_date
        )
        
        # Get previous period for comparison
        days_diff = (end_date - start_date).days + 1
        prev_start = start_date - timedelta(days=days_diff)
        prev_end = start_date - timedelta(days=1)
        
        prev_metrics = await self._get_key_metrics(
            session, tenant_id, prev_start, prev_end
        )
        
        # Calculate KPIs
        kpis = []
        
        # Call Volume KPI
        call_change = self._calculate_change_percentage(
            current_metrics["total_calls"],
            prev_metrics["total_calls"]
        )
        kpis.append({
            "name": "Total Calls",
            "category": "calls",
            "value": current_metrics["total_calls"],
            "unit": "calls",
            "change_percentage": call_change,
            "trend": "up" if call_change > 0 else "down" if call_change < 0 else "stable",
            "status": "good" if call_change >= 0 else "warning"
        })
        
        # Answer Rate KPI
        answer_rate = current_metrics["answer_rate"] * 100
        answer_change = self._calculate_change_percentage(
            answer_rate,
            prev_metrics["answer_rate"] * 100
        )
        kpis.append({
            "name": "Answer Rate",
            "category": "efficiency",
            "value": answer_rate,
            "unit": "%",
            "change_percentage": answer_change,
            "trend": "up" if answer_change > 0 else "down" if answer_change < 0 else "stable",
            "target": 95.0,
            "status": "good" if answer_rate >= 95 else "warning" if answer_rate >= 85 else "critical"
        })
        
        # AI Resolution Rate KPI
        ai_resolution = current_metrics["ai_resolution_rate"] * 100
        ai_change = self._calculate_change_percentage(
            ai_resolution,
            prev_metrics["ai_resolution_rate"] * 100
        )
        kpis.append({
            "name": "AI Resolution Rate",
            "category": "efficiency",
            "value": ai_resolution,
            "unit": "%",
            "change_percentage": ai_change,
            "trend": "up" if ai_change > 0 else "down" if ai_change < 0 else "stable",
            "target": 80.0,
            "status": "good" if ai_resolution >= 80 else "warning" if ai_resolution >= 60 else "critical"
        })
        
        # Customer Satisfaction KPI
        satisfaction = current_metrics["average_satisfaction"]
        satisfaction_change = self._calculate_change_percentage(
            satisfaction,
            prev_metrics["average_satisfaction"]
        )
        kpis.append({
            "name": "Customer Satisfaction",
            "category": "satisfaction",
            "value": satisfaction,
            "unit": "/5",
            "change_percentage": satisfaction_change,
            "trend": "up" if satisfaction_change > 0 else "down" if satisfaction_change < 0 else "stable",
            "target": 4.5,
            "status": "good" if satisfaction >= 4.5 else "warning" if satisfaction >= 4.0 else "critical"
        })
        
        # Revenue KPI
        revenue = current_metrics["total_revenue"]
        revenue_change = self._calculate_change_percentage(
            revenue,
            prev_metrics["total_revenue"]
        )
        kpis.append({
            "name": "Total Revenue",
            "category": "revenue",
            "value": revenue,
            "unit": "$",
            "change_percentage": revenue_change,
            "trend": "up" if revenue_change > 0 else "down" if revenue_change < 0 else "stable",
            "status": "good" if revenue_change >= 0 else "warning"
        })
        
        return kpis
    
    async def _get_trends(
        self,
        session,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get trend data for visualizations."""
        result = await session.execute(
            select(CallAnalytics).where(
                and_(
                    CallAnalytics.tenant_id == tenant_id,
                    CallAnalytics.date >= start_date,
                    CallAnalytics.date <= end_date
                )
            ).order_by(CallAnalytics.date)
        )
        analytics = result.scalars().all()
        
        # Build time series
        call_volume_trend = []
        satisfaction_trend = []
        ai_performance_trend = []
        
        for a in analytics:
            call_volume_trend.append({
                "date": a.date.isoformat(),
                "total_calls": a.total_calls,
                "answered_calls": a.answered_calls
            })
            
            if a.average_satisfaction_score:
                satisfaction_trend.append({
                    "date": a.date.isoformat(),
                    "satisfaction": a.average_satisfaction_score
                })
            
            if a.ai_handled_calls > 0:
                ai_performance_trend.append({
                    "date": a.date.isoformat(),
                    "ai_handled": a.ai_handled_calls,
                    "ai_resolved": a.ai_resolved_calls,
                    "resolution_rate": a.ai_resolved_calls / a.ai_handled_calls
                })
        
        return {
            "call_volume": call_volume_trend,
            "satisfaction": satisfaction_trend,
            "ai_performance": ai_performance_trend
        }
    
    async def _generate_insights(
        self,
        key_metrics: Dict[str, Any],
        kpis: List[Dict[str, Any]],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate business insights from metrics."""
        insights = []
        
        # Call volume insights
        if key_metrics["total_calls"] > 1000:
            insights.append(
                f"High call volume detected with {key_metrics['total_calls']} calls. "
                "Consider scaling resources to maintain service quality."
            )
        
        # Answer rate insights
        answer_rate = key_metrics["answer_rate"] * 100
        if answer_rate < 90:
            insights.append(
                f"Answer rate is {answer_rate:.1f}%, below optimal threshold. "
                "Review agent availability and call routing configuration."
            )
        
        # AI performance insights
        ai_resolution = key_metrics["ai_resolution_rate"] * 100
        if ai_resolution > 75:
            insights.append(
                f"Excellent AI performance with {ai_resolution:.1f}% resolution rate. "
                "AI is effectively handling customer inquiries."
            )
        elif ai_resolution < 50:
            insights.append(
                f"AI resolution rate is {ai_resolution:.1f}%, below target. "
                "Consider additional AI training or knowledge base updates."
            )
        
        # Satisfaction insights
        if key_metrics["average_satisfaction"] >= 4.5:
            insights.append(
                "Outstanding customer satisfaction scores. "
                "Current service quality is exceeding expectations."
            )
        elif key_metrics["average_satisfaction"] < 4.0:
            insights.append(
                "Customer satisfaction needs improvement. "
                "Review call quality and agent performance metrics."
            )
        
        return insights
    
    async def _generate_recommendations(
        self,
        key_metrics: Dict[str, Any],
        kpis: List[Dict[str, Any]],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Based on answer rate
        answer_rate = key_metrics["answer_rate"] * 100
        if answer_rate < 95:
            recommendations.append(
                "Increase agent availability during peak hours to improve answer rate"
            )
        
        # Based on AI performance
        ai_resolution = key_metrics["ai_resolution_rate"] * 100
        if ai_resolution < 70:
            recommendations.append(
                "Enhance AI training data with recent successful interactions"
            )
            recommendations.append(
                "Review and update knowledge base with frequently asked questions"
            )
        
        # Based on escalations
        if key_metrics["escalated_calls"] > key_metrics["total_calls"] * 0.1:
            recommendations.append(
                "High escalation rate detected. Review AI routing rules and agent skills"
            )
        
        # Based on VIP calls
        if key_metrics["vip_calls"] > 0:
            recommendations.append(
                "Ensure VIP calls are prioritized with dedicated agent assignment"
            )
        
        return recommendations
    
    def _calculate_change_percentage(
        self,
        current: float,
        previous: float
    ) -> float:
        """Calculate percentage change between two values."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100
    
    def _aggregate_by_granularity(
        self,
        analytics: List,
        granularity: str
    ) -> List[Dict[str, Any]]:
        """Aggregate analytics data by specified granularity."""
        # Simplified aggregation for demo
        result = []
        for a in analytics:
            result.append({
                "date": a.date.isoformat(),
                "total_calls": a.total_calls,
                "answered_calls": a.answered_calls,
                "ai_handled": a.ai_handled_calls,
                "revenue": a.total_cost_cents / 100
            })
        return result
    
    def _analyze_performance(
        self,
        metrics: Dict[str, Any],
        kpis: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze performance metrics."""
        insights = []
        
        for kpi in kpis:
            if kpi["status"] == "critical":
                insights.append({
                    "type": "performance",
                    "severity": "high",
                    "message": f"{kpi['name']} is below target at {kpi['value']:.1f}{kpi['unit']}"
                })
        
        return insights
    
    def _analyze_trends(self, trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze trend patterns."""
        insights = []
        
        # Analyze call volume trend
        if trends.get("call_volume"):
            recent_calls = [t["total_calls"] for t in trends["call_volume"][-7:]]
            if len(recent_calls) >= 2:
                avg_recent = sum(recent_calls) / len(recent_calls)
                if recent_calls[-1] > avg_recent * 1.2:
                    insights.append({
                        "type": "trend",
                        "severity": "medium",
                        "message": "Call volume is trending upward significantly"
                    })
        
        return insights
    
    def _detect_anomalies(
        self,
        metrics: Dict[str, Any],
        trends: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in metrics."""
        anomalies = []
        
        # Check for unusual answer rate
        if metrics["answer_rate"] < 0.7:
            anomalies.append({
                "type": "anomaly",
                "severity": "high",
                "message": "Unusually low answer rate detected"
            })
        
        return anomalies
    
    def _compare_metrics(
        self,
        metrics1: Dict[str, Any],
        metrics2: Dict[str, Any],
        metric_name: str
    ) -> Dict[str, Any]:
        """Compare specific metric between two periods."""
        value1 = metrics1.get(metric_name, 0)
        value2 = metrics2.get(metric_name, 0)
        
        change = value1 - value2
        change_pct = self._calculate_change_percentage(value1, value2)
        
        return {
            "value1": value1,
            "value2": value2,
            "change": change,
            "change_percentage": change_pct,
            "trend": "up" if change > 0 else "down" if change < 0 else "stable"
        }
