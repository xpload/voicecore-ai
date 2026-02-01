"""
VIP caller management service for VoiceCore AI.

Provides comprehensive VIP caller identification, priority routing,
and special handling rules for premium customer experience.
"""

import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from voicecore.database import get_db_session, set_tenant_context
from voicecore.models import (
    VIPCaller, VIPCallHistory, VIPEscalationRule, Call,
    VIPPriority, VIPStatus, VIPHandlingRule, Agent, Department
)
from voicecore.logging import get_logger
from voicecore.utils.security import SecurityUtils


logger = get_logger(__name__)


class VIPServiceError(Exception):
    """Base exception for VIP service errors."""
    pass


class VIPNotFoundError(VIPServiceError):
    """Raised when a VIP caller is not found."""
    pass


class VIPService:
    """
    Comprehensive VIP caller management service.
    
    Handles VIP caller identification, priority routing, special handling rules,
    and escalation management for premium customer experience.
    """
    
    def __init__(self):
        self.logger = logger
    
    async def identify_vip_caller(
        self,
        tenant_id: uuid.UUID,
        phone_number: str
    ) -> Optional[VIPCaller]:
        """
        Identify if a caller is VIP based on phone number.
        
        Args:
            tenant_id: Tenant UUID
            phone_number: Caller's phone number
            
        Returns:
            Optional[VIPCaller]: VIP caller instance or None if not VIP
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Hash phone number for privacy-compliant lookup
                hashed_phone = SecurityUtils.hash_phone_number(phone_number)
                
                # Look for VIP caller by primary or alternative phone
                result = await session.execute(
                    select(VIPCaller)
                    .options(
                        selectinload(VIPCaller.preferred_agent),
                        selectinload(VIPCaller.preferred_department)
                    )
                    .where(
                        and_(
                            VIPCaller.tenant_id == tenant_id,
                            or_(
                                VIPCaller.phone_number == hashed_phone,
                                VIPCaller.alternative_phone == hashed_phone
                            )
                        )
                    )
                )
                
                vip_caller = result.scalar_one_or_none()
                
                if vip_caller and vip_caller.is_active:
                    self.logger.info(
                        "VIP caller identified",
                        tenant_id=str(tenant_id),
                        vip_id=str(vip_caller.id),
                        vip_level=vip_caller.vip_level.value,
                        caller_name=vip_caller.caller_name
                    )
                    return vip_caller
                
                return None
                
        except Exception as e:
            self.logger.error(
                "Failed to identify VIP caller",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            return None
    
    async def create_vip_caller(
        self,
        tenant_id: uuid.UUID,
        vip_data: Dict[str, Any]
    ) -> VIPCaller:
        """
        Create a new VIP caller.
        
        Args:
            tenant_id: Tenant UUID
            vip_data: Dictionary containing VIP caller information
            
        Returns:
            VIPCaller: Created VIP caller instance
            
        Raises:
            VIPServiceError: If creation fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Hash phone numbers for privacy
                hashed_phone = SecurityUtils.hash_phone_number(vip_data["phone_number"])
                hashed_alt_phone = None
                if vip_data.get("alternative_phone"):
                    hashed_alt_phone = SecurityUtils.hash_phone_number(vip_data["alternative_phone"])
                
                # Check if VIP already exists
                existing_result = await session.execute(
                    select(VIPCaller).where(
                        and_(
                            VIPCaller.tenant_id == tenant_id,
                            or_(
                                VIPCaller.phone_number == hashed_phone,
                                VIPCaller.alternative_phone == hashed_phone
                            )
                        )
                    )
                )
                
                if existing_result.scalar_one_or_none():
                    raise VIPServiceError("VIP caller already exists with this phone number")
                
                # Create VIP caller
                vip_caller = VIPCaller(
                    tenant_id=tenant_id,
                    phone_number=hashed_phone,
                    alternative_phone=hashed_alt_phone,
                    caller_name=vip_data["caller_name"],
                    company_name=vip_data.get("company_name"),
                    vip_level=VIPPriority(vip_data.get("vip_level", VIPPriority.STANDARD.value)),
                    status=VIPStatus(vip_data.get("status", VIPStatus.ACTIVE.value)),
                    preferred_agent_id=vip_data.get("preferred_agent_id"),
                    preferred_department_id=vip_data.get("preferred_department_id"),
                    handling_rules=vip_data.get("handling_rules", []),
                    custom_greeting=vip_data.get("custom_greeting"),
                    custom_hold_music=vip_data.get("custom_hold_music"),
                    max_wait_time=vip_data.get("max_wait_time", 60),
                    callback_priority=vip_data.get("callback_priority", 1),
                    email=vip_data.get("email"),
                    account_number=vip_data.get("account_number"),
                    account_value=vip_data.get("account_value"),
                    valid_from=vip_data.get("valid_from", datetime.utcnow()),
                    valid_until=vip_data.get("valid_until"),
                    notes=vip_data.get("notes"),
                    tags=vip_data.get("tags", []),
                    metadata=vip_data.get("metadata", {})
                )
                
                session.add(vip_caller)
                await session.commit()
                
                self.logger.info(
                    "VIP caller created",
                    tenant_id=str(tenant_id),
                    vip_id=str(vip_caller.id),
                    caller_name=vip_caller.caller_name,
                    vip_level=vip_caller.vip_level.value
                )
                
                return vip_caller
                
        except IntegrityError as e:
            self.logger.error("VIP creation failed due to constraint violation", error=str(e))
            raise VIPServiceError("VIP caller with this information already exists")
        except Exception as e:
            self.logger.error("VIP creation failed", tenant_id=str(tenant_id), error=str(e))
            raise VIPServiceError(f"Failed to create VIP caller: {str(e)}")
    
    async def get_vip_caller(
        self,
        tenant_id: uuid.UUID,
        vip_id: uuid.UUID
    ) -> Optional[VIPCaller]:
        """
        Get VIP caller by ID.
        
        Args:
            tenant_id: Tenant UUID
            vip_id: VIP caller UUID
            
        Returns:
            Optional[VIPCaller]: VIP caller instance or None if not found
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    select(VIPCaller)
                    .options(
                        selectinload(VIPCaller.preferred_agent),
                        selectinload(VIPCaller.preferred_department)
                    )
                    .where(
                        and_(
                            VIPCaller.tenant_id == tenant_id,
                            VIPCaller.id == vip_id
                        )
                    )
                )
                
                return result.scalar_one_or_none()
                
        except Exception as e:
            self.logger.error(
                "Failed to get VIP caller",
                tenant_id=str(tenant_id),
                vip_id=str(vip_id),
                error=str(e)
            )
            return None
    
    async def list_vip_callers(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        vip_level: Optional[VIPPriority] = None,
        status: Optional[VIPStatus] = None,
        search: Optional[str] = None
    ) -> List[VIPCaller]:
        """
        List VIP callers with filtering and pagination.
        
        Args:
            tenant_id: Tenant UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            vip_level: Filter by VIP level
            status: Filter by VIP status
            search: Search term for name or company
            
        Returns:
            List[VIPCaller]: List of VIP caller instances
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                query = select(VIPCaller).where(VIPCaller.tenant_id == tenant_id)
                
                # Apply filters
                if vip_level:
                    query = query.where(VIPCaller.vip_level == vip_level)
                
                if status:
                    query = query.where(VIPCaller.status == status)
                
                if search:
                    search_term = f"%{search}%"
                    query = query.where(
                        or_(
                            VIPCaller.caller_name.ilike(search_term),
                            VIPCaller.company_name.ilike(search_term)
                        )
                    )
                
                # Apply pagination and ordering
                query = query.offset(skip).limit(limit).order_by(
                    VIPCaller.vip_level.desc(),
                    VIPCaller.caller_name.asc()
                )
                
                result = await session.execute(query)
                return list(result.scalars().all())
                
        except Exception as e:
            self.logger.error("Failed to list VIP callers", tenant_id=str(tenant_id), error=str(e))
            return []
    
    async def update_vip_caller(
        self,
        tenant_id: uuid.UUID,
        vip_id: uuid.UUID,
        update_data: Dict[str, Any]
    ) -> Optional[VIPCaller]:
        """
        Update VIP caller information.
        
        Args:
            tenant_id: Tenant UUID
            vip_id: VIP caller UUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Optional[VIPCaller]: Updated VIP caller instance or None if not found
            
        Raises:
            VIPNotFoundError: If VIP caller doesn't exist
            VIPServiceError: If update fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get existing VIP caller
                result = await session.execute(
                    select(VIPCaller).where(
                        and_(
                            VIPCaller.tenant_id == tenant_id,
                            VIPCaller.id == vip_id
                        )
                    )
                )
                vip_caller = result.scalar_one_or_none()
                
                if not vip_caller:
                    raise VIPNotFoundError(f"VIP caller {vip_id} not found")
                
                # Update allowed fields
                allowed_fields = [
                    'caller_name', 'company_name', 'vip_level', 'status',
                    'preferred_agent_id', 'preferred_department_id', 'handling_rules',
                    'custom_greeting', 'custom_hold_music', 'max_wait_time',
                    'callback_priority', 'email', 'account_number', 'account_value',
                    'valid_from', 'valid_until', 'notes', 'tags', 'metadata'
                ]
                
                for field, value in update_data.items():
                    if field in allowed_fields and hasattr(vip_caller, field):
                        if field in ['vip_level', 'status'] and isinstance(value, str):
                            # Convert string enum values
                            if field == 'vip_level':
                                value = VIPPriority(value)
                            elif field == 'status':
                                value = VIPStatus(value)
                        
                        # Handle phone number updates with hashing
                        if field in ['phone_number', 'alternative_phone'] and value:
                            value = SecurityUtils.hash_phone_number(value)
                        
                        setattr(vip_caller, field, value)
                
                vip_caller.updated_at = datetime.utcnow()
                await session.commit()
                
                self.logger.info(
                    "VIP caller updated",
                    tenant_id=str(tenant_id),
                    vip_id=str(vip_id),
                    updated_fields=list(update_data.keys())
                )
                
                return vip_caller
                
        except VIPNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                "VIP caller update failed",
                tenant_id=str(tenant_id),
                vip_id=str(vip_id),
                error=str(e)
            )
            raise VIPServiceError(f"Failed to update VIP caller: {str(e)}")
    
    async def delete_vip_caller(
        self,
        tenant_id: uuid.UUID,
        vip_id: uuid.UUID
    ) -> bool:
        """
        Delete VIP caller.
        
        Args:
            tenant_id: Tenant UUID
            vip_id: VIP caller UUID
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            VIPNotFoundError: If VIP caller doesn't exist
            VIPServiceError: If deletion fails
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Verify VIP caller exists
                result = await session.execute(
                    select(VIPCaller).where(
                        and_(
                            VIPCaller.tenant_id == tenant_id,
                            VIPCaller.id == vip_id
                        )
                    )
                )
                vip_caller = result.scalar_one_or_none()
                
                if not vip_caller:
                    raise VIPNotFoundError(f"VIP caller {vip_id} not found")
                
                # Delete VIP caller (CASCADE will handle related data)
                await session.execute(
                    delete(VIPCaller).where(
                        and_(
                            VIPCaller.tenant_id == tenant_id,
                            VIPCaller.id == vip_id
                        )
                    )
                )
                
                await session.commit()
                
                self.logger.info(
                    "VIP caller deleted",
                    tenant_id=str(tenant_id),
                    vip_id=str(vip_id),
                    caller_name=vip_caller.caller_name
                )
                
                return True
                
        except VIPNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                "VIP caller deletion failed",
                tenant_id=str(tenant_id),
                vip_id=str(vip_id),
                error=str(e)
            )
            raise VIPServiceError(f"Failed to delete VIP caller: {str(e)}")
    
    async def get_vip_routing_priority(
        self,
        tenant_id: uuid.UUID,
        vip_caller: VIPCaller
    ) -> int:
        """
        Calculate routing priority for VIP caller.
        
        Args:
            tenant_id: Tenant UUID
            vip_caller: VIP caller instance
            
        Returns:
            int: Priority score for routing (higher = more priority)
        """
        try:
            base_priority = vip_caller.priority_score
            
            # Additional priority based on handling rules
            if vip_caller.has_handling_rule(VIPHandlingRule.IMMEDIATE_TRANSFER):
                base_priority += 50
            
            if vip_caller.has_handling_rule(VIPHandlingRule.PRIORITY_QUEUE):
                base_priority += 30
            
            if vip_caller.has_handling_rule(VIPHandlingRule.DEDICATED_AGENT):
                base_priority += 20
            
            # Time-based priority boost
            now = datetime.utcnow()
            if vip_caller.last_call_at:
                days_since_last_call = (now - vip_caller.last_call_at).days
                if days_since_last_call > 30:  # Long-time customer
                    base_priority += 10
            
            return base_priority
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate VIP routing priority",
                tenant_id=str(tenant_id),
                vip_id=str(vip_caller.id),
                error=str(e)
            )
            return vip_caller.vip_level.value * 10  # Fallback to basic priority
    
    async def check_escalation_rules(
        self,
        tenant_id: uuid.UUID,
        vip_caller: VIPCaller,
        wait_time: int,
        queue_position: int
    ) -> List[VIPEscalationRule]:
        """
        Check if any escalation rules should be triggered.
        
        Args:
            tenant_id: Tenant UUID
            vip_caller: VIP caller instance
            wait_time: Current wait time in seconds
            queue_position: Current queue position
            
        Returns:
            List[VIPEscalationRule]: List of rules that should be triggered
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get active escalation rules
                result = await session.execute(
                    select(VIPEscalationRule)
                    .where(
                        and_(
                            VIPEscalationRule.tenant_id == tenant_id,
                            VIPEscalationRule.is_active == True
                        )
                    )
                    .order_by(VIPEscalationRule.priority.desc())
                )
                
                escalation_rules = result.scalars().all()
                triggered_rules = []
                
                current_time = datetime.utcnow()
                
                for rule in escalation_rules:
                    # Check if rule is applicable for this VIP level and time
                    if rule.is_applicable(vip_caller.vip_level, current_time):
                        # Check if escalation conditions are met
                        if rule.should_escalate(wait_time, queue_position):
                            triggered_rules.append(rule)
                
                return triggered_rules
                
        except Exception as e:
            self.logger.error(
                "Failed to check escalation rules",
                tenant_id=str(tenant_id),
                vip_id=str(vip_caller.id),
                error=str(e)
            )
            return []
    
    async def record_vip_call(
        self,
        tenant_id: uuid.UUID,
        vip_caller_id: uuid.UUID,
        call_id: uuid.UUID,
        call_details: Dict[str, Any]
    ) -> VIPCallHistory:
        """
        Record VIP call history for analytics.
        
        Args:
            tenant_id: Tenant UUID
            vip_caller_id: VIP caller UUID
            call_id: Call UUID
            call_details: Dictionary containing call details
            
        Returns:
            VIPCallHistory: Created call history record
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Create VIP call history record
                call_history = VIPCallHistory(
                    tenant_id=tenant_id,
                    vip_caller_id=vip_caller_id,
                    call_id=call_id,
                    vip_level_at_call=call_details.get("vip_level", VIPPriority.STANDARD),
                    handling_rules_applied=call_details.get("handling_rules_applied", []),
                    preferred_agent_available=call_details.get("preferred_agent_available"),
                    routed_to_preferred=call_details.get("routed_to_preferred", False),
                    wait_time_seconds=call_details.get("wait_time_seconds", 0),
                    escalation_triggered=call_details.get("escalation_triggered", False),
                    custom_greeting_used=call_details.get("custom_greeting_used", False),
                    satisfaction_rating=call_details.get("satisfaction_rating"),
                    service_quality_score=call_details.get("service_quality_score"),
                    issue_resolved=call_details.get("issue_resolved"),
                    resolution_time=call_details.get("resolution_time"),
                    follow_up_scheduled=call_details.get("follow_up_scheduled", False),
                    caller_feedback=call_details.get("caller_feedback"),
                    agent_notes=call_details.get("agent_notes")
                )
                
                session.add(call_history)
                
                # Update VIP caller statistics
                await session.execute(
                    update(VIPCaller)
                    .where(
                        and_(
                            VIPCaller.tenant_id == tenant_id,
                            VIPCaller.id == vip_caller_id
                        )
                    )
                    .values(
                        total_calls=VIPCaller.total_calls + 1,
                        last_call_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                self.logger.info(
                    "VIP call history recorded",
                    tenant_id=str(tenant_id),
                    vip_caller_id=str(vip_caller_id),
                    call_id=str(call_id)
                )
                
                return call_history
                
        except Exception as e:
            self.logger.error(
                "Failed to record VIP call history",
                tenant_id=str(tenant_id),
                vip_caller_id=str(vip_caller_id),
                call_id=str(call_id),
                error=str(e)
            )
            raise VIPServiceError(f"Failed to record VIP call history: {str(e)}")
    
    async def get_vip_analytics(
        self,
        tenant_id: uuid.UUID,
        vip_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get VIP analytics and metrics.
        
        Args:
            tenant_id: Tenant UUID
            vip_id: Specific VIP caller UUID (optional)
            start_date: Start date for analytics period
            end_date: End date for analytics period
            
        Returns:
            Dict[str, Any]: VIP analytics data
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Set default date range if not provided
                if not end_date:
                    end_date = datetime.utcnow()
                if not start_date:
                    start_date = end_date - timedelta(days=30)
                
                analytics = {}
                
                # Base query conditions
                conditions = [
                    VIPCallHistory.tenant_id == tenant_id,
                    VIPCallHistory.created_at >= start_date,
                    VIPCallHistory.created_at <= end_date
                ]
                
                if vip_id:
                    conditions.append(VIPCallHistory.vip_caller_id == vip_id)
                
                # Get call volume by VIP level
                level_stats = await session.execute(
                    select(
                        VIPCallHistory.vip_level_at_call,
                        func.count().label('call_count'),
                        func.avg(VIPCallHistory.wait_time_seconds).label('avg_wait_time'),
                        func.avg(VIPCallHistory.satisfaction_rating).label('avg_satisfaction')
                    )
                    .where(and_(*conditions))
                    .group_by(VIPCallHistory.vip_level_at_call)
                )
                
                analytics['by_vip_level'] = [
                    {
                        'vip_level': row[0].value if row[0] else 'unknown',
                        'call_count': row[1],
                        'avg_wait_time': float(row[2]) if row[2] else 0,
                        'avg_satisfaction': float(row[3]) if row[3] else None
                    }
                    for row in level_stats.fetchall()
                ]
                
                # Get escalation statistics
                escalation_stats = await session.execute(
                    select(
                        func.count().label('total_calls'),
                        func.sum(func.cast(VIPCallHistory.escalation_triggered, Integer)).label('escalated_calls'),
                        func.avg(VIPCallHistory.service_quality_score).label('avg_quality_score')
                    )
                    .where(and_(*conditions))
                )
                
                escalation_row = escalation_stats.fetchone()
                if escalation_row:
                    total_calls = escalation_row[0] or 0
                    escalated_calls = escalation_row[1] or 0
                    analytics['escalation_rate'] = (escalated_calls / total_calls * 100) if total_calls > 0 else 0
                    analytics['avg_quality_score'] = float(escalation_row[2]) if escalation_row[2] else None
                
                # Get top VIP callers (if not filtering by specific VIP)
                if not vip_id:
                    top_vips = await session.execute(
                        select(
                            VIPCaller.caller_name,
                            VIPCaller.vip_level,
                            func.count(VIPCallHistory.id).label('call_count'),
                            func.avg(VIPCallHistory.satisfaction_rating).label('avg_satisfaction')
                        )
                        .join(VIPCallHistory, VIPCaller.id == VIPCallHistory.vip_caller_id)
                        .where(and_(*conditions))
                        .group_by(VIPCaller.id, VIPCaller.caller_name, VIPCaller.vip_level)
                        .order_by(func.count(VIPCallHistory.id).desc())
                        .limit(10)
                    )
                    
                    analytics['top_vip_callers'] = [
                        {
                            'caller_name': row[0],
                            'vip_level': row[1].value,
                            'call_count': row[2],
                            'avg_satisfaction': float(row[3]) if row[3] else None
                        }
                        for row in top_vips.fetchall()
                    ]
                
                return analytics
                
        except Exception as e:
            self.logger.error(
                "Failed to get VIP analytics",
                tenant_id=str(tenant_id),
                vip_id=str(vip_id) if vip_id else None,
                error=str(e)
            )
            return {}
    
    async def bulk_import_vips(
        self,
        tenant_id: uuid.UUID,
        vip_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk import VIP callers.
        
        Args:
            tenant_id: Tenant UUID
            vip_data_list: List of VIP caller data dictionaries
            
        Returns:
            Dict[str, Any]: Import results with success/failure counts
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                results = {
                    'total': len(vip_data_list),
                    'successful': 0,
                    'failed': 0,
                    'errors': []
                }
                
                for i, vip_data in enumerate(vip_data_list):
                    try:
                        # Create VIP caller (reuse existing method logic)
                        vip_caller = await self.create_vip_caller(tenant_id, vip_data)
                        results['successful'] += 1
                        
                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append({
                            'row': i + 1,
                            'data': vip_data.get('caller_name', 'Unknown'),
                            'error': str(e)
                        })
                
                self.logger.info(
                    "VIP bulk import completed",
                    tenant_id=str(tenant_id),
                    total=results['total'],
                    successful=results['successful'],
                    failed=results['failed']
                )
                
                return results
                
        except Exception as e:
            self.logger.error(
                "VIP bulk import failed",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise VIPServiceError(f"Bulk import failed: {str(e)}")