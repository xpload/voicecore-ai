"""
CRM Service for VoiceCore AI 2.0.

Provides comprehensive CRM functionality including contact management,
lead tracking, interaction history, and import/export capabilities.
"""

import uuid
import csv
import io
from typing import Dict, Any, Optional, List
from datetime import datetime

from voicecore.config import settings
from voicecore.database import get_db_session, set_tenant_context
from voicecore.models.crm import CRMContact, CRMLead, CRMInteraction, CRMActivity
from voicecore.logging import get_logger

logger = get_logger(__name__)


class CRMService:
    """
    Service for CRM operations.
    
    Manages contacts, leads, interactions, and provides import/export
    functionality for CRM data.
    """
    
    def __init__(self):
        self.logger = logger
    
    # Contact Management
    
    async def create_contact(
        self,
        tenant_id: uuid.UUID,
        first_name: str,
        last_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Optional[uuid.UUID]:
        """
        Create a new CRM contact.
        
        Args:
            tenant_id: Tenant UUID
            first_name: Contact first name
            last_name: Contact last name
            email: Contact email
            phone: Contact phone
            company: Company name
            tags: List of tags
            custom_fields: Custom field values
            
        Returns:
            UUID of created contact or None
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                contact_id = uuid.uuid4()
                contact = CRMContact(
                    id=contact_id,
                    tenant_id=tenant_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    company=company,
                    tags=tags or [],
                    custom_fields=custom_fields or {},
                    created_at=datetime.utcnow()
                )
                
                session.add(contact)
                await session.commit()
                
                self.logger.info(
                    "CRM contact created",
                    tenant_id=str(tenant_id),
                    contact_id=str(contact_id),
                    name=f"{first_name} {last_name}"
                )
                
                return contact_id
                
        except Exception as e:
            self.logger.error("Failed to create CRM contact", error=str(e))
            return None
    
    async def get_contact(
        self,
        contact_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get contact by ID.
        
        Args:
            contact_id: Contact UUID
            
        Returns:
            Dict with contact details or None
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    """
                    SELECT id, tenant_id, first_name, last_name, email, phone,
                           company, tags, custom_fields, created_at, updated_at
                    FROM crm_contacts
                    WHERE id = :contact_id
                    """,
                    {"contact_id": contact_id}
                )
                
                row = result.fetchone()
                
                if not row:
                    return None
                
                return {
                    "id": str(row[0]),
                    "tenant_id": str(row[1]),
                    "first_name": row[2],
                    "last_name": row[3],
                    "email": row[4],
                    "phone": row[5],
                    "company": row[6],
                    "tags": row[7],
                    "custom_fields": row[8],
                    "created_at": row[9].isoformat() if row[9] else None,
                    "updated_at": row[10].isoformat() if row[10] else None
                }
                
        except Exception as e:
            self.logger.error("Failed to get CRM contact", error=str(e))
            return None
    
    async def update_contact(
        self,
        contact_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update contact information.
        
        Args:
            contact_id: Contact UUID
            updates: Dict of fields to update
            
        Returns:
            bool: True if successful
        """
        try:
            async with get_db_session() as session:
                set_clauses = []
                params = {"contact_id": contact_id, "updated_at": datetime.utcnow()}
                
                for key, value in updates.items():
                    if key in ["first_name", "last_name", "email", "phone", "company"]:
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value
                    elif key in ["tags", "custom_fields"]:
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value
                
                if not set_clauses:
                    return False
                
                set_clauses.append("updated_at = :updated_at")
                
                query = f"""
                    UPDATE crm_contacts
                    SET {', '.join(set_clauses)}
                    WHERE id = :contact_id
                """
                
                await session.execute(query, params)
                await session.commit()
                
                self.logger.info("CRM contact updated", contact_id=str(contact_id))
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to update CRM contact", error=str(e))
            return False
    
    async def delete_contact(
        self,
        contact_id: uuid.UUID
    ) -> bool:
        """
        Delete a contact.
        
        Args:
            contact_id: Contact UUID
            
        Returns:
            bool: True if successful
        """
        try:
            async with get_db_session() as session:
                await session.execute(
                    "DELETE FROM crm_contacts WHERE id = :contact_id",
                    {"contact_id": contact_id}
                )
                await session.commit()
                
                self.logger.info("CRM contact deleted", contact_id=str(contact_id))
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to delete CRM contact", error=str(e))
            return False
    
    async def search_contacts(
        self,
        tenant_id: uuid.UUID,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search contacts.
        
        Args:
            tenant_id: Tenant UUID
            query: Search query (name, email, phone, company)
            tags: Filter by tags
            limit: Maximum results
            offset: Results offset
            
        Returns:
            List of contact dicts
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                sql = """
                    SELECT id, first_name, last_name, email, phone, company, tags, created_at
                    FROM crm_contacts
                    WHERE tenant_id = :tenant_id
                """
                params = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
                
                if query:
                    sql += """ AND (
                        first_name ILIKE :query OR
                        last_name ILIKE :query OR
                        email ILIKE :query OR
                        phone ILIKE :query OR
                        company ILIKE :query
                    )"""
                    params["query"] = f"%{query}%"
                
                if tags:
                    sql += " AND tags && :tags"
                    params["tags"] = tags
                
                sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                
                result = await session.execute(sql, params)
                
                contacts = []
                for row in result.fetchall():
                    contacts.append({
                        "id": str(row[0]),
                        "first_name": row[1],
                        "last_name": row[2],
                        "email": row[3],
                        "phone": row[4],
                        "company": row[5],
                        "tags": row[6],
                        "created_at": row[7].isoformat() if row[7] else None
                    })
                
                return contacts
                
        except Exception as e:
            self.logger.error("Failed to search CRM contacts", error=str(e))
            return []
    
    # Lead Management
    
    async def create_lead(
        self,
        tenant_id: uuid.UUID,
        contact_id: uuid.UUID,
        source: str,
        status: str = "new",
        score: int = 0,
        pipeline_stage_id: Optional[uuid.UUID] = None
    ) -> Optional[uuid.UUID]:
        """
        Create a new lead.
        
        Args:
            tenant_id: Tenant UUID
            contact_id: Associated contact UUID
            source: Lead source
            status: Lead status
            score: Lead score (0-100)
            pipeline_stage_id: Pipeline stage UUID
            
        Returns:
            UUID of created lead or None
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                lead_id = uuid.uuid4()
                lead = CRMLead(
                    id=lead_id,
                    tenant_id=tenant_id,
                    contact_id=contact_id,
                    source=source,
                    status=status,
                    score=score,
                    pipeline_stage_id=pipeline_stage_id,
                    created_at=datetime.utcnow()
                )
                
                session.add(lead)
                await session.commit()
                
                self.logger.info(
                    "CRM lead created",
                    tenant_id=str(tenant_id),
                    lead_id=str(lead_id),
                    contact_id=str(contact_id)
                )
                
                return lead_id
                
        except Exception as e:
            self.logger.error("Failed to create CRM lead", error=str(e))
            return None
    
    async def update_lead_score(
        self,
        lead_id: uuid.UUID,
        score: int
    ) -> bool:
        """
        Update lead score.
        
        Args:
            lead_id: Lead UUID
            score: New score (0-100)
            
        Returns:
            bool: True if successful
        """
        try:
            async with get_db_session() as session:
                await session.execute(
                    """
                    UPDATE crm_leads
                    SET score = :score, updated_at = :updated_at
                    WHERE id = :lead_id
                    """,
                    {"score": score, "updated_at": datetime.utcnow(), "lead_id": lead_id}
                )
                await session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to update lead score", error=str(e))
            return False
    
    # Interaction Tracking
    
    async def log_interaction(
        self,
        tenant_id: uuid.UUID,
        contact_id: uuid.UUID,
        interaction_type: str,
        subject: str,
        notes: Optional[str] = None,
        call_id: Optional[uuid.UUID] = None
    ) -> Optional[uuid.UUID]:
        """
        Log an interaction with a contact.
        
        Args:
            tenant_id: Tenant UUID
            contact_id: Contact UUID
            interaction_type: Type (call, email, meeting, note)
            subject: Interaction subject
            notes: Optional notes
            call_id: Optional associated call UUID
            
        Returns:
            UUID of created interaction or None
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                interaction_id = uuid.uuid4()
                interaction = CRMInteraction(
                    id=interaction_id,
                    tenant_id=tenant_id,
                    contact_id=contact_id,
                    interaction_type=interaction_type,
                    subject=subject,
                    notes=notes,
                    call_id=call_id,
                    interaction_date=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                
                session.add(interaction)
                await session.commit()
                
                return interaction_id
                
        except Exception as e:
            self.logger.error("Failed to log CRM interaction", error=str(e))
            return None
    
    async def get_contact_interactions(
        self,
        contact_id: uuid.UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get interaction history for a contact.
        
        Args:
            contact_id: Contact UUID
            limit: Maximum results
            
        Returns:
            List of interaction dicts
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    """
                    SELECT id, interaction_type, subject, notes, interaction_date, created_at
                    FROM crm_interactions
                    WHERE contact_id = :contact_id
                    ORDER BY interaction_date DESC
                    LIMIT :limit
                    """,
                    {"contact_id": contact_id, "limit": limit}
                )
                
                interactions = []
                for row in result.fetchall():
                    interactions.append({
                        "id": str(row[0]),
                        "interaction_type": row[1],
                        "subject": row[2],
                        "notes": row[3],
                        "interaction_date": row[4].isoformat() if row[4] else None,
                        "created_at": row[5].isoformat() if row[5] else None
                    })
                
                return interactions
                
        except Exception as e:
            self.logger.error("Failed to get contact interactions", error=str(e))
            return []
    
    # Import/Export
    
    async def import_contacts_csv(
        self,
        tenant_id: uuid.UUID,
        csv_content: str
    ) -> Dict[str, Any]:
        """
        Import contacts from CSV.
        
        Args:
            tenant_id: Tenant UUID
            csv_content: CSV file content
            
        Returns:
            Dict with import results
        """
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            imported = 0
            failed = 0
            errors = []
            
            for row in reader:
                try:
                    contact_id = await self.create_contact(
                        tenant_id=tenant_id,
                        first_name=row.get("first_name", ""),
                        last_name=row.get("last_name", ""),
                        email=row.get("email"),
                        phone=row.get("phone"),
                        company=row.get("company"),
                        tags=row.get("tags", "").split(",") if row.get("tags") else []
                    )
                    
                    if contact_id:
                        imported += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    failed += 1
                    errors.append(str(e))
            
            return {
                "imported": imported,
                "failed": failed,
                "errors": errors[:10]  # Limit error messages
            }
            
        except Exception as e:
            self.logger.error("Failed to import contacts", error=str(e))
            return {"imported": 0, "failed": 0, "errors": [str(e)]}
    
    async def export_contacts_csv(
        self,
        tenant_id: uuid.UUID
    ) -> str:
        """
        Export contacts to CSV.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            CSV content as string
        """
        try:
            contacts = await self.search_contacts(tenant_id, limit=10000)
            
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["id", "first_name", "last_name", "email", "phone", "company", "tags", "created_at"]
            )
            
            writer.writeheader()
            for contact in contacts:
                writer.writerow({
                    "id": contact["id"],
                    "first_name": contact["first_name"],
                    "last_name": contact["last_name"],
                    "email": contact["email"] or "",
                    "phone": contact["phone"] or "",
                    "company": contact["company"] or "",
                    "tags": ",".join(contact["tags"]) if contact["tags"] else "",
                    "created_at": contact["created_at"]
                })
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.error("Failed to export contacts", error=str(e))
            return ""


# Global instance
crm_service = CRMService()
