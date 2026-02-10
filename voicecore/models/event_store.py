"""
Event Store Models for Event Sourcing
Immutable event storage for critical business transactions
"""

from sqlalchemy import Column, String, DateTime, Integer, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from voicecore.models.base import Base


class EventStore(Base):
    """
    Immutable event store for event sourcing
    All critical business transactions are stored as immutable events
    """
    __tablename__ = "event_store"
    
    # Primary identifier
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Aggregate information
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    aggregate_type = Column(String(100), nullable=False)
    
    # Event information
    event_type = Column(String(100), nullable=False)
    event_version = Column(Integer, nullable=False, default=1)
    event_data = Column(JSONB, nullable=False)
    event_metadata = Column("metadata", JSONB, default={})
    
    # Temporal information
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    sequence_number = Column(Integer, nullable=False)
    
    # Causation and correlation for distributed tracing
    causation_id = Column(UUID(as_uuid=True), nullable=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Blockchain reference for audit trail
    blockchain_tx_hash = Column(String(66), nullable=True)
    
    # Tenant isolation
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_aggregate_sequence', 'aggregate_id', 'sequence_number'),
        Index('idx_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('idx_correlation', 'correlation_id'),
    )
    
    def to_dict(self):
        """Convert event to dictionary"""
        return {
            'id': str(self.id),
            'aggregate_id': str(self.aggregate_id),
            'aggregate_type': self.aggregate_type,
            'event_type': self.event_type,
            'event_version': self.event_version,
            'event_data': self.event_data,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'sequence_number': self.sequence_number,
            'causation_id': str(self.causation_id) if self.causation_id else None,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'blockchain_tx_hash': self.blockchain_tx_hash,
            'tenant_id': str(self.tenant_id)
        }


class EventSnapshot(Base):
    """
    Snapshots of aggregate state for performance optimization
    Reduces need to replay all events from beginning
    """
    __tablename__ = "event_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    aggregate_type = Column(String(100), nullable=False)
    
    # Snapshot data
    snapshot_data = Column(JSONB, nullable=False)
    snapshot_version = Column(Integer, nullable=False)
    
    # Last event included in snapshot
    last_event_sequence = Column(Integer, nullable=False)
    last_event_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Temporal information
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Tenant isolation
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_aggregate_snapshot', 'aggregate_id', 'last_event_sequence'),
    )


class ReadModel(Base):
    """
    CQRS Read Model - Optimized for queries
    Materialized views of aggregate state
    """
    __tablename__ = "read_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Model information
    model_type = Column(String(100), nullable=False, index=True)
    model_id = Column(String(255), nullable=False, index=True)
    
    # Denormalized data optimized for reads
    data = Column(JSONB, nullable=False)
    
    # Version tracking
    version = Column(Integer, nullable=False, default=1)
    last_event_id = Column(UUID(as_uuid=True), nullable=False)
    last_event_sequence = Column(Integer, nullable=False)
    
    # Temporal information
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Tenant isolation
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Soft delete for CQRS
    is_deleted = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('idx_model_type_id', 'model_type', 'model_id'),
        Index('idx_tenant_model', 'tenant_id', 'model_type'),
    )
    
    def to_dict(self):
        """Convert read model to dictionary"""
        return {
            'id': str(self.id),
            'model_type': self.model_type,
            'model_id': self.model_id,
            'data': self.data,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tenant_id': str(self.tenant_id)
        }
