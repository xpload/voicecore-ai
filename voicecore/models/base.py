"""
Base models and mixins for VoiceCore AI.

Provides common functionality and patterns for all database models
including tenant isolation, timestamps, and UUID primary keys.
"""

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Create the declarative base
Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model with UUID primary key.
    
    All models inherit from this to ensure consistent
    primary key structure and basic functionality.
    """
    
    __abstract__ = True
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the record"
    )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: dict) -> None:
        """Update model instance from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


class TimestampMixin:
    """
    Mixin for adding created_at and updated_at timestamps.
    
    Automatically manages creation and update timestamps
    for all models that include this mixin.
    """
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="When the record was last updated"
    )


class TenantMixin:
    """
    Mixin for adding tenant isolation to models.
    
    Ensures all tenant-scoped models include the tenant_id
    column for Row-Level Security (RLS) policies.
    """
    
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        doc="Tenant this record belongs to"
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    
    Allows marking records as deleted without actually
    removing them from the database.
    """
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the record was soft deleted"
    )
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the record is soft deleted"
    )
    
    def soft_delete(self) -> None:
        """Mark the record as soft deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """
    Mixin for audit trail functionality.
    
    Tracks who created and last modified records
    for compliance and debugging purposes.
    """
    
    created_by = Column(
        String(255),
        nullable=True,
        doc="User who created the record"
    )
    
    updated_by = Column(
        String(255),
        nullable=True,
        doc="User who last updated the record"
    )
    
    def set_created_by(self, user_id: str) -> None:
        """Set the creator of the record."""
        self.created_by = user_id
    
    def set_updated_by(self, user_id: str) -> None:
        """Set the last updater of the record."""
        self.updated_by = user_id