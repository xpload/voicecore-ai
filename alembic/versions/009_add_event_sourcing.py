"""Add Event Sourcing and CQRS tables

Revision ID: 009_add_event_sourcing
Revises: 008_add_v2_enterprise_features
Create Date: 2026-02-10

This migration adds comprehensive Event Sourcing and CQRS infrastructure:
- EventStore: Immutable event storage for all business transactions
- EventSnapshot: Performance optimization through aggregate snapshots
- ReadModel: CQRS read-side materialized views
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision = '009_add_event_sourcing'
down_revision = '008_add_v2_enterprise_features'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add Event Sourcing and CQRS tables
    """
    
    # Create event_store table
    op.create_table(
        'event_store',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('aggregate_type', sa.String(100), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_version', sa.Integer, nullable=False, default=1),
        sa.Column('event_data', postgresql.JSONB, nullable=False),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), index=True),
        sa.Column('sequence_number', sa.Integer, nullable=False),
        sa.Column('causation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('blockchain_tx_hash', sa.String(66), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for event_store
    op.create_index('idx_aggregate_sequence', 'event_store', ['aggregate_id', 'sequence_number'])
    op.create_index('idx_event_type_timestamp', 'event_store', ['event_type', 'timestamp'])
    op.create_index('idx_tenant_timestamp', 'event_store', ['tenant_id', 'timestamp'])
    op.create_index('idx_correlation', 'event_store', ['correlation_id'])
    
    # Create event_snapshots table
    op.create_table(
        'event_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('aggregate_type', sa.String(100), nullable=False),
        sa.Column('snapshot_data', postgresql.JSONB, nullable=False),
        sa.Column('snapshot_version', sa.Integer, nullable=False),
        sa.Column('last_event_sequence', sa.Integer, nullable=False),
        sa.Column('last_event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    
    # Create index for event_snapshots
    op.create_index('idx_aggregate_snapshot', 'event_snapshots', ['aggregate_id', 'last_event_sequence'])
    
    # Create read_models table (CQRS)
    op.create_table(
        'read_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('model_type', sa.String(100), nullable=False, index=True),
        sa.Column('model_id', sa.String(255), nullable=False, index=True),
        sa.Column('data', postgresql.JSONB, nullable=False),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        sa.Column('last_event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_event_sequence', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('is_deleted', sa.Boolean, default=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for read_models
    op.create_index('idx_model_type_id', 'read_models', ['model_type', 'model_id'])
    op.create_index('idx_tenant_model', 'read_models', ['tenant_id', 'model_type'])
    
    # Add RLS policies for event_store
    op.execute("""
        ALTER TABLE event_store ENABLE ROW LEVEL SECURITY;
        
        CREATE POLICY tenant_isolation_policy ON event_store
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
        
        CREATE POLICY tenant_isolation_insert_policy ON event_store
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)
    
    # Add RLS policies for event_snapshots
    op.execute("""
        ALTER TABLE event_snapshots ENABLE ROW LEVEL SECURITY;
        
        CREATE POLICY tenant_isolation_policy ON event_snapshots
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
        
        CREATE POLICY tenant_isolation_insert_policy ON event_snapshots
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)
    
    # Add RLS policies for read_models
    op.execute("""
        ALTER TABLE read_models ENABLE ROW LEVEL SECURITY;
        
        CREATE POLICY tenant_isolation_policy ON read_models
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
        
        CREATE POLICY tenant_isolation_insert_policy ON read_models
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)
    
    # Create function to ensure sequence number uniqueness per aggregate
    op.execute("""
        CREATE OR REPLACE FUNCTION check_event_sequence()
        RETURNS TRIGGER AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM event_store
                WHERE aggregate_id = NEW.aggregate_id
                AND sequence_number = NEW.sequence_number
                AND id != NEW.id
            ) THEN
                RAISE EXCEPTION 'Duplicate sequence number % for aggregate %', 
                    NEW.sequence_number, NEW.aggregate_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER ensure_unique_sequence
            BEFORE INSERT OR UPDATE ON event_store
            FOR EACH ROW
            EXECUTE FUNCTION check_event_sequence();
    """)
    
    # Create function to auto-update read_model updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_read_model_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER update_read_model_timestamp
            BEFORE UPDATE ON read_models
            FOR EACH ROW
            EXECUTE FUNCTION update_read_model_timestamp();
    """)
    
    print("✅ Event Sourcing and CQRS tables created successfully")


def downgrade() -> None:
    """
    Remove Event Sourcing and CQRS tables
    """
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS ensure_unique_sequence ON event_store;")
    op.execute("DROP TRIGGER IF EXISTS update_read_model_timestamp ON read_models;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS check_event_sequence();")
    op.execute("DROP FUNCTION IF EXISTS update_read_model_timestamp();")
    
    # Drop tables
    op.drop_table('read_models')
    op.drop_table('event_snapshots')
    op.drop_table('event_store')
    
    print("✅ Event Sourcing and CQRS tables removed successfully")
