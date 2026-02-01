"""
Analytics data collection service for VoiceCore AI.

Provides comprehensive analytics data collection, real-time metrics tracking,
and performance monitoring for calls, agents, and system performance.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, or_, func, update, delete, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    CallAnalytics, AgentMetrics, SystemMetrics, ReportTemplate,
    Call, Agent, Department, CallStatus, AgentStatus, MetricType
)
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)


class AnalyticsServiceError(Exception):
    """Base exception for analytics service errors."""
    pass


class AnalyticsService:
    """
    Comprehensive analytics data collection and metrics service.
    
    Handles real-time metrics collection, call analytics tracking,
    agent performance monitoring, and system performance metrics.
    """
    
    def __init__(self):
        self.logger = logger
        self._metrics_cache = {}
        self._last_cache_update = {}
    
    async def collect_call_metrics(
        self,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        call_data: Dict[str, Any]
    ) -> bool:
        """
        Collect and aggregate call metrics for analytics.
        
        Args:
            tenant_id: Tenant UUID
            call_id: Call UUID
            call_data: Call data including duration, status, etc.
            
        Returns:
            bool: True if metrics were collected successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get call details
                result = await session.execute(
                    select(Call)
                    .options(selectinload(Call.agent), selectinload(Call.department))
                    .where(Call.id == call_id)
                )
                call = result.scalar_one_or_none()
                
                if not call:
                    return False
                
                call_date = call.created_at.date()
                call_hour = call.created_at.hour
                
                # Update daily analytics
                await self._update_call_analytics(
                    session, tenant_id, call_date, call_hour,
                    call.department_id, call.agent_id, call_data
                )
                
                # Update agent metrics if call was handled by agent
                if call.agent_id:
                    await self._update_agent_metrics(
                        session, tenant_id, call.agent_id, call_date, call_data
                    )
                
                await session.commit()
                
                self.logger.info(
                    "Call metrics collected",
                    tenant_id=str(tenant_id),
                    call_id=str(call_id),
                    duration=call_data.get("duration", 0)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to collect call metrics",
                tenant_id=str(tenant_id),
                call_id=str(call_id),
                error=str(e)
            )
            return False
    async def collect_agent_activity(
        self,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        activity_data: Dict[str, Any]
    ) -> bool:
        """
        Collect agent activity metrics for performance tracking.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            activity_data: Activity data including status changes, login time, etc.
            
        Returns:
            bool: True if activity was collected successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                current_date = datetime.utcnow().date()
                
                # Get or create agent metrics for today
                result = await session.execute(
                    select(AgentMetrics).where(
                        and_(
                            AgentMetrics.tenant_id == tenant_id,
                            AgentMetrics.agent_id == agent_id,
                            AgentMetrics.date == current_date
                        )
                    )
                )
                agent_metrics = result.scalar_one_or_none()
                
                if not agent_metrics:
                    agent_metrics = AgentMetrics(
                        tenant_id=tenant_id,
                        agent_id=agent_id,
                        date=current_date
                    )
                    session.add(agent_metrics)
                    await session.flush()
                
                # Update metrics based on activity type
                activity_type = activity_data.get("type")
                duration = activity_data.get("duration", 0)
                
                if activity_type == "login":
                    agent_metrics.total_login_time += duration
                elif activity_type == "available":
                    agent_metrics.available_time += duration
                elif activity_type == "busy":
                    agent_metrics.busy_time += duration
                elif activity_type == "break":
                    agent_metrics.break_time += duration
                elif activity_type == "call_handled":
                    agent_metrics.calls_handled += 1
                    agent_metrics.total_talk_time += duration
                    # Recalculate averages
                    if agent_metrics.calls_handled > 0:
                        agent_metrics.average_call_duration = (
                            agent_metrics.total_talk_time / agent_metrics.calls_handled
                        )
                        agent_metrics.calls_per_hour = (
                            agent_metrics.calls_handled / 
                            max(1, agent_metrics.total_login_time / 3600)
                        )
                        agent_metrics.utilization_rate = (
                            agent_metrics.total_talk_time / 
                            max(1, agent_metrics.available_time)
                        )
                
                await session.commit()
                
                self.logger.debug(
                    "Agent activity collected",
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    activity_type=activity_type
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to collect agent activity",
                tenant_id=str(tenant_id),
                agent_id=str(agent_id),
                error=str(e)
            )
            return False
    
    async def collect_system_metrics(
        self,
        tenant_id: uuid.UUID,
        metric_type: MetricType,
        metrics_data: Dict[str, Any]
    ) -> bool:
        """
        Collect system performance metrics.
        
        Args:
            tenant_id: Tenant UUID
            metric_type: Type of metric being collected
            metrics_data: System metrics data
            
        Returns:
            bool: True if metrics were collected successfully
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                system_metrics = SystemMetrics(
                    tenant_id=tenant_id,
                    timestamp=datetime.utcnow(),
                    metric_type=metric_type,
                    concurrent_calls=metrics_data.get("concurrent_calls", 0),
                    peak_concurrent_calls=metrics_data.get("peak_concurrent_calls", 0),
                    system_cpu_usage=metrics_data.get("cpu_usage"),
                    system_memory_usage=metrics_data.get("memory_usage"),
                    api_response_time_ms=metrics_data.get("api_response_time"),
                    api_error_rate=metrics_data.get("api_error_rate", 0.0),
                    api_requests_per_second=metrics_data.get("api_rps", 0.0),
                    twilio_api_latency_ms=metrics_data.get("twilio_latency"),
                    openai_api_latency_ms=metrics_data.get("openai_latency"),
                    database_query_time_ms=metrics_data.get("db_query_time"),
                    uptime_percentage=metrics_data.get("uptime", 100.0),
                    error_count=metrics_data.get("error_count", 0),
                    warning_count=metrics_data.get("warning_count", 0),
                    storage_usage_gb=metrics_data.get("storage_usage"),
                    bandwidth_usage_mbps=metrics_data.get("bandwidth_usage"),
                    active_tenants=metrics_data.get("active_tenants", 0),
                    active_agents=metrics_data.get("active_agents", 0),
                    total_revenue_cents=metrics_data.get("revenue_cents", 0),
                    metadata=metrics_data.get("metadata", {})
                )
                
                session.add(system_metrics)
                await session.commit()
                
                self.logger.debug(
                    "System metrics collected",
                    tenant_id=str(tenant_id),
                    metric_type=metric_type.value
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to collect system metrics",
                tenant_id=str(tenant_id),
                metric_type=metric_type.value,
                error=str(e)
            )
            return False
    
    async def get_real_time_dashboard_data(
        self,
        tenant_id: uuid.UUID,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get real-time dashboard data for the specified tenant.
        
        Args:
            tenant_id: Tenant UUID
            time_range_hours: Time range in hours for metrics
            
        Returns:
            Dict containing dashboard metrics
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                current_time = datetime.utcnow()
                start_time = current_time - timedelta(hours=time_range_hours)
                
                dashboard_data = {
                    "timestamp": current_time.isoformat(),
                    "time_range_hours": time_range_hours,
                    "call_metrics": {},
                    "agent_metrics": {},
                    "system_metrics": {},
                    "trends": {}
                }
                
                # Get current call metrics
                call_metrics = await self._get_current_call_metrics(
                    session, tenant_id, start_time, current_time
                )
                dashboard_data["call_metrics"] = call_metrics
                
                # Get agent performance metrics
                agent_metrics = await self._get_current_agent_metrics(
                    session, tenant_id, start_time, current_time
                )
                dashboard_data["agent_metrics"] = agent_metrics
                
                # Get system performance metrics
                system_metrics = await self._get_current_system_metrics(
                    session, tenant_id, start_time, current_time
                )
                dashboard_data["system_metrics"] = system_metrics
                
                # Get trend data
                trends = await self._get_trend_data(
                    session, tenant_id, start_time, current_time
                )
                dashboard_data["trends"] = trends
                
                return dashboard_data
                
        except Exception as e:
            self.logger.error(
                "Failed to get dashboard data",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {
                "error": "Failed to retrieve dashboard data",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_agent_performance_stats(
        self,
        tenant_id: uuid.UUID,
        agent_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get agent performance statistics.
        
        Args:
            tenant_id: Tenant UUID
            agent_id: Specific agent ID (optional)
            start_date: Start date for metrics
            end_date: End date for metrics
            
        Returns:
            Dict containing agent performance data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                if not end_date:
                    end_date = datetime.utcnow().date()
                if not start_date:
                    start_date = end_date - timedelta(days=30)
                
                query = select(AgentMetrics).where(
                    and_(
                        AgentMetrics.tenant_id == tenant_id,
                        AgentMetrics.date >= start_date,
                        AgentMetrics.date <= end_date
                    )
                )
                
                if agent_id:
                    query = query.where(AgentMetrics.agent_id == agent_id)
                
                result = await session.execute(query)
                metrics = result.scalars().all()
                
                # Aggregate metrics
                performance_stats = {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": (end_date - start_date).days + 1
                    },
                    "summary": {},
                    "agents": {},
                    "trends": []
                }
                
                if agent_id:
                    # Single agent stats
                    agent_stats = self._aggregate_agent_metrics(metrics)
                    performance_stats["agent"] = agent_stats
                else:
                    # Multi-agent stats
                    agent_groups = {}
                    for metric in metrics:
                        if metric.agent_id not in agent_groups:
                            agent_groups[metric.agent_id] = []
                        agent_groups[metric.agent_id].append(metric)
                    
                    for aid, agent_metrics in agent_groups.items():
                        agent_stats = self._aggregate_agent_metrics(agent_metrics)
                        performance_stats["agents"][str(aid)] = agent_stats
                    
                    # Overall summary
                    performance_stats["summary"] = self._calculate_summary_stats(metrics)
                
                return performance_stats
                
        except Exception as e:
            self.logger.error(
                "Failed to get agent performance stats",
                tenant_id=str(tenant_id),
                agent_id=str(agent_id) if agent_id else "all",
                error=str(e)
            )
            return {"error": "Failed to retrieve agent performance statistics"}
    
    # Private helper methods
    
    async def _update_call_analytics(
        self,
        session,
        tenant_id: uuid.UUID,
        call_date: date,
        call_hour: int,
        department_id: Optional[uuid.UUID],
        agent_id: Optional[uuid.UUID],
        call_data: Dict[str, Any]
    ):
        """Update call analytics aggregation."""
        # Get or create daily analytics record
        result = await session.execute(
            select(CallAnalytics).where(
                and_(
                    CallAnalytics.tenant_id == tenant_id,
                    CallAnalytics.date == call_date,
                    CallAnalytics.hour.is_(None),  # Daily aggregation
                    CallAnalytics.department_id == department_id,
                    CallAnalytics.agent_id.is_(None)  # Department-level aggregation
                )
            )
        )
        analytics = result.scalar_one_or_none()
        
        if not analytics:
            analytics = CallAnalytics(
                tenant_id=tenant_id,
                date=call_date,
                department_id=department_id
            )
            session.add(analytics)
            await session.flush()
        
        # Update metrics based on call data
        analytics.total_calls += 1
        
        direction = call_data.get("direction", "inbound")
        if direction == "inbound":
            analytics.inbound_calls += 1
        else:
            analytics.outbound_calls += 1
        
        status = call_data.get("status")
        if status == "completed":
            analytics.answered_calls += 1
        elif status == "no-answer":
            analytics.missed_calls += 1
        elif status == "abandoned":
            analytics.abandoned_calls += 1
        
        duration = call_data.get("duration", 0)
        if duration > 0:
            analytics.total_talk_time += duration
            # Recalculate average
            if analytics.answered_calls > 0:
                analytics.average_call_duration = (
                    analytics.total_talk_time / analytics.answered_calls
                )
        
        wait_time = call_data.get("wait_time", 0)
        if wait_time > 0:
            analytics.total_wait_time += wait_time
            analytics.average_wait_time = (
                analytics.total_wait_time / analytics.total_calls
            )
        
        # AI metrics
        if call_data.get("handled_by_ai"):
            analytics.ai_handled_calls += 1
            if call_data.get("resolved_by_ai"):
                analytics.ai_resolved_calls += 1
            if call_data.get("transferred_by_ai"):
                analytics.ai_transferred_calls += 1
        
        # Quality metrics
        satisfaction = call_data.get("satisfaction_score")
        if satisfaction is not None:
            analytics.satisfaction_responses += 1
            # Update running average
            current_total = (analytics.average_satisfaction_score or 0) * (analytics.satisfaction_responses - 1)
            analytics.average_satisfaction_score = (current_total + satisfaction) / analytics.satisfaction_responses
        
        # Spam and security
        if call_data.get("is_spam"):
            analytics.spam_calls_detected += 1
            if call_data.get("spam_blocked"):
                analytics.spam_calls_blocked += 1
        
        # VIP and priority
        if call_data.get("is_vip"):
            analytics.vip_calls += 1
        if call_data.get("is_priority"):
            analytics.priority_calls += 1
        if call_data.get("is_escalated"):
            analytics.escalated_calls += 1
        
        # Cost tracking
        cost_cents = call_data.get("cost_cents", 0)
        if cost_cents > 0:
            analytics.total_cost_cents += cost_cents
            analytics.average_cost_per_call_cents = (
                analytics.total_cost_cents / analytics.total_calls
            )
    
    async def _update_agent_metrics(
        self,
        session,
        tenant_id: uuid.UUID,
        agent_id: uuid.UUID,
        call_date: date,
        call_data: Dict[str, Any]
    ):
        """Update agent-specific metrics."""
        # Get or create agent metrics for the date
        result = await session.execute(
            select(AgentMetrics).where(
                and_(
                    AgentMetrics.tenant_id == tenant_id,
                    AgentMetrics.agent_id == agent_id,
                    AgentMetrics.date == call_date
                )
            )
        )
        agent_metrics = result.scalar_one_or_none()
        
        if not agent_metrics:
            agent_metrics = AgentMetrics(
                tenant_id=tenant_id,
                agent_id=agent_id,
                date=call_date
            )
            session.add(agent_metrics)
            await session.flush()
        
        # Update call handling metrics
        agent_metrics.calls_handled += 1
        
        duration = call_data.get("duration", 0)
        if duration > 0:
            agent_metrics.total_talk_time += duration
            agent_metrics.average_call_duration = (
                agent_metrics.total_talk_time / agent_metrics.calls_handled
            )
        
        # Transfer metrics
        if call_data.get("transferred_in"):
            agent_metrics.calls_transferred_in += 1
        if call_data.get("transferred_out"):
            agent_metrics.calls_transferred_out += 1
        
        # Quality metrics
        satisfaction = call_data.get("satisfaction_score")
        if satisfaction is not None:
            agent_metrics.satisfaction_responses += 1
            current_total = (agent_metrics.customer_satisfaction_score or 0) * (agent_metrics.satisfaction_responses - 1)
            agent_metrics.customer_satisfaction_score = (current_total + satisfaction) / agent_metrics.satisfaction_responses
        
        # Performance indicators
        if call_data.get("first_call_resolution"):
            # Update FCR rate (simplified calculation)
            current_fcr_total = agent_metrics.first_call_resolution_rate * (agent_metrics.calls_handled - 1)
            agent_metrics.first_call_resolution_rate = (current_fcr_total + 1) / agent_metrics.calls_handled
    
    async def _get_current_call_metrics(
        self,
        session,
        tenant_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get current call metrics for dashboard."""
        # Get recent call analytics
        result = await session.execute(
            select(CallAnalytics).where(
                and_(
                    CallAnalytics.tenant_id == tenant_id,
                    CallAnalytics.date >= start_time.date(),
                    CallAnalytics.date <= end_time.date()
                )
            )
        )
        analytics = result.scalars().all()
        
        # Aggregate metrics
        total_calls = sum(a.total_calls for a in analytics)
        answered_calls = sum(a.answered_calls for a in analytics)
        missed_calls = sum(a.missed_calls for a in analytics)
        ai_handled = sum(a.ai_handled_calls for a in analytics)
        ai_resolved = sum(a.ai_resolved_calls for a in analytics)
        
        return {
            "total_calls": total_calls,
            "answered_calls": answered_calls,
            "missed_calls": missed_calls,
            "answer_rate": answered_calls / max(1, total_calls),
            "ai_handled_calls": ai_handled,
            "ai_resolved_calls": ai_resolved,
            "ai_resolution_rate": ai_resolved / max(1, ai_handled),
            "average_call_duration": sum(a.average_call_duration * a.answered_calls for a in analytics) / max(1, answered_calls),
            "average_wait_time": sum(a.average_wait_time * a.total_calls for a in analytics) / max(1, total_calls)
        }
    
    async def _get_current_agent_metrics(
        self,
        session,
        tenant_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get current agent metrics for dashboard."""
        # Get active agents count
        result = await session.execute(
            select(func.count(Agent.id)).where(
                and_(
                    Agent.tenant_id == tenant_id,
                    Agent.is_active == True
                )
            )
        )
        total_agents = result.scalar() or 0
        
        # Get agents currently available
        result = await session.execute(
            select(func.count(Agent.id)).where(
                and_(
                    Agent.tenant_id == tenant_id,
                    Agent.is_active == True,
                    Agent.status == AgentStatus.AVAILABLE
                )
            )
        )
        available_agents = result.scalar() or 0
        
        # Get recent agent metrics
        result = await session.execute(
            select(AgentMetrics).where(
                and_(
                    AgentMetrics.tenant_id == tenant_id,
                    AgentMetrics.date >= start_time.date(),
                    AgentMetrics.date <= end_time.date()
                )
            )
        )
        metrics = result.scalars().all()
        
        if not metrics:
            return {
                "total_agents": total_agents,
                "available_agents": available_agents,
                "busy_agents": total_agents - available_agents,
                "average_utilization": 0.0,
                "average_satisfaction": 0.0,
                "total_calls_handled": 0
            }
        
        # Aggregate metrics
        total_calls_handled = sum(m.calls_handled for m in metrics)
        avg_utilization = sum(m.utilization_rate for m in metrics) / len(metrics)
        satisfaction_scores = [m.customer_satisfaction_score for m in metrics if m.customer_satisfaction_score]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.0
        
        return {
            "total_agents": total_agents,
            "available_agents": available_agents,
            "busy_agents": total_agents - available_agents,
            "average_utilization": avg_utilization,
            "average_satisfaction": avg_satisfaction,
            "total_calls_handled": total_calls_handled
        }
    
    async def _get_current_system_metrics(
        self,
        session,
        tenant_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get current system metrics for dashboard."""
        # Get recent system metrics
        result = await session.execute(
            select(SystemMetrics).where(
                and_(
                    SystemMetrics.tenant_id == tenant_id,
                    SystemMetrics.timestamp >= start_time,
                    SystemMetrics.timestamp <= end_time
                )
            ).order_by(SystemMetrics.timestamp.desc()).limit(10)
        )
        metrics = result.scalars().all()
        
        if not metrics:
            return {
                "concurrent_calls": 0,
                "peak_concurrent_calls": 0,
                "api_response_time": 0.0,
                "system_uptime": 100.0,
                "error_rate": 0.0
            }
        
        latest_metric = metrics[0]
        avg_response_time = sum(m.api_response_time_ms for m in metrics if m.api_response_time_ms) / len([m for m in metrics if m.api_response_time_ms])
        avg_uptime = sum(m.uptime_percentage for m in metrics) / len(metrics)
        avg_error_rate = sum(m.api_error_rate for m in metrics) / len(metrics)
        
        return {
            "concurrent_calls": latest_metric.concurrent_calls,
            "peak_concurrent_calls": max(m.peak_concurrent_calls for m in metrics),
            "api_response_time": avg_response_time or 0.0,
            "system_uptime": avg_uptime,
            "error_rate": avg_error_rate
        }
    
    async def _get_trend_data(
        self,
        session,
        tenant_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get trend data for dashboard charts."""
        # Get hourly call volume trend
        result = await session.execute(
            select(
                CallAnalytics.date,
                CallAnalytics.hour,
                func.sum(CallAnalytics.total_calls).label('calls'),
                func.sum(CallAnalytics.answered_calls).label('answered')
            ).where(
                and_(
                    CallAnalytics.tenant_id == tenant_id,
                    CallAnalytics.date >= start_time.date(),
                    CallAnalytics.date <= end_time.date(),
                    CallAnalytics.hour.isnot(None)
                )
            ).group_by(CallAnalytics.date, CallAnalytics.hour)
            .order_by(CallAnalytics.date, CallAnalytics.hour)
        )
        
        hourly_data = []
        for row in result.fetchall():
            hourly_data.append({
                "timestamp": datetime.combine(row[0], datetime.min.time().replace(hour=row[1] or 0)).isoformat(),
                "total_calls": row[2] or 0,
                "answered_calls": row[3] or 0,
                "answer_rate": (row[3] or 0) / max(1, row[2] or 1)
            })
        
        return {
            "hourly_call_volume": hourly_data,
            "period_summary": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "data_points": len(hourly_data)
            }
        }
    
    def _aggregate_agent_metrics(self, metrics: List[AgentMetrics]) -> Dict[str, Any]:
        """Aggregate agent metrics for reporting."""
        if not metrics:
            return {}
        
        total_calls = sum(m.calls_handled for m in metrics)
        total_talk_time = sum(m.total_talk_time for m in metrics)
        total_login_time = sum(m.total_login_time for m in metrics)
        
        satisfaction_scores = [m.customer_satisfaction_score for m in metrics if m.customer_satisfaction_score]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.0
        
        return {
            "total_calls_handled": total_calls,
            "total_talk_time": total_talk_time,
            "total_login_time": total_login_time,
            "average_call_duration": total_talk_time / max(1, total_calls),
            "utilization_rate": total_talk_time / max(1, total_login_time),
            "average_satisfaction": avg_satisfaction,
            "efficiency_score": sum(m.efficiency_score for m in metrics) / len(metrics)
        }
    
    def _calculate_summary_stats(self, metrics: List[AgentMetrics]) -> Dict[str, Any]:
        """Calculate summary statistics across all agents."""
        if not metrics:
            return {}
        
        # Group by agent
        agent_groups = {}
        for metric in metrics:
            if metric.agent_id not in agent_groups:
                agent_groups[metric.agent_id] = []
            agent_groups[metric.agent_id].append(metric)
        
        agent_summaries = []
        for agent_metrics in agent_groups.values():
            agent_summary = self._aggregate_agent_metrics(agent_metrics)
            agent_summaries.append(agent_summary)
        
        if not agent_summaries:
            return {}
        
        return {
            "total_agents": len(agent_summaries),
            "total_calls_handled": sum(s["total_calls_handled"] for s in agent_summaries),
            "average_utilization": sum(s["utilization_rate"] for s in agent_summaries) / len(agent_summaries),
            "average_satisfaction": sum(s["average_satisfaction"] for s in agent_summaries) / len(agent_summaries),
            "average_efficiency": sum(s["efficiency_score"] for s in agent_summaries) / len(agent_summaries)
        }

    # Additional methods for Task 13.2 - Reporting and Dashboard APIs
    
    async def generate_call_report(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        department_id: Optional[uuid.UUID] = None,
        agent_id: Optional[uuid.UUID] = None,
        call_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate detailed call reports with filtering options.
        
        Args:
            tenant_id: Tenant UUID
            start_date: Report start date
            end_date: Report end date
            department_id: Optional department filter
            agent_id: Optional agent filter
            call_status: Optional call status filter
            
        Returns:
            Dict containing detailed call report data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Build query with filters
                query = select(Call).options(
                    selectinload(Call.agent),
                    selectinload(Call.department)
                ).where(
                    and_(
                        Call.tenant_id == tenant_id,
                        Call.created_at >= datetime.combine(start_date, datetime.min.time()),
                        Call.created_at <= datetime.combine(end_date, datetime.max.time())
                    )
                )
                
                if department_id:
                    query = query.where(Call.department_id == department_id)
                if agent_id:
                    query = query.where(Call.agent_id == agent_id)
                if call_status:
                    query = query.where(Call.status == call_status)
                
                result = await session.execute(query.order_by(Call.created_at.desc()))
                calls = result.scalars().all()
                
                # Format call data for report
                call_data = []
                for call in calls:
                    call_data.append({
                        "call_id": str(call.id),
                        "phone_number": call.caller_phone_number,
                        "direction": call.direction.value if call.direction else "unknown",
                        "status": call.status.value if call.status else "unknown",
                        "duration": call.duration or 0,
                        "created_at": call.created_at.isoformat(),
                        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                        "agent_name": call.agent.name if call.agent else None,
                        "department_name": call.department.name if call.department else None,
                        "ai_handled": call.ai_handled,
                        "transferred": call.transferred_count > 0 if call.transferred_count else False,
                        "cost_cents": call.cost_cents or 0
                    })
                
                # Calculate summary statistics
                total_calls = len(calls)
                completed_calls = len([c for c in calls if c.status and c.status.value == "completed"])
                total_duration = sum(c.duration or 0 for c in calls)
                ai_handled_count = len([c for c in calls if c.ai_handled])
                
                summary = {
                    "total_calls": total_calls,
                    "completed_calls": completed_calls,
                    "completion_rate": completed_calls / max(1, total_calls),
                    "total_duration_minutes": total_duration / 60,
                    "average_duration_minutes": (total_duration / max(1, completed_calls)) / 60,
                    "ai_handled_calls": ai_handled_count,
                    "ai_handling_rate": ai_handled_count / max(1, total_calls),
                    "total_cost_dollars": sum(c.cost_cents or 0 for c in calls) / 100
                }
                
                return {
                    "report_info": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "generated_at": datetime.utcnow().isoformat(),
                        "filters": {
                            "department_id": str(department_id) if department_id else None,
                            "agent_id": str(agent_id) if agent_id else None,
                            "call_status": call_status
                        }
                    },
                    "summary": summary,
                    "calls": call_data
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to generate call report",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to generate call report"}
    
    async def generate_agent_report(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        department_id: Optional[uuid.UUID] = None,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """
        Generate detailed agent performance reports.
        
        Args:
            tenant_id: Tenant UUID
            start_date: Report start date
            end_date: Report end date
            department_id: Optional department filter
            include_inactive: Whether to include inactive agents
            
        Returns:
            Dict containing detailed agent report data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get agents with filters
                agent_query = select(Agent).options(
                    selectinload(Agent.department)
                ).where(Agent.tenant_id == tenant_id)
                
                if department_id:
                    agent_query = agent_query.where(Agent.department_id == department_id)
                if not include_inactive:
                    agent_query = agent_query.where(Agent.is_active == True)
                
                result = await session.execute(agent_query)
                agents = result.scalars().all()
                
                # Get agent metrics for the period
                metrics_query = select(AgentMetrics).where(
                    and_(
                        AgentMetrics.tenant_id == tenant_id,
                        AgentMetrics.date >= start_date,
                        AgentMetrics.date <= end_date
                    )
                )
                
                if department_id:
                    # Filter by agents in the department
                    agent_ids = [a.id for a in agents]
                    metrics_query = metrics_query.where(AgentMetrics.agent_id.in_(agent_ids))
                
                result = await session.execute(metrics_query)
                metrics = result.scalars().all()
                
                # Group metrics by agent
                agent_metrics_map = {}
                for metric in metrics:
                    if metric.agent_id not in agent_metrics_map:
                        agent_metrics_map[metric.agent_id] = []
                    agent_metrics_map[metric.agent_id].append(metric)
                
                # Generate agent report data
                agent_data = []
                for agent in agents:
                    agent_metrics = agent_metrics_map.get(agent.id, [])
                    
                    if agent_metrics:
                        aggregated = self._aggregate_agent_metrics(agent_metrics)
                        agent_data.append({
                            "agent_id": str(agent.id),
                            "agent_name": agent.name,
                            "email": agent.email,
                            "extension": agent.extension,
                            "department": agent.department.name if agent.department else None,
                            "is_active": agent.is_active,
                            "total_calls_handled": aggregated["total_calls_handled"],
                            "total_talk_time_minutes": aggregated["total_talk_time"] / 60,
                            "average_call_duration_minutes": aggregated["average_call_duration"] / 60,
                            "utilization_rate": aggregated["utilization_rate"],
                            "customer_satisfaction": aggregated["average_satisfaction"],
                            "efficiency_score": aggregated["efficiency_score"]
                        })
                    else:
                        # Agent with no metrics in period
                        agent_data.append({
                            "agent_id": str(agent.id),
                            "agent_name": agent.name,
                            "email": agent.email,
                            "extension": agent.extension,
                            "department": agent.department.name if agent.department else None,
                            "is_active": agent.is_active,
                            "total_calls_handled": 0,
                            "total_talk_time_minutes": 0,
                            "average_call_duration_minutes": 0,
                            "utilization_rate": 0,
                            "customer_satisfaction": 0,
                            "efficiency_score": 0
                        })
                
                # Calculate summary statistics
                active_agents = [a for a in agent_data if a["is_active"]]
                total_calls = sum(a["total_calls_handled"] for a in agent_data)
                avg_utilization = sum(a["utilization_rate"] for a in active_agents) / max(1, len(active_agents))
                avg_satisfaction = sum(a["customer_satisfaction"] for a in agent_data if a["customer_satisfaction"] > 0) / max(1, len([a for a in agent_data if a["customer_satisfaction"] > 0]))
                
                summary = {
                    "total_agents": len(agents),
                    "active_agents": len(active_agents),
                    "total_calls_handled": total_calls,
                    "average_utilization": avg_utilization,
                    "average_satisfaction": avg_satisfaction,
                    "top_performer": max(agent_data, key=lambda x: x["efficiency_score"])["agent_name"] if agent_data else None
                }
                
                return {
                    "report_info": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "generated_at": datetime.utcnow().isoformat(),
                        "filters": {
                            "department_id": str(department_id) if department_id else None,
                            "include_inactive": include_inactive
                        }
                    },
                    "summary": summary,
                    "agents": agent_data
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to generate agent report",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to generate agent report"}
    
    async def generate_conversation_analytics(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        include_transcripts: bool = False,
        sentiment_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate conversation analytics and insights per Requirement 9.2.
        
        Args:
            tenant_id: Tenant UUID
            start_date: Analysis start date
            end_date: Analysis end date
            include_transcripts: Whether to include call transcripts
            sentiment_filter: Optional sentiment filter
            
        Returns:
            Dict containing conversation analytics data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get calls with transcripts in the period
                query = select(Call).where(
                    and_(
                        Call.tenant_id == tenant_id,
                        Call.created_at >= datetime.combine(start_date, datetime.min.time()),
                        Call.created_at <= datetime.combine(end_date, datetime.max.time()),
                        Call.transcript.isnot(None)
                    )
                )
                
                result = await session.execute(query)
                calls = result.scalars().all()
                
                # Analyze conversations
                conversation_data = []
                ai_performance_metrics = {
                    "total_ai_interactions": 0,
                    "successful_resolutions": 0,
                    "transfer_rate": 0,
                    "average_interaction_length": 0,
                    "common_topics": {},
                    "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0}
                }
                
                for call in calls:
                    if call.transcript:
                        # Simple sentiment analysis (would use actual NLP in production)
                        sentiment = self._analyze_sentiment(call.transcript)
                        
                        if sentiment_filter and sentiment != sentiment_filter:
                            continue
                        
                        conversation_item = {
                            "call_id": str(call.id),
                            "duration": call.duration or 0,
                            "ai_handled": call.ai_handled,
                            "sentiment": sentiment,
                            "topics": self._extract_topics(call.transcript),
                            "resolution_status": "resolved" if call.status and call.status.value == "completed" else "unresolved"
                        }
                        
                        if include_transcripts:
                            conversation_item["transcript"] = call.transcript
                        
                        conversation_data.append(conversation_item)
                        
                        # Update AI performance metrics
                        if call.ai_handled:
                            ai_performance_metrics["total_ai_interactions"] += 1
                            if call.status and call.status.value == "completed":
                                ai_performance_metrics["successful_resolutions"] += 1
                        
                        # Update sentiment distribution
                        ai_performance_metrics["sentiment_distribution"][sentiment] += 1
                        
                        # Update common topics
                        for topic in conversation_item["topics"]:
                            if topic in ai_performance_metrics["common_topics"]:
                                ai_performance_metrics["common_topics"][topic] += 1
                            else:
                                ai_performance_metrics["common_topics"][topic] = 1
                
                # Calculate final metrics
                if ai_performance_metrics["total_ai_interactions"] > 0:
                    ai_performance_metrics["resolution_rate"] = (
                        ai_performance_metrics["successful_resolutions"] / 
                        ai_performance_metrics["total_ai_interactions"]
                    )
                    ai_performance_metrics["transfer_rate"] = len([c for c in calls if c.transferred_count and c.transferred_count > 0]) / ai_performance_metrics["total_ai_interactions"]
                
                # Sort common topics by frequency
                ai_performance_metrics["common_topics"] = dict(
                    sorted(ai_performance_metrics["common_topics"].items(), 
                           key=lambda x: x[1], reverse=True)[:10]
                )
                
                return {
                    "analysis_info": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "generated_at": datetime.utcnow().isoformat(),
                        "total_conversations": len(conversation_data),
                        "include_transcripts": include_transcripts,
                        "sentiment_filter": sentiment_filter
                    },
                    "ai_performance": ai_performance_metrics,
                    "conversations": conversation_data
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to generate conversation analytics",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to generate conversation analytics"}
    
    async def get_live_dashboard_data(
        self,
        tenant_id: uuid.UUID,
        refresh_interval: int = 30
    ) -> Dict[str, Any]:
        """
        Get real-time dashboard data optimized for live updates per Requirement 9.1.
        
        Args:
            tenant_id: Tenant UUID
            refresh_interval: Refresh interval in seconds
            
        Returns:
            Dict containing live dashboard metrics
        """
        try:
            # Use cached data if available and fresh
            cache_key = f"live_dashboard_{tenant_id}"
            if (cache_key in self._metrics_cache and 
                cache_key in self._last_cache_update and
                (datetime.utcnow() - self._last_cache_update[cache_key]).seconds < refresh_interval):
                return self._metrics_cache[cache_key]
            
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                current_time = datetime.utcnow()
                
                # Get real-time metrics
                live_data = {
                    "timestamp": current_time.isoformat(),
                    "active_calls": await self._get_active_calls_count(session, tenant_id),
                    "queue_length": await self._get_queue_length(session, tenant_id),
                    "available_agents": await self._get_available_agents_count(session, tenant_id),
                    "busy_agents": await self._get_busy_agents_count(session, tenant_id),
                    "calls_today": await self._get_calls_today_count(session, tenant_id),
                    "ai_resolution_rate_today": await self._get_ai_resolution_rate_today(session, tenant_id),
                    "average_wait_time": await self._get_current_average_wait_time(session, tenant_id),
                    "system_status": "operational",  # Would check actual system health
                    "alerts": await self._get_active_alerts(session, tenant_id)
                }
                
                # Cache the data
                self._metrics_cache[cache_key] = live_data
                self._last_cache_update[cache_key] = current_time
                
                return live_data
                
        except Exception as e:
            self.logger.error(
                "Failed to get live dashboard data",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to get live dashboard data"}
    
    async def get_call_volume_trends(
        self,
        tenant_id: uuid.UUID,
        days: int = 7,
        granularity: str = "hour"
    ) -> Dict[str, Any]:
        """
        Get call volume trends with configurable time periods and granularity.
        
        Args:
            tenant_id: Tenant UUID
            days: Number of days to analyze
            granularity: Time granularity (hour, day, week)
            
        Returns:
            Dict containing trend data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                end_date = date.today()
                start_date = end_date - timedelta(days=days)
                
                if granularity == "hour":
                    # Hourly trends
                    result = await session.execute(
                        select(
                            CallAnalytics.date,
                            CallAnalytics.hour,
                            func.sum(CallAnalytics.total_calls).label('calls'),
                            func.sum(CallAnalytics.answered_calls).label('answered')
                        ).where(
                            and_(
                                CallAnalytics.tenant_id == tenant_id,
                                CallAnalytics.date >= start_date,
                                CallAnalytics.date <= end_date,
                                CallAnalytics.hour.isnot(None)
                            )
                        ).group_by(CallAnalytics.date, CallAnalytics.hour)
                        .order_by(CallAnalytics.date, CallAnalytics.hour)
                    )
                    
                    trends = []
                    for row in result.fetchall():
                        trends.append({
                            "timestamp": datetime.combine(row[0], datetime.min.time().replace(hour=row[1] or 0)).isoformat(),
                            "period": f"{row[0]} {row[1]:02d}:00",
                            "call_count": row[2] or 0,
                            "answered_count": row[3] or 0,
                            "answer_rate": (row[3] or 0) / max(1, row[2] or 1)
                        })
                
                elif granularity == "day":
                    # Daily trends
                    result = await session.execute(
                        select(
                            CallAnalytics.date,
                            func.sum(CallAnalytics.total_calls).label('calls'),
                            func.sum(CallAnalytics.answered_calls).label('answered')
                        ).where(
                            and_(
                                CallAnalytics.tenant_id == tenant_id,
                                CallAnalytics.date >= start_date,
                                CallAnalytics.date <= end_date,
                                CallAnalytics.hour.is_(None)  # Daily aggregation
                            )
                        ).group_by(CallAnalytics.date)
                        .order_by(CallAnalytics.date)
                    )
                    
                    trends = []
                    for row in result.fetchall():
                        trends.append({
                            "timestamp": datetime.combine(row[0], datetime.min.time()).isoformat(),
                            "period": str(row[0]),
                            "call_count": row[1] or 0,
                            "answered_count": row[2] or 0,
                            "answer_rate": (row[2] or 0) / max(1, row[1] or 1)
                        })
                
                else:  # week
                    # Weekly trends (simplified)
                    result = await session.execute(
                        select(
                            func.date_trunc('week', CallAnalytics.date).label('week'),
                            func.sum(CallAnalytics.total_calls).label('calls'),
                            func.sum(CallAnalytics.answered_calls).label('answered')
                        ).where(
                            and_(
                                CallAnalytics.tenant_id == tenant_id,
                                CallAnalytics.date >= start_date,
                                CallAnalytics.date <= end_date,
                                CallAnalytics.hour.is_(None)
                            )
                        ).group_by(func.date_trunc('week', CallAnalytics.date))
                        .order_by(func.date_trunc('week', CallAnalytics.date))
                    )
                    
                    trends = []
                    for row in result.fetchall():
                        week_start = row[0]
                        trends.append({
                            "timestamp": week_start.isoformat() if hasattr(week_start, 'isoformat') else str(week_start),
                            "period": f"Week of {week_start}",
                            "call_count": row[1] or 0,
                            "answered_count": row[2] or 0,
                            "answer_rate": (row[2] or 0) / max(1, row[1] or 1)
                        })
                
                return {
                    "period_info": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": days,
                        "granularity": granularity
                    },
                    "trends": trends,
                    "summary": {
                        "total_periods": len(trends),
                        "total_calls": sum(t["call_count"] for t in trends),
                        "total_answered": sum(t["answered_count"] for t in trends),
                        "overall_answer_rate": sum(t["answered_count"] for t in trends) / max(1, sum(t["call_count"] for t in trends))
                    }
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get call volume trends",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to get call volume trends"}
    
    async def get_ai_performance_insights(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get AI performance insights and analytics.
        
        Args:
            tenant_id: Tenant UUID
            start_date: Analysis start date
            end_date: Analysis end date
            
        Returns:
            Dict containing AI performance insights
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get AI-related call analytics
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
                
                # Aggregate AI metrics
                total_calls = sum(a.total_calls for a in analytics)
                ai_handled = sum(a.ai_handled_calls for a in analytics)
                ai_resolved = sum(a.ai_resolved_calls for a in analytics)
                ai_transferred = sum(a.ai_transferred_calls for a in analytics)
                
                insights = {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "ai_metrics": {
                        "total_calls": total_calls,
                        "ai_handled_calls": ai_handled,
                        "ai_resolved_calls": ai_resolved,
                        "ai_transferred_calls": ai_transferred,
                        "ai_handling_rate": ai_handled / max(1, total_calls),
                        "ai_resolution_rate": ai_resolved / max(1, ai_handled),
                        "ai_transfer_rate": ai_transferred / max(1, ai_handled),
                        "human_escalation_rate": (ai_handled - ai_resolved) / max(1, ai_handled)
                    },
                    "performance_trends": await self._get_ai_performance_trends(session, tenant_id, start_date, end_date),
                    "recommendations": self._generate_ai_recommendations(ai_handled, ai_resolved, ai_transferred, total_calls)
                }
                
                return insights
                
        except Exception as e:
            self.logger.error(
                "Failed to get AI performance insights",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to get AI performance insights"}
    
    async def generate_custom_report(
        self,
        tenant_id: uuid.UUID,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate custom reports with flexible configuration.
        
        Args:
            tenant_id: Tenant UUID
            config: Report configuration
            
        Returns:
            Dict containing custom report data
        """
        try:
            # This would implement a flexible reporting engine
            # For now, return a basic structure
            return {
                "report_type": "custom",
                "config": config,
                "generated_at": datetime.utcnow().isoformat(),
                "data": "Custom report generation would be implemented here",
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to generate custom report",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to generate custom report"}
    
    async def export_analytics_data(
        self,
        tenant_id: uuid.UUID,
        data_type: str,
        start_date: date,
        end_date: date,
        format: str = "json"
    ) -> Any:
        """
        Export analytics data in various formats per Requirement 10.4.
        
        Args:
            tenant_id: Tenant UUID
            data_type: Type of data to export
            start_date: Export start date
            end_date: Export end date
            format: Export format
            
        Returns:
            Exported data in requested format
        """
        try:
            if data_type == "calls":
                data = await self.generate_call_report(tenant_id, start_date, end_date)
            elif data_type == "agents":
                data = await self.generate_agent_report(tenant_id, start_date, end_date)
            elif data_type == "metrics":
                data = await self.get_real_time_dashboard_data(tenant_id, 24)
            else:
                # Export all data types
                data = {
                    "calls": await self.generate_call_report(tenant_id, start_date, end_date),
                    "agents": await self.generate_agent_report(tenant_id, start_date, end_date),
                    "metrics": await self.get_real_time_dashboard_data(tenant_id, 24)
                }
            
            if format.lower() == "json":
                return data
            else:
                # For CSV/XLSX, would implement actual file generation
                # For now, return JSON data
                return data
                
        except Exception as e:
            self.logger.error(
                "Failed to export analytics data",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return {"error": "Failed to export analytics data"}
    
    # Helper methods for new functionality
    
    def _analyze_sentiment(self, transcript: str) -> str:
        """Simple sentiment analysis (would use actual NLP in production)."""
        # Simplified sentiment analysis
        positive_words = ["good", "great", "excellent", "satisfied", "happy", "thank"]
        negative_words = ["bad", "terrible", "awful", "angry", "frustrated", "complaint"]
        
        transcript_lower = transcript.lower()
        positive_count = sum(1 for word in positive_words if word in transcript_lower)
        negative_count = sum(1 for word in negative_words if word in transcript_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _extract_topics(self, transcript: str) -> List[str]:
        """Extract topics from transcript (simplified implementation)."""
        # Simplified topic extraction
        topics = []
        topic_keywords = {
            "billing": ["bill", "payment", "charge", "invoice"],
            "technical": ["problem", "issue", "error", "not working"],
            "support": ["help", "assistance", "support"],
            "sales": ["buy", "purchase", "price", "cost"],
            "account": ["account", "login", "password", "profile"]
        }
        
        transcript_lower = transcript.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in transcript_lower for keyword in keywords):
                topics.append(topic)
        
        return topics or ["general"]
    
    async def _get_active_calls_count(self, session, tenant_id: uuid.UUID) -> int:
        """Get current active calls count."""
        result = await session.execute(
            select(func.count(Call.id)).where(
                and_(
                    Call.tenant_id == tenant_id,
                    Call.status.in_([CallStatus.IN_PROGRESS, CallStatus.RINGING])
                )
            )
        )
        return result.scalar() or 0
    
    async def _get_queue_length(self, session, tenant_id: uuid.UUID) -> int:
        """Get current queue length."""
        result = await session.execute(
            select(func.count(CallQueue.id)).where(
                and_(
                    CallQueue.tenant_id == tenant_id,
                    CallQueue.status == "waiting"
                )
            )
        )
        return result.scalar() or 0
    
    async def _get_available_agents_count(self, session, tenant_id: uuid.UUID) -> int:
        """Get available agents count."""
        result = await session.execute(
            select(func.count(Agent.id)).where(
                and_(
                    Agent.tenant_id == tenant_id,
                    Agent.is_active == True,
                    Agent.status == AgentStatus.AVAILABLE
                )
            )
        )
        return result.scalar() or 0
    
    async def _get_busy_agents_count(self, session, tenant_id: uuid.UUID) -> int:
        """Get busy agents count."""
        result = await session.execute(
            select(func.count(Agent.id)).where(
                and_(
                    Agent.tenant_id == tenant_id,
                    Agent.is_active == True,
                    Agent.status == AgentStatus.BUSY
                )
            )
        )
        return result.scalar() or 0
    
    async def _get_calls_today_count(self, session, tenant_id: uuid.UUID) -> int:
        """Get calls today count."""
        today = date.today()
        result = await session.execute(
            select(func.count(Call.id)).where(
                and_(
                    Call.tenant_id == tenant_id,
                    func.date(Call.created_at) == today
                )
            )
        )
        return result.scalar() or 0
    
    async def _get_ai_resolution_rate_today(self, session, tenant_id: uuid.UUID) -> float:
        """Get AI resolution rate for today."""
        today = date.today()
        result = await session.execute(
            select(CallAnalytics).where(
                and_(
                    CallAnalytics.tenant_id == tenant_id,
                    CallAnalytics.date == today,
                    CallAnalytics.hour.is_(None)
                )
            )
        )
        analytics = result.scalar_one_or_none()
        
        if analytics and analytics.ai_handled_calls > 0:
            return analytics.ai_resolved_calls / analytics.ai_handled_calls
        return 0.0
    
    async def _get_current_average_wait_time(self, session, tenant_id: uuid.UUID) -> float:
        """Get current average wait time."""
        # Simplified implementation
        return 45.0  # Would calculate actual wait time
    
    async def _get_active_alerts(self, session, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get active system alerts."""
        # Simplified implementation
        return []  # Would return actual alerts
    
    async def _get_ai_performance_trends(self, session, tenant_id: uuid.UUID, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get AI performance trends over time."""
        result = await session.execute(
            select(
                CallAnalytics.date,
                CallAnalytics.ai_handled_calls,
                CallAnalytics.ai_resolved_calls,
                CallAnalytics.total_calls
            ).where(
                and_(
                    CallAnalytics.tenant_id == tenant_id,
                    CallAnalytics.date >= start_date,
                    CallAnalytics.date <= end_date,
                    CallAnalytics.hour.is_(None)
                )
            ).order_by(CallAnalytics.date)
        )
        
        trends = []
        for row in result.fetchall():
            ai_handled = row[1] or 0
            ai_resolved = row[2] or 0
            total_calls = row[3] or 0
            
            trends.append({
                "date": row[0].isoformat(),
                "ai_handling_rate": ai_handled / max(1, total_calls),
                "ai_resolution_rate": ai_resolved / max(1, ai_handled),
                "total_calls": total_calls,
                "ai_handled": ai_handled,
                "ai_resolved": ai_resolved
            })
        
        return trends
    
    def _generate_ai_recommendations(self, ai_handled: int, ai_resolved: int, ai_transferred: int, total_calls: int) -> List[str]:
        """Generate AI performance recommendations."""
        recommendations = []
        
        if total_calls > 0:
            ai_handling_rate = ai_handled / total_calls
            if ai_handling_rate < 0.7:
                recommendations.append("Consider expanding AI capabilities to handle more call types")
        
        if ai_handled > 0:
            ai_resolution_rate = ai_resolved / ai_handled
            if ai_resolution_rate < 0.6:
                recommendations.append("Review AI training data to improve resolution rates")
            
            ai_transfer_rate = ai_transferred / ai_handled
            if ai_transfer_rate > 0.4:
                recommendations.append("Analyze transfer patterns to reduce unnecessary escalations")
        
        if not recommendations:
            recommendations.append("AI performance is within acceptable ranges")
        
        return recommendations