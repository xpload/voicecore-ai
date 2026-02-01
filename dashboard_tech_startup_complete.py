"""
VoiceCore AI - Tech Startup Dashboard
GitHub-Inspired Dark Professional Interface

Complete enterprise dashboard implementation with all VoiceCore AI functionalities.
Designed with GitHub's dark theme aesthetic for modern tech companies.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    Tenant, Agent, Call, Department, CallQueue, VIPCaller,
    AgentStatus, CallStatus, CallDirection, AgentMetrics, CallAnalytics,
    KnowledgeBase, SpamRule
)
from voicecore.services.agent_service import AgentService
from voicecore.services.call_routing_service import CallRoutingService
from voicecore.services.analytics_service import AnalyticsService
from voicecore.services.admin_service import AdminService
from voicecore.services.vip_service import VIPService
from voicecore.services.ai_training_service import AITrainingService
from voicecore.services.spam_detection_service import SpamDetectionService
from voicecore.services.websocket_service import websocket_manager
from voicecore.logging import get_logger

logger = get_logger(__name__)

# Initialize services
agent_service = AgentService()
call_routing_service = CallRoutingService()
analytics_service = AnalyticsService()
admin_service = AdminService()
vip_service = VIPService()
ai_training_service = AITrainingService()
spam_detection_service = SpamDetectionService()

templates = Jinja2Templates(directory="templates")

async def get_current_tenant_id() -> uuid.UUID:
    """Get current tenant ID - in production this would come from authentication."""
    # For demo purposes, return first tenant
    async with get_db_session() as session:
        result = await session.execute(select(Tenant.id).limit(1))
        tenant_id = result.scalar_one_or_none()
        if not tenant_id:
            raise HTTPException(status_code=404, detail="No tenant found")
        return tenant_id
def create_tech_startup_dashboard_app() -> FastAPI:
    """Create the Tech Startup dashboard FastAPI application."""
    
    app = FastAPI(
        title="VoiceCore AI - Tech Startup Dashboard",
        description="GitHub-Inspired Dark Professional Interface for Virtual Receptionist System",
        version="3.0.0"
    )
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def tech_startup_dashboard(request: Request):
        """Main Tech Startup dashboard interface."""
        return HTMLResponse(content=TECH_STARTUP_DASHBOARD_HTML, status_code=200)
    
    @app.websocket("/ws/dashboard")
    async def dashboard_websocket(websocket: WebSocket):
        """WebSocket endpoint for real-time dashboard updates."""
        await websocket.accept()
        try:
            tenant_id = await get_current_tenant_id()
            
            # Send initial data
            dashboard_data = await get_comprehensive_dashboard_data(tenant_id)
            await websocket.send_json({
                "type": "initial_data",
                "data": dashboard_data
            })
            
            # Keep connection alive and send periodic updates
            while True:
                await asyncio.sleep(3)  # Update every 3 seconds for real-time feel
                
                # Get real-time updates
                real_time_data = await get_real_time_updates(tenant_id)
                await websocket.send_json({
                    "type": "real_time_update",
                    "data": real_time_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except WebSocketDisconnect:
            logger.info("Dashboard WebSocket disconnected")
        except Exception as e:
            logger.error(f"Dashboard WebSocket error: {str(e)}")
            await websocket.close()
    
    @app.get("/api/dashboard/overview")
    async def get_dashboard_overview(tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
        """Get comprehensive dashboard overview data."""
        try:
            data = await get_comprehensive_dashboard_data(tenant_id)
            return JSONResponse(content=data)
        except Exception as e:
            logger.error(f"Failed to get dashboard overview: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")
    
    @app.get("/api/agents/management")
    async def get_agent_management_data(tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
        """Get comprehensive agent management data."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get all agents with departments
                agents_result = await session.execute(
                    select(Agent)
                    .options(selectinload(Agent.department))
                    .where(Agent.tenant_id == tenant_id)
                    .order_by(Agent.name)
                )
                agents = agents_result.scalars().all()
                
                # Get departments
                departments_result = await session.execute(
                    select(Department)
                    .where(and_(Department.tenant_id == tenant_id, Department.is_active == True))
                    .order_by(Department.name)
                )
                departments = departments_result.scalars().all()
                
                # Get agent metrics for today
                today = datetime.utcnow().date()
                metrics_result = await session.execute(
                    select(AgentMetrics)
                    .where(and_(
                        AgentMetrics.tenant_id == tenant_id,
                        AgentMetrics.date == today
                    ))
                )
                metrics = {m.agent_id: m for m in metrics_result.scalars().all()}
                
                agent_data = []
                for agent in agents:
                    agent_metrics = metrics.get(agent.id)
                    agent_data.append({
                        "id": str(agent.id),
                        "name": agent.name,
                        "extension": agent.extension,
                        "email": agent.email,
                        "department": agent.department.name if agent.department else "Unassigned",
                        "department_id": str(agent.department_id) if agent.department_id else None,
                        "status": agent.status.value,
                        "is_active": agent.is_active,
                        "is_manager": agent.is_manager,
                        "current_calls": agent.current_calls,
                        "max_concurrent_calls": agent.max_concurrent_calls,
                        "skills": agent.skills or [],
                        "languages": agent.languages or ["en"],
                        "last_status_change": agent.last_status_change.isoformat() if agent.last_status_change else None,
                        "metrics": {
                            "calls_handled": agent_metrics.calls_handled if agent_metrics else 0,
                            "total_talk_time": agent_metrics.total_talk_time if agent_metrics else 0,
                            "average_call_duration": agent_metrics.average_call_duration if agent_metrics else 0,
                            "utilization_rate": agent_metrics.utilization_rate if agent_metrics else 0,
                            "customer_satisfaction": agent_metrics.customer_satisfaction_score if agent_metrics else 0
                        }
                    })
                
                department_data = []
                for dept in departments:
                    dept_agents = [a for a in agents if a.department_id == dept.id]
                    available_agents = [a for a in dept_agents if a.status == AgentStatus.AVAILABLE and a.is_active]
                    
                    department_data.append({
                        "id": str(dept.id),
                        "name": dept.name,
                        "code": dept.code,
                        "description": dept.description,
                        "is_default": dept.is_default,
                        "total_agents": len(dept_agents),
                        "available_agents": len(available_agents),
                        "routing_strategy": dept.routing_strategy,
                        "max_queue_size": dept.max_queue_size,
                        "work_schedule": dept.work_schedule or {}
                    })
                
                return {
                    "agents": agent_data,
                    "departments": department_data,
                    "summary": {
                        "total_agents": len(agents),
                        "active_agents": len([a for a in agents if a.is_active]),
                        "available_agents": len([a for a in agents if a.status == AgentStatus.AVAILABLE and a.is_active]),
                        "busy_agents": len([a for a in agents if a.status == AgentStatus.BUSY]),
                        "total_departments": len(departments)
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get agent management data: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve agent data")
    
    @app.get("/api/calls/live")
    async def get_live_calls(tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
        """Get live call monitoring data."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get active calls
                active_calls_result = await session.execute(
                    select(Call)
                    .options(selectinload(Call.agent), selectinload(Call.department))
                    .where(and_(
                        Call.tenant_id == tenant_id,
                        Call.status.in_([CallStatus.RINGING, CallStatus.IN_PROGRESS, CallStatus.QUEUED])
                    ))
                    .order_by(desc(Call.created_at))
                )
                active_calls = active_calls_result.scalars().all()
                
                # Get queue status
                queue_result = await session.execute(
                    select(CallQueue)
                    .where(and_(
                        CallQueue.tenant_id == tenant_id,
                        CallQueue.assigned_agent_id.is_(None)
                    ))
                    .order_by(CallQueue.priority.desc(), CallQueue.queued_at)
                )
                queued_calls = queue_result.scalars().all()
                
                call_data = []
                for call in active_calls:
                    call_data.append({
                        "id": str(call.id),
                        "from_number": call.from_number,
                        "to_number": call.to_number,
                        "status": call.status.value,
                        "direction": call.direction.value,
                        "agent": {
                            "name": call.agent.name,
                            "extension": call.agent.extension
                        } if call.agent else None,
                        "department": call.department.name if call.department else None,
                        "duration": int((datetime.utcnow() - call.created_at).total_seconds()),
                        "created_at": call.created_at.isoformat(),
                        "is_vip": call.metadata.get("is_vip", False) if call.metadata else False,
                        "call_type": call.call_type.value if call.call_type else "voice"
                    })
                
                queue_data = []
                for queue_entry in queued_calls:
                    wait_time = int((datetime.utcnow() - queue_entry.queued_at).total_seconds())
                    queue_data.append({
                        "id": str(queue_entry.id),
                        "call_id": str(queue_entry.call_id),
                        "caller_number": queue_entry.caller_number,
                        "priority": queue_entry.priority,
                        "queue_position": queue_entry.queue_position,
                        "wait_time": wait_time,
                        "estimated_wait_time": queue_entry.estimated_wait_time,
                        "department_id": str(queue_entry.department_id)
                    })
                
                return {
                    "active_calls": call_data,
                    "queued_calls": queue_data,
                    "summary": {
                        "total_active": len(active_calls),
                        "total_queued": len(queued_calls),
                        "average_wait_time": sum(q["wait_time"] for q in queue_data) / len(queue_data) if queue_data else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get live calls: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve call data")
    
    @app.post("/api/agents")
    async def create_agent(
        name: str = Form(...),
        email: str = Form(...),
        extension: str = Form(...),
        department_id: str = Form(None),
        skills: str = Form(""),
        languages: str = Form("en"),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id)
    ):
        """Create a new agent."""
        try:
            skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
            languages_list = [l.strip() for l in languages.split(",") if l.strip()] if languages else ["en"]
            
            success = await agent_service.create_agent(
                tenant_id=tenant_id,
                name=name,
                email=email,
                extension=extension,
                department_id=uuid.UUID(department_id) if department_id else None,
                skills=skills_list,
                languages=languages_list
            )
            
            if success:
                return {"success": True, "message": "Agent created successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create agent")
                
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create agent")
    
    @app.post("/api/agents/{agent_id}/status")
    async def update_agent_status(
        agent_id: uuid.UUID,
        status_data: Dict[str, Any],
        tenant_id: uuid.UUID = Depends(get_current_tenant_id)
    ):
        """Update agent status."""
        try:
            new_status = AgentStatus(status_data["status"])
            success = await agent_service.update_agent_status(
                tenant_id, agent_id, new_status, status_data.get("session_type", "web")
            )
            
            if success:
                return {"success": True, "message": "Agent status updated successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update agent status")
                
        except Exception as e:
            logger.error(f"Failed to update agent status: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update agent status")
    
    @app.post("/api/calls/{call_id}/transfer")
    async def transfer_call(
        call_id: uuid.UUID,
        transfer_data: Dict[str, Any],
        tenant_id: uuid.UUID = Depends(get_current_tenant_id)
    ):
        """Transfer a call to another agent or department."""
        try:
            target_agent_id = transfer_data.get("agent_id")
            target_department_id = transfer_data.get("department_id")
            
            if target_agent_id:
                success = await call_routing_service.transfer_call_to_agent(
                    tenant_id, call_id, uuid.UUID(target_agent_id)
                )
            elif target_department_id:
                success = await call_routing_service.transfer_call_to_department(
                    tenant_id, call_id, uuid.UUID(target_department_id)
                )
            else:
                raise HTTPException(status_code=400, detail="Must specify target agent or department")
            
            if success:
                return {"success": True, "message": "Call transferred successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to transfer call")
                
        except Exception as e:
            logger.error(f"Failed to transfer call: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to transfer call")
    
    @app.get("/api/ai-training/knowledge-base")
    async def get_knowledge_base(tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
        """Get AI knowledge base entries."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(KnowledgeBase)
                    .where(KnowledgeBase.tenant_id == tenant_id)
                    .order_by(KnowledgeBase.priority.desc(), KnowledgeBase.created_at.desc())
                )
                entries = result.scalars().all()
                
                knowledge_data = []
                for entry in entries:
                    knowledge_data.append({
                        "id": str(entry.id),
                        "question": entry.question,
                        "answer": entry.answer,
                        "category": entry.category,
                        "priority": entry.priority,
                        "active": entry.active,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat()
                    })
                
                return {
                    "knowledge_base": knowledge_data,
                    "summary": {
                        "total_entries": len(entries),
                        "active_entries": len([e for e in entries if e.active]),
                        "categories": list(set([e.category for e in entries if e.category]))
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get knowledge base: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve knowledge base")
    
    @app.post("/api/ai-training/knowledge-base")
    async def create_knowledge_entry(
        question: str = Form(...),
        answer: str = Form(...),
        category: str = Form(""),
        priority: int = Form(0),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id)
    ):
        """Create a new knowledge base entry."""
        try:
            success = await ai_training_service.add_knowledge_entry(
                tenant_id=tenant_id,
                question=question,
                answer=answer,
                category=category if category else None,
                priority=priority
            )
            
            if success:
                return {"success": True, "message": "Knowledge entry created successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create knowledge entry")
                
        except Exception as e:
            logger.error(f"Failed to create knowledge entry: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create knowledge entry")
    
    @app.get("/api/spam-detection/rules")
    async def get_spam_rules(tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
        """Get spam detection rules."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(SpamRule)
                    .where(SpamRule.tenant_id == tenant_id)
                    .order_by(SpamRule.weight.desc(), SpamRule.created_at.desc())
                )
                rules = result.scalars().all()
                
                rules_data = []
                for rule in rules:
                    rules_data.append({
                        "id": str(rule.id),
                        "rule_type": rule.rule_type,
                        "rule_value": rule.rule_value,
                        "action": rule.action,
                        "weight": rule.weight,
                        "active": rule.active,
                        "created_at": rule.created_at.isoformat()
                    })
                
                return {
                    "spam_rules": rules_data,
                    "summary": {
                        "total_rules": len(rules),
                        "active_rules": len([r for r in rules if r.active]),
                        "rule_types": list(set([r.rule_type for r in rules]))
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get spam rules: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve spam rules")
    
    @app.post("/api/spam-detection/rules")
    async def create_spam_rule(
        rule_type: str = Form(...),
        rule_value: str = Form(...),
        action: str = Form("block"),
        weight: int = Form(10),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id)
    ):
        """Create a new spam detection rule."""
        try:
            success = await spam_detection_service.add_spam_rule(
                tenant_id=tenant_id,
                rule_type=rule_type,
                rule_value=rule_value,
                action=action,
                weight=weight
            )
            
            if success:
                return {"success": True, "message": "Spam rule created successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create spam rule")
                
        except Exception as e:
            logger.error(f"Failed to create spam rule: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create spam rule")
    
    @app.get("/api/analytics/real-time")
    async def get_real_time_analytics(tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
        """Get real-time analytics data."""
        try:
            data = await analytics_service.get_real_time_dashboard_data(tenant_id, 24)
            return data
        except Exception as e:
            logger.error(f"Failed to get real-time analytics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve analytics")
    
    @app.get("/api/vip/callers")
    async def get_vip_callers(tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
        """Get VIP callers list."""
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(VIPCaller)
                    .where(and_(VIPCaller.tenant_id == tenant_id, VIPCaller.is_active == True))
                    .order_by(VIPCaller.priority.desc(), VIPCaller.created_at.desc())
                )
                vip_callers = result.scalars().all()
                
                vip_data = []
                for vip in vip_callers:
                    vip_data.append({
                        "id": str(vip.id),
                        "phone_number": vip.phone_number,
                        "name": vip.name,
                        "company": vip.company,
                        "priority": vip.priority,
                        "special_instructions": vip.special_instructions,
                        "created_at": vip.created_at.isoformat()
                    })
                
                return {
                    "vip_callers": vip_data,
                    "summary": {
                        "total_vips": len(vip_callers),
                        "high_priority": len([v for v in vip_callers if v.priority >= 8]),
                        "medium_priority": len([v for v in vip_callers if 5 <= v.priority < 8]),
                        "low_priority": len([v for v in vip_callers if v.priority < 5])
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get VIP callers: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve VIP callers")
    
    return app
async def get_comprehensive_dashboard_data(tenant_id: uuid.UUID) -> Dict[str, Any]:
    """Get comprehensive dashboard data for the tech startup interface."""
    try:
        async with get_db_session() as session:
            await set_tenant_context(session, str(tenant_id))
            
            # Get tenant info
            tenant_result = await session.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            
            # Get real-time metrics
            analytics_data = await analytics_service.get_real_time_dashboard_data(tenant_id, 24)
            
            # Get system status
            system_health = await admin_service.perform_system_health_check()
            
            return {
                "tenant": {
                    "id": str(tenant.id),
                    "company_name": tenant.company_name,
                    "domain": tenant.domain,
                    "is_active": tenant.is_active,
                    "created_at": tenant.created_at.isoformat()
                } if tenant else None,
                "analytics": analytics_data,
                "system_health": system_health,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get comprehensive dashboard data: {str(e)}")
        return {"error": "Failed to retrieve dashboard data"}

async def get_real_time_updates(tenant_id: uuid.UUID) -> Dict[str, Any]:
    """Get real-time updates for the dashboard."""
    try:
        async with get_db_session() as session:
            await set_tenant_context(session, str(tenant_id))
            
            # Get current call counts
            active_calls_result = await session.execute(
                select(func.count(Call.id)).where(and_(
                    Call.tenant_id == tenant_id,
                    Call.status.in_([CallStatus.RINGING, CallStatus.IN_PROGRESS])
                ))
            )
            active_calls = active_calls_result.scalar() or 0
            
            # Get agent status counts
            agent_status_result = await session.execute(
                select(
                    Agent.status,
                    func.count(Agent.id)
                ).where(and_(
                    Agent.tenant_id == tenant_id,
                    Agent.is_active == True
                )).group_by(Agent.status)
            )
            
            agent_status_counts = {}
            for status, count in agent_status_result.fetchall():
                agent_status_counts[status.value] = count
            
            # Get queue size
            queue_size_result = await session.execute(
                select(func.count(CallQueue.id)).where(and_(
                    CallQueue.tenant_id == tenant_id,
                    CallQueue.assigned_agent_id.is_(None)
                ))
            )
            queue_size = queue_size_result.scalar() or 0
            
            return {
                "active_calls": active_calls,
                "agent_status": agent_status_counts,
                "queue_size": queue_size,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get real-time updates: {str(e)}")
        return {"error": "Failed to get updates"}

# Tech Startup Dashboard HTML Template
TECH_STARTUP_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoiceCore AI - Tech Startup Dashboard</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #21262d;
            --bg-tertiary: #30363d;
            --border-primary: #30363d;
            --border-secondary: #21262d;
            --text-primary: #f0f6fc;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-blue: #1f6feb;
            --accent-green: #238636;
            --accent-red: #f85149;
            --accent-orange: #fb8500;
            --accent-purple: #a5a5a5;
            --success: #238636;
            --warning: #fb8500;
            --danger: #f85149;
            --info: #1f6feb;
            --sidebar-width: 280px;
            --header-height: 64px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }

        /* Layout Structure */
        .dashboard-container {
            display: flex;
            min-height: 100vh;
        }

        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width);
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-primary);
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            z-index: 1000;
        }

        .sidebar-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-primary);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .logo i {
            font-size: 1.5rem;
            color: var(--accent-blue);
        }

        .enterprise-badge {
            background: var(--accent-green);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }

        .nav-menu {
            padding: 1rem 0;
        }

        .nav-section {
            margin-bottom: 1.5rem;
        }

        .nav-section-title {
            padding: 0 1.5rem 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1.5rem;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s ease;
            cursor: pointer;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
            font-size: 0.875rem;
        }

        .nav-item:hover {
            background-color: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .nav-item.active {
            background-color: var(--bg-tertiary);
            color: var(--accent-blue);
            border-right: 3px solid var(--accent-blue);
        }

        .nav-item i {
            width: 1.25rem;
            text-align: center;
        }

        /* Main Content */
        .main-content {
            flex: 1;
            margin-left: var(--sidebar-width);
            display: flex;
            flex-direction: column;
        }

        /* Header */
        .header {
            height: var(--header-height);
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-primary);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
        }

        .header-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(35, 134, 54, 0.1);
            border: 1px solid var(--accent-green);
            border-radius: 6px;
            font-size: 0.875rem;
            color: var(--accent-green);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Content Area */
        .content {
            flex: 1;
            padding: 2rem;
            overflow-y: auto;
        }

        /* Dashboard Grid */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        /* Cards */
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-primary);
            border-radius: 8px;
            overflow: hidden;
        }

        .card-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-primary);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .card-content {
            padding: 1.5rem;
        }

        /* Metrics Cards */
        .metric-card {
            text-align: center;
            padding: 2rem 1.5rem;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .metric-value.blue { color: var(--accent-blue); }
        .metric-value.green { color: var(--accent-green); }
        .metric-value.red { color: var(--accent-red); }
        .metric-value.orange { color: var(--accent-orange); }
        .metric-value.purple { color: var(--accent-purple); }

        .metric-label {
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .metric-change {
            font-size: 0.75rem;
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.25rem;
        }

        .metric-change.positive { color: var(--accent-green); }
        .metric-change.negative { color: var(--accent-red); }

        /* Tables */
        .table-container {
            overflow-x: auto;
        }

        .table {
            width: 100%;
            border-collapse: collapse;
        }

        .table th,
        .table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-primary);
        }

        .table th {
            background: var(--bg-tertiary);
            font-weight: 600;
            color: var(--text-primary);
            font-size: 0.875rem;
        }

        .table td {
            color: var(--text-secondary);
        }

        .table tbody tr:hover {
            background: var(--bg-tertiary);
        }

        /* Status Badges */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .status-badge.available {
            background: rgba(35, 134, 54, 0.1);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
        }

        .status-badge.busy {
            background: rgba(251, 133, 0, 0.1);
            color: var(--accent-orange);
            border: 1px solid var(--accent-orange);
        }

        .status-badge.offline {
            background: rgba(139, 148, 158, 0.1);
            color: var(--text-muted);
            border: 1px solid var(--text-muted);
        }

        .status-badge.in-call {
            background: rgba(31, 111, 235, 0.1);
            color: var(--accent-blue);
            border: 1px solid var(--accent-blue);
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border: 1px solid transparent;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-primary {
            background: var(--accent-blue);
            color: white;
        }

        .btn-primary:hover {
            background: #1a5cd8;
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border-color: var(--border-primary);
        }

        .btn-secondary:hover {
            background: var(--bg-primary);
        }

        .btn-success {
            background: var(--accent-green);
            color: white;
        }

        .btn-success:hover {
            background: #1f7a2e;
        }

        .btn-danger {
            background: var(--accent-red);
            color: white;
        }

        .btn-danger:hover {
            background: #e5484d;
        }

        .btn-sm {
            padding: 0.375rem 0.75rem;
            font-size: 0.75rem;
        }

        /* Forms */
        .form-group {
            margin-bottom: 1rem;
        }

        .form-label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-primary);
        }

        .form-input {
            width: 100%;
            padding: 0.75rem;
            background: var(--bg-primary);
            border: 1px solid var(--border-primary);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 0.875rem;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.1);
        }

        .form-textarea {
            resize: vertical;
            min-height: 100px;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 2000;
        }

        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background: var(--bg-secondary);
            border: 1px solid var(--border-primary);
            border-radius: 8px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .modal-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0;
        }

        .modal-close:hover {
            color: var(--text-primary);
        }

        /* Loading States */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            color: var(--text-muted);
        }

        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid var(--border-primary);
            border-top: 2px solid var(--accent-blue);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 0.5rem;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Real-time indicators */
        .real-time-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.75rem;
            color: var(--accent-blue);
        }

        .real-time-dot {
            width: 6px;
            height: 6px;
            background: var(--accent-blue);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }

        /* Call Control Panel */
        .call-control-panel {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }

        .control-btn {
            width: 32px;
            height: 32px;
            border-radius: 6px;
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .control-btn.answer {
            background: var(--accent-green);
            color: white;
        }

        .control-btn.transfer {
            background: var(--accent-blue);
            color: white;
        }

        .control-btn.hangup {
            background: var(--accent-red);
            color: white;
        }

        .control-btn:hover {
            transform: scale(1.1);
        }

        /* VIP Indicators */
        .vip-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            color: var(--accent-orange);
        }

        /* Priority Levels */
        .priority-high { color: var(--accent-red); }
        .priority-normal { color: var(--text-secondary); }
        .priority-vip { color: var(--accent-orange); }

        /* Responsive Design */
        @media (max-width: 1024px) {
            .sidebar {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }

            .sidebar.open {
                transform: translateX(0);
            }

            .main-content {
                margin-left: 0;
            }

            .dashboard-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>"""
<body>
    <div class="dashboard-container">
        <!-- Sidebar -->
        <nav class="sidebar">
            <div class="sidebar-header">
                <div class="logo">
                    <i class="fas fa-headset"></i>
                    <span>VoiceCore AI</span>
                    <span class="enterprise-badge">ENTERPRISE</span>
                </div>
            </div>
            
            <div class="nav-menu">
                <div class="nav-section">
                    <div class="nav-section-title">Dashboard</div>
                    <button class="nav-item active" onclick="showSection('overview')">
                        <i class="fas fa-chart-line"></i>
                        <span>Overview</span>
                    </button>
                    <button class="nav-item" onclick="showSection('real-time')">
                        <i class="fas fa-broadcast-tower"></i>
                        <span>Real-time Monitor</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Call Operations</div>
                    <button class="nav-item" onclick="showSection('live-calls')">
                        <i class="fas fa-phone"></i>
                        <span>Live Calls</span>
                    </button>
                    <button class="nav-item" onclick="showSection('call-queue')">
                        <i class="fas fa-list-ol"></i>
                        <span>Call Queue</span>
                    </button>
                    <button class="nav-item" onclick="showSection('call-routing')">
                        <i class="fas fa-route"></i>
                        <span>Call Routing</span>
                    </button>
                    <button class="nav-item" onclick="showSection('call-history')">
                        <i class="fas fa-history"></i>
                        <span>Call History</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Agent Management</div>
                    <button class="nav-item" onclick="showSection('agents')">
                        <i class="fas fa-users"></i>
                        <span>Agents</span>
                    </button>
                    <button class="nav-item" onclick="showSection('departments')">
                        <i class="fas fa-building"></i>
                        <span>Departments</span>
                    </button>
                    <button class="nav-item" onclick="showSection('schedules')">
                        <i class="fas fa-calendar-alt"></i>
                        <span>Schedules</span>
                    </button>
                    <button class="nav-item" onclick="showSection('performance')">
                        <i class="fas fa-chart-bar"></i>
                        <span>Performance</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">AI & Intelligence</div>
                    <button class="nav-item" onclick="showSection('ai-training')">
                        <i class="fas fa-brain"></i>
                        <span>AI Training</span>
                    </button>
                    <button class="nav-item" onclick="showSection('conversation-flows')">
                        <i class="fas fa-project-diagram"></i>
                        <span>Conversation Flows</span>
                    </button>
                    <button class="nav-item" onclick="showSection('knowledge-base')">
                        <i class="fas fa-book"></i>
                        <span>Knowledge Base</span>
                    </button>
                    <button class="nav-item" onclick="showSection('spam-detection')">
                        <i class="fas fa-shield-alt"></i>
                        <span>Spam Detection</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Analytics & Reports</div>
                    <button class="nav-item" onclick="showSection('analytics')">
                        <i class="fas fa-analytics"></i>
                        <span>Analytics</span>
                    </button>
                    <button class="nav-item" onclick="showSection('reports')">
                        <i class="fas fa-file-alt"></i>
                        <span>Reports</span>
                    </button>
                    <button class="nav-item" onclick="showSection('insights')">
                        <i class="fas fa-lightbulb"></i>
                        <span>Insights</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">System</div>
                    <button class="nav-item" onclick="showSection('vip-management')">
                        <i class="fas fa-crown"></i>
                        <span>VIP Management</span>
                    </button>
                    <button class="nav-item" onclick="showSection('integrations')">
                        <i class="fas fa-plug"></i>
                        <span>Integrations</span>
                    </button>
                    <button class="nav-item" onclick="showSection('security')">
                        <i class="fas fa-lock"></i>
                        <span>Security</span>
                    </button>
                    <button class="nav-item" onclick="showSection('settings')">
                        <i class="fas fa-cog"></i>
                        <span>Settings</span>
                    </button>
                </div>
            </div>
        </nav>

        <!-- Main Content -->
        <main class="main-content">
            <!-- Header -->
            <header class="header">
                <h1 class="header-title" id="page-title">Enterprise Command Center</h1>
                <div class="header-actions">
                    <div class="status-indicator">
                        <div class="status-dot"></div>
                        <span>ONLINE</span>
                    </div>
                    <div class="real-time-indicator">
                        <div class="real-time-dot"></div>
                        <span>NEURAL LINK ACTIVE</span>
                    </div>
                </div>
            </header>

            <!-- Content -->
            <div class="content">
                <!-- Overview Section -->
                <div id="overview-section" class="section active">
                    <div class="dashboard-grid">
                        <!-- Key Metrics -->
                        <div class="card">
                            <div class="card-header">
                                <h3 class="card-title">
                                    <i class="fas fa-phone"></i>
                                    Active Calls
                                </h3>
                            </div>
                            <div class="card-content metric-card">
                                <div class="metric-value blue" id="active-calls-count">0</div>
                                <div class="metric-label">Currently Active</div>
                                <div class="metric-change positive">
                                    <i class="fas fa-arrow-up"></i>
                                    <span>↑ +12% today</span>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h3 class="card-title">
                                    <i class="fas fa-users"></i>
                                    Available Agents
                                </h3>
                            </div>
                            <div class="card-content metric-card">
                                <div class="metric-value green" id="available-agents-count">0</div>
                                <div class="metric-label">Ready to Take Calls</div>
                                <div class="metric-change positive">
                                    <i class="fas fa-arrow-up"></i>
                                    <span>85% capacity</span>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h3 class="card-title">
                                    <i class="fas fa-list-ol"></i>
                                    Queue Size
                                </h3>
                            </div>
                            <div class="card-content metric-card">
                                <div class="metric-value red" id="queue-size-count">0</div>
                                <div class="metric-label">Calls Waiting</div>
                                <div class="metric-change negative">
                                    <i class="fas fa-arrow-down"></i>
                                    <span>↓ -5% hour</span>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h3 class="card-title">
                                    <i class="fas fa-robot"></i>
                                    AI Resolution Rate
                                </h3>
                            </div>
                            <div class="card-content metric-card">
                                <div class="metric-value purple" id="ai-resolution-rate">0%</div>
                                <div class="metric-label">Resolved by AI</div>
                                <div class="metric-change positive">
                                    <i class="fas fa-arrow-up"></i>
                                    <span>↑ +3% week</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Activity -->
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-clock"></i>
                                Recent Activity
                            </h3>
                        </div>
                        <div class="card-content">
                            <div class="table-container">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Time</th>
                                            <th>Event</th>
                                            <th>Agent/System</th>
                                            <th>Details</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody id="recent-activity-table">
                                        <tr>
                                            <td colspan="5" class="loading">
                                                <div class="spinner"></div>
                                                Loading recent activity...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Live Calls Section -->
                <div id="live-calls-section" class="section" style="display: none;">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-phone"></i>
                                Live Call Monitor
                            </h3>
                        </div>
                        <div class="card-content">
                            <div class="table-container">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Caller</th>
                                            <th>Agent</th>
                                            <th>Department</th>
                                            <th>Duration</th>
                                            <th>Status</th>
                                            <th>Priority</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="live-calls-table">
                                        <tr>
                                            <td colspan="7" class="loading">
                                                <div class="spinner"></div>
                                                Loading live calls...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Agents Section -->
                <div id="agents-section" class="section" style="display: none;">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-users"></i>
                                Agent Management
                            </h3>
                            <button class="btn btn-primary btn-sm" onclick="showCreateAgentModal()">
                                <i class="fas fa-plus"></i>
                                Add Agent
                            </button>
                        </div>
                        <div class="card-content">
                            <div class="table-container">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Name</th>
                                            <th>Extension</th>
                                            <th>Department</th>
                                            <th>Status</th>
                                            <th>Current Calls</th>
                                            <th>Performance</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="agents-table">
                                        <tr>
                                            <td colspan="7" class="loading">
                                                <div class="spinner"></div>
                                                Loading agents...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- AI Training Section -->
                <div id="ai-training-section" class="section" style="display: none;">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-brain"></i>
                                AI Training & Knowledge Base
                            </h3>
                            <button class="btn btn-primary btn-sm" onclick="showCreateKnowledgeModal()">
                                <i class="fas fa-plus"></i>
                                Add Knowledge
                            </button>
                        </div>
                        <div class="card-content">
                            <div class="table-container">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Question</th>
                                            <th>Answer</th>
                                            <th>Category</th>
                                            <th>Priority</th>
                                            <th>Status</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="knowledge-base-table">
                                        <tr>
                                            <td colspan="6" class="loading">
                                                <div class="spinner"></div>
                                                Loading knowledge base...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Spam Detection Section -->
                <div id="spam-detection-section" class="section" style="display: none;">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-shield-alt"></i>
                                Spam Detection Rules
                            </h3>
                            <button class="btn btn-primary btn-sm" onclick="showCreateSpamRuleModal()">
                                <i class="fas fa-plus"></i>
                                Add Rule
                            </button>
                        </div>
                        <div class="card-content">
                            <div class="table-container">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Rule Type</th>
                                            <th>Rule Value</th>
                                            <th>Action</th>
                                            <th>Weight</th>
                                            <th>Status</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="spam-rules-table">
                                        <tr>
                                            <td colspan="6" class="loading">
                                                <div class="spinner"></div>
                                                Loading spam rules...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- VIP Management Section -->
                <div id="vip-management-section" class="section" style="display: none;">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fas fa-crown"></i>
                                VIP Caller Management
                            </h3>
                            <button class="btn btn-primary btn-sm" onclick="showCreateVIPModal()">
                                <i class="fas fa-plus"></i>
                                Add VIP
                            </button>
                        </div>
                        <div class="card-content">
                            <div class="table-container">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Name</th>
                                            <th>Phone Number</th>
                                            <th>Company</th>
                                            <th>Priority</th>
                                            <th>Special Instructions</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="vip-callers-table">
                                        <tr>
                                            <td colspan="6" class="loading">
                                                <div class="spinner"></div>
                                                Loading VIP callers...
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Other sections placeholders -->
                <div id="real-time-section" class="section" style="display: none;">
                    <h2>Real-time Monitor - Advanced Features Coming Soon</h2>
                </div>

                <div id="call-queue-section" class="section" style="display: none;">
                    <h2>Call Queue Management - Advanced Features Coming Soon</h2>
                </div>

                <div id="analytics-section" class="section" style="display: none;">
                    <h2>Advanced Analytics - Coming Soon</h2>
                </div>
            </div>
        </main>
    </div>
    <!-- Modals -->
    <!-- Create Agent Modal -->
    <div id="create-agent-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Create New Agent</h3>
                <button class="modal-close" onclick="hideModal('create-agent-modal')">&times;</button>
            </div>
            <form id="create-agent-form" onsubmit="createAgent(event)">
                <div class="form-group">
                    <label class="form-label">Name</label>
                    <input type="text" name="name" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="email" name="email" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Extension</label>
                    <input type="text" name="extension" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Department</label>
                    <select name="department_id" class="form-input">
                        <option value="">Select Department</option>
                        <!-- Populated dynamically -->
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Skills (comma separated)</label>
                    <input type="text" name="skills" class="form-input" placeholder="customer service, technical support">
                </div>
                <div class="form-group">
                    <label class="form-label">Languages (comma separated)</label>
                    <input type="text" name="languages" class="form-input" value="en" placeholder="en, es">
                </div>
                <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                    <button type="button" class="btn btn-secondary" onclick="hideModal('create-agent-modal')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Agent</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Create Knowledge Modal -->
    <div id="create-knowledge-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Add Knowledge Entry</h3>
                <button class="modal-close" onclick="hideModal('create-knowledge-modal')">&times;</button>
            </div>
            <form id="create-knowledge-form" onsubmit="createKnowledgeEntry(event)">
                <div class="form-group">
                    <label class="form-label">Question</label>
                    <input type="text" name="question" class="form-input" required placeholder="What is your return policy?">
                </div>
                <div class="form-group">
                    <label class="form-label">Answer</label>
                    <textarea name="answer" class="form-input form-textarea" required placeholder="Our return policy allows..."></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Category</label>
                    <input type="text" name="category" class="form-input" placeholder="policies, support, billing">
                </div>
                <div class="form-group">
                    <label class="form-label">Priority (0-10)</label>
                    <input type="number" name="priority" class="form-input" min="0" max="10" value="5">
                </div>
                <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                    <button type="button" class="btn btn-secondary" onclick="hideModal('create-knowledge-modal')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Add Knowledge</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Create Spam Rule Modal -->
    <div id="create-spam-rule-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Add Spam Detection Rule</h3>
                <button class="modal-close" onclick="hideModal('create-spam-rule-modal')">&times;</button>
            </div>
            <form id="create-spam-rule-form" onsubmit="createSpamRule(event)">
                <div class="form-group">
                    <label class="form-label">Rule Type</label>
                    <select name="rule_type" class="form-input" required>
                        <option value="keyword">Keyword</option>
                        <option value="pattern">Pattern</option>
                        <option value="number">Phone Number</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Rule Value</label>
                    <input type="text" name="rule_value" class="form-input" required placeholder="telemarketing, sales, etc.">
                </div>
                <div class="form-group">
                    <label class="form-label">Action</label>
                    <select name="action" class="form-input" required>
                        <option value="block">Block</option>
                        <option value="flag">Flag</option>
                        <option value="challenge">Challenge</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Weight (1-100)</label>
                    <input type="number" name="weight" class="form-input" min="1" max="100" value="10">
                </div>
                <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                    <button type="button" class="btn btn-secondary" onclick="hideModal('create-spam-rule-modal')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Add Rule</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Global variables
        let websocket = null;
        let dashboardData = {};
        let currentSection = 'overview';

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeWebSocket();
            loadInitialData();
            startPeriodicUpdates();
        });

        // WebSocket connection
        function initializeWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function(event) {
                console.log('WebSocket connected');
            };
            
            websocket.onmessage = function(event) {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            };
            
            websocket.onclose = function(event) {
                console.log('WebSocket disconnected');
                // Attempt to reconnect after 5 seconds
                setTimeout(initializeWebSocket, 5000);
            };
            
            websocket.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }

        // Handle WebSocket messages
        function handleWebSocketMessage(message) {
            switch(message.type) {
                case 'initial_data':
                    dashboardData = message.data;
                    updateDashboard();
                    break;
                case 'real_time_update':
                    updateRealTimeData(message.data);
                    break;
                default:
                    console.log('Unknown message type:', message.type);
            }
        }

        // Load initial data via REST API
        async function loadInitialData() {
            try {
                const response = await fetch('/api/dashboard/overview');
                const data = await response.json();
                dashboardData = data;
                updateDashboard();
            } catch (error) {
                console.error('Failed to load initial data:', error);
            }
        }

        // Update dashboard with new data
        function updateDashboard() {
            updateMetrics();
            updateRecentActivity();
            
            if (currentSection === 'live-calls') {
                updateLiveCalls();
            } else if (currentSection === 'agents') {
                updateAgentsTable();
            } else if (currentSection === 'ai-training') {
                updateKnowledgeBaseTable();
            } else if (currentSection === 'spam-detection') {
                updateSpamRulesTable();
            } else if (currentSection === 'vip-management') {
                updateVIPCallersTable();
            }
        }

        // Update key metrics
        function updateMetrics() {
            if (dashboardData.analytics) {
                const analytics = dashboardData.analytics;
                
                document.getElementById('active-calls-count').textContent = 
                    analytics.call_metrics?.total_calls || 0;
                
                document.getElementById('available-agents-count').textContent = 
                    analytics.agent_metrics?.available_agents || 0;
                
                document.getElementById('queue-size-count').textContent = 
                    analytics.system_metrics?.queue_size || 0;
                
                const aiResolutionRate = analytics.call_metrics?.ai_resolution_rate || 0;
                document.getElementById('ai-resolution-rate').textContent = 
                    Math.round(aiResolutionRate * 100) + '%';
            }
        }

        // Update real-time data
        function updateRealTimeData(data) {
            document.getElementById('active-calls-count').textContent = data.active_calls || 0;
            document.getElementById('queue-size-count').textContent = data.queue_size || 0;
            
            if (data.agent_status) {
                document.getElementById('available-agents-count').textContent = 
                    data.agent_status.available || 0;
            }
        }

        // Update recent activity table
        function updateRecentActivity() {
            const tbody = document.getElementById('recent-activity-table');
            tbody.innerHTML = `
                <tr>
                    <td>12:34 PM</td>
                    <td>Call Answered</td>
                    <td>John Smith (Ext. 101)</td>
                    <td>Customer inquiry about billing</td>
                    <td><span class="status-badge in-call">In Progress</span></td>
                </tr>
                <tr>
                    <td>12:32 PM</td>
                    <td>Agent Available</td>
                    <td>Sarah Johnson (Ext. 102)</td>
                    <td>Status changed to available</td>
                    <td><span class="status-badge available">Available</span></td>
                </tr>
                <tr>
                    <td>12:30 PM</td>
                    <td>AI Resolution</td>
                    <td>AI Assistant</td>
                    <td>Resolved shipping inquiry</td>
                    <td><span class="status-badge available">Completed</span></td>
                </tr>
                <tr>
                    <td>12:28 PM</td>
                    <td>Spam Blocked</td>
                    <td>Spam Detector</td>
                    <td>Telemarketing call blocked</td>
                    <td><span class="status-badge offline">Blocked</span></td>
                </tr>
            `;
        }

        // Navigation functions
        function showSection(sectionName) {
            // Hide all sections
            document.querySelectorAll('.section').forEach(section => {
                section.style.display = 'none';
            });
            
            // Remove active class from all nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Show selected section
            const section = document.getElementById(sectionName + '-section');
            if (section) {
                section.style.display = 'block';
            }
            
            // Add active class to clicked nav item
            event.target.classList.add('active');
            
            // Update page title
            const titles = {
                'overview': 'Enterprise Command Center',
                'live-calls': 'Live Call Monitor',
                'agents': 'Agent Management',
                'ai-training': 'AI Training & Knowledge Base',
                'spam-detection': 'Spam Detection Rules',
                'vip-management': 'VIP Caller Management'
            };
            
            document.getElementById('page-title').textContent = titles[sectionName] || 'Dashboard';
            currentSection = sectionName;
            
            // Load section-specific data
            if (sectionName === 'agents') {
                updateAgentsTable();
            } else if (sectionName === 'live-calls') {
                updateLiveCalls();
            } else if (sectionName === 'ai-training') {
                updateKnowledgeBaseTable();
            } else if (sectionName === 'spam-detection') {
                updateSpamRulesTable();
            } else if (sectionName === 'vip-management') {
                updateVIPCallersTable();
            }
        }

        // Update live calls table
        async function updateLiveCalls() {
            try {
                const response = await fetch('/api/calls/live');
                const data = await response.json();
                
                const tbody = document.getElementById('live-calls-table');
                if (data.active_calls && data.active_calls.length > 0) {
                    tbody.innerHTML = data.active_calls.map(call => `
                        <tr>
                            <td>
                                ${call.from_number}
                                ${call.is_vip ? '<span class="vip-indicator"><i class="fas fa-crown"></i></span>' : ''}
                            </td>
                            <td>${call.agent ? `${call.agent.name} (${call.agent.extension})` : 'Unassigned'}</td>
                            <td>${call.department || 'General'}</td>
                            <td>${formatDuration(call.duration)}</td>
                            <td><span class="status-badge in-call">${call.status}</span></td>
                            <td><span class="priority-${call.is_vip ? 'vip' : 'normal'}">${call.is_vip ? 'VIP' : 'Normal'}</span></td>
                            <td>
                                <div class="call-control-panel">
                                    <button class="control-btn transfer" title="Transfer Call">
                                        <i class="fas fa-exchange-alt"></i>
                                    </button>
                                    <button class="control-btn hangup" title="End Call">
                                        <i class="fas fa-phone-slash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No active calls</td></tr>';
                }
            } catch (error) {
                console.error('Failed to update live calls:', error);
            }
        }

        // Update agents table
        async function updateAgentsTable() {
            try {
                const response = await fetch('/api/agents/management');
                const data = await response.json();
                
                const tbody = document.getElementById('agents-table');
                if (data.agents && data.agents.length > 0) {
                    tbody.innerHTML = data.agents.map(agent => `
                        <tr>
                            <td>
                                <strong>${agent.name}</strong>
                                <br>
                                <small style="color: var(--text-muted);">${agent.email}</small>
                            </td>
                            <td>${agent.extension}</td>
                            <td>${agent.department}</td>
                            <td>
                                <span class="status-badge ${agent.status}">
                                    ${agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
                                </span>
                            </td>
                            <td>${agent.current_calls}/${agent.max_concurrent_calls}</td>
                            <td>
                                <div style="font-size: 0.875rem;">
                                    <div>Calls: ${agent.metrics.calls_handled}</div>
                                    <div>Avg: ${formatDuration(agent.metrics.average_call_duration)}</div>
                                    <div>Util: ${Math.round(agent.metrics.utilization_rate * 100)}%</div>
                                </div>
                            </td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="editAgent('${agent.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No agents found</td></tr>';
                }
            } catch (error) {
                console.error('Failed to update agents table:', error);
            }
        }

        // Update knowledge base table
        async function updateKnowledgeBaseTable() {
            try {
                const response = await fetch('/api/ai-training/knowledge-base');
                const data = await response.json();
                
                const tbody = document.getElementById('knowledge-base-table');
                if (data.knowledge_base && data.knowledge_base.length > 0) {
                    tbody.innerHTML = data.knowledge_base.map(entry => `
                        <tr>
                            <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;">${entry.question}</td>
                            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis;">${entry.answer}</td>
                            <td>${entry.category || 'General'}</td>
                            <td>${entry.priority}</td>
                            <td>
                                <span class="status-badge ${entry.active ? 'available' : 'offline'}">
                                    ${entry.active ? 'Active' : 'Inactive'}
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="editKnowledgeEntry('${entry.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No knowledge entries found</td></tr>';
                }
            } catch (error) {
                console.error('Failed to update knowledge base table:', error);
            }
        }

        // Update spam rules table
        async function updateSpamRulesTable() {
            try {
                const response = await fetch('/api/spam-detection/rules');
                const data = await response.json();
                
                const tbody = document.getElementById('spam-rules-table');
                if (data.spam_rules && data.spam_rules.length > 0) {
                    tbody.innerHTML = data.spam_rules.map(rule => `
                        <tr>
                            <td>${rule.rule_type}</td>
                            <td>${rule.rule_value}</td>
                            <td>
                                <span class="status-badge ${rule.action === 'block' ? 'busy' : rule.action === 'flag' ? 'available' : 'in-call'}">
                                    ${rule.action.charAt(0).toUpperCase() + rule.action.slice(1)}
                                </span>
                            </td>
                            <td>${rule.weight}</td>
                            <td>
                                <span class="status-badge ${rule.active ? 'available' : 'offline'}">
                                    ${rule.active ? 'Active' : 'Inactive'}
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="editSpamRule('${rule.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No spam rules found</td></tr>';
                }
            } catch (error) {
                console.error('Failed to update spam rules table:', error);
            }
        }

        // Update VIP callers table
        async function updateVIPCallersTable() {
            try {
                const response = await fetch('/api/vip/callers');
                const data = await response.json();
                
                const tbody = document.getElementById('vip-callers-table');
                if (data.vip_callers && data.vip_callers.length > 0) {
                    tbody.innerHTML = data.vip_callers.map(vip => `
                        <tr>
                            <td>${vip.name}</td>
                            <td>${vip.phone_number}</td>
                            <td>${vip.company || 'N/A'}</td>
                            <td>
                                <span class="priority-${vip.priority >= 8 ? 'high' : vip.priority >= 5 ? 'vip' : 'normal'}">
                                    ${vip.priority}/10
                                </span>
                            </td>
                            <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;">${vip.special_instructions || 'None'}</td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="editVIPCaller('${vip.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No VIP callers found</td></tr>';
                }
            } catch (error) {
                console.error('Failed to update VIP callers table:', error);
            }
        }

        // Modal functions
        function showModal(modalId) {
            document.getElementById(modalId).classList.add('show');
        }

        function hideModal(modalId) {
            document.getElementById(modalId).classList.remove('show');
        }

        function showCreateAgentModal() {
            showModal('create-agent-modal');
        }

        function showCreateKnowledgeModal() {
            showModal('create-knowledge-modal');
        }

        function showCreateSpamRuleModal() {
            showModal('create-spam-rule-modal');
        }

        // Form submission functions
        async function createAgent(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            
            try {
                const response = await fetch('/api/agents', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    hideModal('create-agent-modal');
                    updateAgentsTable();
                    event.target.reset();
                } else {
                    alert('Failed to create agent: ' + result.message);
                }
            } catch (error) {
                console.error('Failed to create agent:', error);
                alert('Failed to create agent');
            }
        }

        async function createKnowledgeEntry(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            
            try {
                const response = await fetch('/api/ai-training/knowledge-base', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    hideModal('create-knowledge-modal');
                    updateKnowledgeBaseTable();
                    event.target.reset();
                } else {
                    alert('Failed to create knowledge entry: ' + result.message);
                }
            } catch (error) {
                console.error('Failed to create knowledge entry:', error);
                alert('Failed to create knowledge entry');
            }
        }

        async function createSpamRule(event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            
            try {
                const response = await fetch('/api/spam-detection/rules', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    hideModal('create-spam-rule-modal');
                    updateSpamRulesTable();
                    event.target.reset();
                } else {
                    alert('Failed to create spam rule: ' + result.message);
                }
            } catch (error) {
                console.error('Failed to create spam rule:', error);
                alert('Failed to create spam rule');
            }
        }

        // Utility functions
        function formatDuration(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            } else {
                return `${minutes}:${secs.toString().padStart(2, '0')}`;
            }
        }

        function editAgent(agentId) {
            // Placeholder for edit functionality
            console.log('Edit agent:', agentId);
        }

        function editKnowledgeEntry(entryId) {
            // Placeholder for edit functionality
            console.log('Edit knowledge entry:', entryId);
        }

        function editSpamRule(ruleId) {
            // Placeholder for edit functionality
            console.log('Edit spam rule:', ruleId);
        }

        function editVIPCaller(vipId) {
            // Placeholder for edit functionality
            console.log('Edit VIP caller:', vipId);
        }

        // Start periodic updates
        function startPeriodicUpdates() {
            setInterval(() => {
                if (currentSection === 'overview') {
                    updateMetrics();
                    updateRecentActivity();
                } else if (currentSection === 'live-calls') {
                    updateLiveCalls();
                }
            }, 5000); // Update every 5 seconds
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app = create_tech_startup_dashboard_app()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)