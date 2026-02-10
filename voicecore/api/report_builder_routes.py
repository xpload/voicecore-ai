"""
Custom Report Builder API routes for VoiceCore AI 2.0.

Provides drag-and-drop report builder, custom query builder,
scheduled reports, and advanced analytics capabilities.

Implements Requirements 3.3, 3.6: Advanced analytics and custom report builder
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field

from voicecore.services.report_builder_service import ReportBuilderService
from voicecore.middleware import get_current_tenant_id
from voicecore.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/reports", tags=["Report Builder"])


# Pydantic models
class ReportColumn(BaseModel):
    """Report column configuration."""
    field: str
    label: str
    type: str  # "string", "number", "date", "boolean"
    aggregation: Optional[str] = None  # "sum", "avg", "count", "min", "max"
    format: Optional[str] = None


class ReportFilter(BaseModel):
    """Report filter configuration."""
    field: str
    operator: str  # "equals", "not_equals", "contains", "greater_than", "less_than", "between"
    value: Any
    value2: Optional[Any] = None  # For "between" operator


class ReportSort(BaseModel):
    """Report sort configuration."""
    field: str
    direction: str  # "asc", "desc"


class ReportConfig(BaseModel):
    """Report configuration model."""
    report_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    data_source: str  # "calls", "agents", "analytics", "crm"
    columns: List[ReportColumn]
    filters: List[ReportFilter] = []
    sorts: List[ReportSort] = []
    group_by: Optional[List[str]] = None
    limit: Optional[int] = None


class ScheduledReport(BaseModel):
    """Scheduled report configuration."""
    schedule_id: Optional[str] = None
    report_id: str
    schedule_type: str  # "daily", "weekly", "monthly"
    schedule_time: str  # "HH:MM" format
    recipients: List[str]  # Email addresses
    format: str = "pdf"  # "pdf", "excel", "csv"
    is_active: bool = True


@router.post("/create")
async def create_report(
    report_config: ReportConfig,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Create a new custom report configuration.
    
    Allows users to build custom reports with drag-and-drop
    column selection, filters, and aggregations.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        report = await report_service.create_report(
            tenant_id=tenant_id,
            config=report_config.dict()
        )
        
        logger.info(
            "Custom report created",
            tenant_id=str(tenant_id),
            report_id=report["report_id"],
            report_name=report_config.name
        )
        
        return {
            "status": "success",
            "report": report,
            "message": "Report created successfully"
        }
        
    except Exception as e:
        logger.error("Failed to create report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/list")
async def list_reports(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get list of all saved reports for the tenant.
    
    Returns all custom report configurations created by the tenant.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        reports = await report_service.list_reports(tenant_id=tenant_id)
        
        return {
            "reports": reports,
            "count": len(reports)
        }
        
    except Exception as e:
        logger.error("Failed to list reports", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get specific report configuration by ID.
    
    Returns the configuration for a specific custom report.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        report = await report_service.get_report(
            tenant_id=tenant_id,
            report_id=report_id
        )
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/{report_id}/execute")
async def execute_report(
    report_id: str,
    start_date: Optional[date] = Query(None, description="Start date for report data"),
    end_date: Optional[date] = Query(None, description="End date for report data"),
    format: str = Query("json", description="Output format: json, csv, excel, pdf"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Execute a report and return the results.
    
    Runs the report query and returns data in the specified format.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        result = await report_service.execute_report(
            tenant_id=tenant_id,
            report_id=report_id,
            start_date=start_date,
            end_date=end_date,
            output_format=format
        )
        
        if format in ["csv", "excel", "pdf"]:
            # Return file download
            from fastapi.responses import StreamingResponse
            import io
            
            media_types = {
                "csv": "text/csv",
                "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "pdf": "application/pdf"
            }
            
            response = StreamingResponse(
                io.BytesIO(result["data"]),
                media_type=media_types[format],
                headers={
                    "Content-Disposition": f"attachment; filename=report_{report_id}_{start_date}_{end_date}.{format}"
                }
            )
            return response
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to execute report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/{report_id}")
async def update_report(
    report_id: str,
    report_config: ReportConfig,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Update an existing report configuration.
    
    Allows modification of report columns, filters, and settings.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        updated_report = await report_service.update_report(
            tenant_id=tenant_id,
            report_id=report_id,
            config=report_config.dict()
        )
        
        if not updated_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        logger.info(
            "Report updated",
            tenant_id=str(tenant_id),
            report_id=report_id
        )
        
        return {
            "status": "success",
            "report": updated_report,
            "message": "Report updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Delete a report configuration.
    
    Removes a custom report and all associated schedules.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        success = await report_service.delete_report(
            tenant_id=tenant_id,
            report_id=report_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        logger.info(
            "Report deleted",
            tenant_id=str(tenant_id),
            report_id=report_id
        )
        
        return {"status": "success", "message": "Report deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/schedule")
async def schedule_report(
    schedule_config: ScheduledReport,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Schedule automatic report generation and delivery.
    
    Creates a scheduled job to generate and email reports automatically.
    
    **Validates: Requirements 3.6**
    """
    try:
        report_service = ReportBuilderService()
        
        schedule = await report_service.schedule_report(
            tenant_id=tenant_id,
            config=schedule_config.dict()
        )
        
        logger.info(
            "Report scheduled",
            tenant_id=str(tenant_id),
            schedule_id=schedule["schedule_id"],
            report_id=schedule_config.report_id
        )
        
        return {
            "status": "success",
            "schedule": schedule,
            "message": "Report scheduled successfully"
        }
        
    except Exception as e:
        logger.error("Failed to schedule report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/schedules/list")
async def list_scheduled_reports(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get list of all scheduled reports.
    
    Returns all scheduled report configurations for the tenant.
    
    **Validates: Requirements 3.6**
    """
    try:
        report_service = ReportBuilderService()
        
        schedules = await report_service.list_scheduled_reports(tenant_id=tenant_id)
        
        return {
            "schedules": schedules,
            "count": len(schedules)
        }
        
    except Exception as e:
        logger.error("Failed to list scheduled reports", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/schedule/{schedule_id}")
async def delete_scheduled_report(
    schedule_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Delete a scheduled report.
    
    Removes automatic report generation schedule.
    
    **Validates: Requirements 3.6**
    """
    try:
        report_service = ReportBuilderService()
        
        success = await report_service.delete_scheduled_report(
            tenant_id=tenant_id,
            schedule_id=schedule_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled report not found"
            )
        
        logger.info(
            "Scheduled report deleted",
            tenant_id=str(tenant_id),
            schedule_id=schedule_id
        )
        
        return {"status": "success", "message": "Scheduled report deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete scheduled report", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/templates")
async def get_report_templates(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Get available report templates.
    
    Returns pre-built report templates for common use cases.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        templates = await report_service.get_report_templates()
        
        return {
            "templates": templates,
            "count": len(templates)
        }
        
    except Exception as e:
        logger.error("Failed to get report templates", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/query/custom")
async def execute_custom_query(
    query_config: Dict[str, Any],
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    """
    Execute a custom query for advanced users.
    
    Allows advanced users to build custom queries with complex logic.
    
    **Validates: Requirements 3.3**
    """
    try:
        report_service = ReportBuilderService()
        
        result = await report_service.execute_custom_query(
            tenant_id=tenant_id,
            query_config=query_config
        )
        
        return result
        
    except Exception as e:
        logger.error("Failed to execute custom query", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/health")
async def report_builder_health_check():
    """Health check endpoint for report builder service."""
    try:
        return {
            "status": "healthy",
            "service": "report-builder",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error("Report builder health check failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unavailable")
