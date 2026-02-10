"""
Custom Report Builder Service for VoiceCore AI 2.0.

Provides drag-and-drop report builder, custom query builder,
scheduled reports, and advanced analytics capabilities.

Implements Requirements 3.3, 3.6: Advanced analytics and custom report builder
"""

import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func, or_, text
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    CallAnalytics, AgentMetrics, SystemMetrics,
    Call, Agent, Department
)
from voicecore.services.cache_service import CacheService
from voicecore.logging import get_logger


logger = get_logger(__name__)


class ReportBuilderService:
    """
    Custom Report Builder Service.
    
    Provides comprehensive report building capabilities including
    drag-and-drop interface, custom queries, and scheduled reports.
    """
    
    def __init__(self):
        self.logger = logger
        self.cache_service = CacheService()
        self._reports = {}  # In-memory storage for demo
        self._schedules = {}  # In-memory storage for demo
    
    async def create_report(
        self,
        tenant_id: uuid.UUID,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new custom report configuration."""
        try:
            report_id = config.get("report_id") or str(uuid.uuid4())
            
            report_data = {
                "report_id": report_id,
                "tenant_id": str(tenant_id),
                "name": config["name"],
                "description": config.get("description"),
                "data_source": config["data_source"],
                "columns": config["columns"],
                "filters": config.get("filters", []),
                "sorts": config.get("sorts", []),
                "group_by": config.get("group_by"),
                "limit": config.get("limit"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Store in cache and in-memory
            cache_key = f"report:{tenant_id}:{report_id}"
            await self.cache_service.set(
                cache_key,
                json.dumps(report_data),
                ttl=86400 * 30  # 30 days
            )
            
            self._reports[report_id] = report_data
            
            self.logger.info(
                "Report created",
                tenant_id=str(tenant_id),
                report_id=report_id
            )
            
            return report_data
            
        except Exception as e:
            self.logger.error(
                "Failed to create report",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise

    async def list_reports(
        self,
        tenant_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get list of all saved reports for the tenant."""
        try:
            reports = [
                report for report in self._reports.values()
                if report["tenant_id"] == str(tenant_id)
            ]
            return reports
            
        except Exception as e:
            self.logger.error(
                "Failed to list reports",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_report(
        self,
        tenant_id: uuid.UUID,
        report_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific report configuration by ID."""
        try:
            # Check cache first
            cache_key = f"report:{tenant_id}:{report_id}"
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            # Check in-memory storage
            report = self._reports.get(report_id)
            if report and report["tenant_id"] == str(tenant_id):
                return report
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get report",
                tenant_id=str(tenant_id),
                report_id=report_id,
                error=str(e)
            )
            raise
    
    async def execute_report(
        self,
        tenant_id: uuid.UUID,
        report_id: str,
        start_date: date,
        end_date: date,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """Execute a report and return the results."""
        try:
            # Get report configuration
            report = await self.get_report(tenant_id, report_id)
            if not report:
                raise ValueError("Report not found")
            
            # Execute query based on data source
            data_source = report["data_source"]
            
            if data_source == "calls":
                data = await self._query_calls_data(
                    tenant_id, report, start_date, end_date
                )
            elif data_source == "agents":
                data = await self._query_agents_data(
                    tenant_id, report, start_date, end_date
                )
            elif data_source == "analytics":
                data = await self._query_analytics_data(
                    tenant_id, report, start_date, end_date
                )
            else:
                raise ValueError(f"Unsupported data source: {data_source}")
            
            # Format output
            if output_format == "json":
                return {
                    "report_id": report_id,
                    "report_name": report["name"],
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "data": data,
                    "row_count": len(data),
                    "generated_at": datetime.utcnow().isoformat()
                }
            elif output_format == "csv":
                return {"data": self._format_as_csv(data, report["columns"])}
            elif output_format == "excel":
                return {"data": self._format_as_excel(data, report["columns"])}
            elif output_format == "pdf":
                return {"data": self._format_as_pdf(data, report)}
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
        except Exception as e:
            self.logger.error(
                "Failed to execute report",
                tenant_id=str(tenant_id),
                report_id=report_id,
                error=str(e)
            )
            raise
    
    async def update_report(
        self,
        tenant_id: uuid.UUID,
        report_id: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing report configuration."""
        try:
            # Check if report exists
            existing_report = await self.get_report(tenant_id, report_id)
            if not existing_report:
                return None
            
            # Update report data
            report_data = {
                **existing_report,
                "name": config.get("name", existing_report["name"]),
                "description": config.get("description", existing_report["description"]),
                "data_source": config.get("data_source", existing_report["data_source"]),
                "columns": config.get("columns", existing_report["columns"]),
                "filters": config.get("filters", existing_report["filters"]),
                "sorts": config.get("sorts", existing_report["sorts"]),
                "group_by": config.get("group_by", existing_report["group_by"]),
                "limit": config.get("limit", existing_report["limit"]),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Update cache and in-memory storage
            cache_key = f"report:{tenant_id}:{report_id}"
            await self.cache_service.set(
                cache_key,
                json.dumps(report_data),
                ttl=86400 * 30
            )
            
            self._reports[report_id] = report_data
            
            self.logger.info(
                "Report updated",
                tenant_id=str(tenant_id),
                report_id=report_id
            )
            
            return report_data
            
        except Exception as e:
            self.logger.error(
                "Failed to update report",
                tenant_id=str(tenant_id),
                report_id=report_id,
                error=str(e)
            )
            raise
    
    async def delete_report(
        self,
        tenant_id: uuid.UUID,
        report_id: str
    ) -> bool:
        """Delete a report configuration."""
        try:
            # Remove from cache
            cache_key = f"report:{tenant_id}:{report_id}"
            await self.cache_service.delete(cache_key)
            
            # Remove from in-memory storage
            if report_id in self._reports:
                report = self._reports[report_id]
                if report["tenant_id"] == str(tenant_id):
                    del self._reports[report_id]
                    
                    # Also delete associated schedules
                    schedules_to_delete = [
                        sid for sid, schedule in self._schedules.items()
                        if schedule["report_id"] == report_id and schedule["tenant_id"] == str(tenant_id)
                    ]
                    for sid in schedules_to_delete:
                        del self._schedules[sid]
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to delete report",
                tenant_id=str(tenant_id),
                report_id=report_id,
                error=str(e)
            )
            raise

    async def schedule_report(
        self,
        tenant_id: uuid.UUID,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Schedule automatic report generation and delivery."""
        try:
            schedule_id = config.get("schedule_id") or str(uuid.uuid4())
            
            schedule_data = {
                "schedule_id": schedule_id,
                "tenant_id": str(tenant_id),
                "report_id": config["report_id"],
                "schedule_type": config["schedule_type"],
                "schedule_time": config["schedule_time"],
                "recipients": config["recipients"],
                "format": config.get("format", "pdf"),
                "is_active": config.get("is_active", True),
                "created_at": datetime.utcnow().isoformat(),
                "last_run": None,
                "next_run": self._calculate_next_run(
                    config["schedule_type"],
                    config["schedule_time"]
                ).isoformat()
            }
            
            # Store in cache and in-memory
            cache_key = f"schedule:{tenant_id}:{schedule_id}"
            await self.cache_service.set(
                cache_key,
                json.dumps(schedule_data),
                ttl=86400 * 30
            )
            
            self._schedules[schedule_id] = schedule_data
            
            self.logger.info(
                "Report scheduled",
                tenant_id=str(tenant_id),
                schedule_id=schedule_id
            )
            
            return schedule_data
            
        except Exception as e:
            self.logger.error(
                "Failed to schedule report",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def list_scheduled_reports(
        self,
        tenant_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get list of all scheduled reports."""
        try:
            schedules = [
                schedule for schedule in self._schedules.values()
                if schedule["tenant_id"] == str(tenant_id)
            ]
            return schedules
            
        except Exception as e:
            self.logger.error(
                "Failed to list scheduled reports",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def delete_scheduled_report(
        self,
        tenant_id: uuid.UUID,
        schedule_id: str
    ) -> bool:
        """Delete a scheduled report."""
        try:
            # Remove from cache
            cache_key = f"schedule:{tenant_id}:{schedule_id}"
            await self.cache_service.delete(cache_key)
            
            # Remove from in-memory storage
            if schedule_id in self._schedules:
                schedule = self._schedules[schedule_id]
                if schedule["tenant_id"] == str(tenant_id):
                    del self._schedules[schedule_id]
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to delete scheduled report",
                tenant_id=str(tenant_id),
                schedule_id=schedule_id,
                error=str(e)
            )
            raise
    
    async def get_report_templates(self) -> List[Dict[str, Any]]:
        """Get available report templates."""
        return [
            {
                "template_id": "call_summary",
                "name": "Call Summary Report",
                "description": "Comprehensive call statistics and metrics",
                "data_source": "calls",
                "columns": [
                    {"field": "date", "label": "Date", "type": "date"},
                    {"field": "total_calls", "label": "Total Calls", "type": "number"},
                    {"field": "answered_calls", "label": "Answered", "type": "number"},
                    {"field": "missed_calls", "label": "Missed", "type": "number"},
                    {"field": "answer_rate", "label": "Answer Rate", "type": "number", "format": "percentage"}
                ]
            },
            {
                "template_id": "agent_performance",
                "name": "Agent Performance Report",
                "description": "Agent productivity and quality metrics",
                "data_source": "agents",
                "columns": [
                    {"field": "agent_name", "label": "Agent", "type": "string"},
                    {"field": "calls_handled", "label": "Calls Handled", "type": "number"},
                    {"field": "avg_call_duration", "label": "Avg Duration", "type": "number", "format": "duration"},
                    {"field": "satisfaction_score", "label": "Satisfaction", "type": "number", "format": "rating"}
                ]
            },
            {
                "template_id": "ai_performance",
                "name": "AI Performance Report",
                "description": "AI handling and resolution metrics",
                "data_source": "analytics",
                "columns": [
                    {"field": "date", "label": "Date", "type": "date"},
                    {"field": "ai_handled", "label": "AI Handled", "type": "number"},
                    {"field": "ai_resolved", "label": "AI Resolved", "type": "number"},
                    {"field": "resolution_rate", "label": "Resolution Rate", "type": "number", "format": "percentage"}
                ]
            },
            {
                "template_id": "revenue_analysis",
                "name": "Revenue Analysis Report",
                "description": "Revenue and cost analysis",
                "data_source": "analytics",
                "columns": [
                    {"field": "date", "label": "Date", "type": "date"},
                    {"field": "total_revenue", "label": "Revenue", "type": "number", "format": "currency"},
                    {"field": "total_calls", "label": "Calls", "type": "number"},
                    {"field": "revenue_per_call", "label": "Revenue/Call", "type": "number", "format": "currency"}
                ]
            }
        ]
    
    async def execute_custom_query(
        self,
        tenant_id: uuid.UUID,
        query_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a custom query for advanced users."""
        try:
            # This is a simplified implementation
            # In production, this would have more sophisticated query building
            
            data_source = query_config.get("data_source", "calls")
            start_date = date.fromisoformat(query_config.get("start_date", str(date.today() - timedelta(days=30))))
            end_date = date.fromisoformat(query_config.get("end_date", str(date.today())))
            
            # Create temporary report config
            temp_report = {
                "data_source": data_source,
                "columns": query_config.get("columns", []),
                "filters": query_config.get("filters", []),
                "sorts": query_config.get("sorts", []),
                "group_by": query_config.get("group_by"),
                "limit": query_config.get("limit")
            }
            
            # Execute query
            if data_source == "calls":
                data = await self._query_calls_data(tenant_id, temp_report, start_date, end_date)
            elif data_source == "agents":
                data = await self._query_agents_data(tenant_id, temp_report, start_date, end_date)
            elif data_source == "analytics":
                data = await self._query_analytics_data(tenant_id, temp_report, start_date, end_date)
            else:
                raise ValueError(f"Unsupported data source: {data_source}")
            
            return {
                "data": data,
                "row_count": len(data),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to execute custom query",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    # Private helper methods
    
    async def _query_calls_data(
        self,
        tenant_id: uuid.UUID,
        report: Dict[str, Any],
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Query calls data based on report configuration."""
        async with get_db_session() as session:
            await set_tenant_context(session, str(tenant_id))
            
            # Build query
            query = select(Call).where(
                and_(
                    Call.tenant_id == tenant_id,
                    func.date(Call.created_at) >= start_date,
                    func.date(Call.created_at) <= end_date
                )
            )
            
            # Apply filters
            for filter_config in report.get("filters", []):
                query = self._apply_filter(query, Call, filter_config)
            
            # Apply sorts
            for sort_config in report.get("sorts", []):
                query = self._apply_sort(query, Call, sort_config)
            
            # Apply limit
            if report.get("limit"):
                query = query.limit(report["limit"])
            
            result = await session.execute(query)
            calls = result.scalars().all()
            
            # Format data based on columns
            data = []
            for call in calls:
                row = {}
                for col in report["columns"]:
                    field = col["field"]
                    row[field] = getattr(call, field, None)
                data.append(row)
            
            return data
    
    async def _query_agents_data(
        self,
        tenant_id: uuid.UUID,
        report: Dict[str, Any],
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Query agents data based on report configuration."""
        async with get_db_session() as session:
            await set_tenant_context(session, str(tenant_id))
            
            # Get agent metrics
            result = await session.execute(
                select(AgentMetrics).where(
                    and_(
                        AgentMetrics.tenant_id == tenant_id,
                        AgentMetrics.date >= start_date,
                        AgentMetrics.date <= end_date
                    )
                )
            )
            metrics = result.scalars().all()
            
            # Format data
            data = []
            for metric in metrics:
                row = {}
                for col in report["columns"]:
                    field = col["field"]
                    row[field] = getattr(metric, field, None)
                data.append(row)
            
            return data
    
    async def _query_analytics_data(
        self,
        tenant_id: uuid.UUID,
        report: Dict[str, Any],
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Query analytics data based on report configuration."""
        async with get_db_session() as session:
            await set_tenant_context(session, str(tenant_id))
            
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
            
            # Format data
            data = []
            for analytic in analytics:
                row = {}
                for col in report["columns"]:
                    field = col["field"]
                    row[field] = getattr(analytic, field, None)
                data.append(row)
            
            return data
    
    def _apply_filter(self, query, model, filter_config: Dict[str, Any]):
        """Apply filter to query."""
        field = getattr(model, filter_config["field"])
        operator = filter_config["operator"]
        value = filter_config["value"]
        
        if operator == "equals":
            return query.where(field == value)
        elif operator == "not_equals":
            return query.where(field != value)
        elif operator == "contains":
            return query.where(field.contains(value))
        elif operator == "greater_than":
            return query.where(field > value)
        elif operator == "less_than":
            return query.where(field < value)
        elif operator == "between":
            value2 = filter_config.get("value2")
            return query.where(and_(field >= value, field <= value2))
        
        return query
    
    def _apply_sort(self, query, model, sort_config: Dict[str, Any]):
        """Apply sort to query."""
        field = getattr(model, sort_config["field"])
        direction = sort_config["direction"]
        
        if direction == "desc":
            return query.order_by(field.desc())
        else:
            return query.order_by(field.asc())
    
    def _calculate_next_run(self, schedule_type: str, schedule_time: str) -> datetime:
        """Calculate next run time for scheduled report."""
        now = datetime.utcnow()
        hour, minute = map(int, schedule_time.split(":"))
        
        if schedule_type == "daily":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        elif schedule_type == "weekly":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = 7 - now.weekday()
            next_run += timedelta(days=days_ahead)
        elif schedule_type == "monthly":
            next_run = now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                # Next month
                if now.month == 12:
                    next_run = next_run.replace(year=now.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=now.month + 1)
        else:
            next_run = now + timedelta(days=1)
        
        return next_run
    
    def _format_as_csv(self, data: List[Dict[str, Any]], columns: List[Dict[str, Any]]) -> bytes:
        """Format data as CSV."""
        import csv
        import io
        
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=[col["field"] for col in columns])
            writer.writeheader()
            writer.writerows(data)
        
        return output.getvalue().encode()
    
    def _format_as_excel(self, data: List[Dict[str, Any]], columns: List[Dict[str, Any]]) -> bytes:
        """Format data as Excel."""
        # Simplified implementation - would use openpyxl in production
        return self._format_as_csv(data, columns)
    
    def _format_as_pdf(self, data: List[Dict[str, Any]], report: Dict[str, Any]) -> bytes:
        """Format data as PDF."""
        # Simplified implementation - would use reportlab in production
        return self._format_as_csv(data, report["columns"])
