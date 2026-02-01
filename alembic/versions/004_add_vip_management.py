"""Add VIP caller management tables

Revision ID: 004_add_vip_management
Revises: 003_add_call_routing
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_vip_management'
down_revision = '003_add_call_routing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add VIP caller management tables."""
    
    # Create VIP priority enum
    vip_priority_enum = postgresql.ENUM(
        'STANDARD', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND',
        name='vippriority',
        create_type=False
    )
    vip_priority_enum.create(op.get_bind(), checkfirst=True)
    
    # Create VIP status enum
    vip_status_enum = postgresql.ENUM(
        'ACTIVE', 'INACTIVE', 'SUSPENDED', 'EXPIRED',
        name='vipstatus',
        create_type=False
    )
    vip_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create VIP caller table
    op.create_table(
        'vip_caller',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Caller identification
        sa.Column('phone_number', sa.String(255), nullable=False, index=True),
        sa.Column('caller_name', sa.String(255), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        
        # VIP configuration
        sa.Column('vip_level', vip_priority_enum, nullable=False, server_default='STANDARD'),
        sa.Column('status', vip_status_enum, nullable=False, server_default='ACTIVE'),
        
        # Handling preferences
        sa.Column('preferred_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('preferred_department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('handling_rules', postgresql.JSON, nullable=False, server_default='[]'),
        
        # Custom configurations
        sa.Column('custom_greeting', sa.Text, nullable=True),
        sa.Column('custom_hold_music', sa.String(500), nullable=True),
        sa.Column('max_wait_time', sa.Integer, nullable=False, server_default='60'),
        sa.Column('callback_priority', sa.Integer, nullable=False, server_default='1'),
        
        # Contact information
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('alternative_phone', sa.String(255), nullable=True),
        
        # Account information
        sa.Column('account_number', sa.String(100), nullable=True),
        sa.Column('account_value', sa.Float, nullable=True),
        
        # Validity and expiration
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        
        # Usage tracking
        sa.Column('total_calls', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_call_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('average_call_duration', sa.Integer, nullable=False, server_default='0'),
        sa.Column('satisfaction_score', sa.Float, nullable=True),
        
        # Notes and tags
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=False, server_default='[]'),
        
        # Metadata
        sa.Column('metadata', postgresql.JSON, nullable=False, server_default='{}'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['preferred_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['preferred_department_id'], ['departments.id'], ondelete='SET NULL'),
        
        # Indexes
        sa.Index('ix_vip_caller_tenant_phone', 'tenant_id', 'phone_number'),
        sa.Index('ix_vip_caller_tenant_status', 'tenant_id', 'status'),
        sa.Index('ix_vip_caller_tenant_level', 'tenant_id', 'vip_level'),
    )
    
    # Create VIP call history table
    op.create_table(
        'vip_call_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # References
        sa.Column('vip_caller_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # VIP-specific call details
        sa.Column('vip_level_at_call', vip_priority_enum, nullable=False),
        sa.Column('handling_rules_applied', postgresql.JSON, nullable=False, server_default='[]'),
        sa.Column('preferred_agent_available', sa.Boolean, nullable=True),
        sa.Column('routed_to_preferred', sa.Boolean, nullable=False, server_default='false'),
        
        # Service quality metrics
        sa.Column('wait_time_seconds', sa.Integer, nullable=False, server_default='0'),
        sa.Column('escalation_triggered', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('custom_greeting_used', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('satisfaction_rating', sa.Integer, nullable=True),
        sa.Column('service_quality_score', sa.Float, nullable=True),
        
        # Resolution tracking
        sa.Column('issue_resolved', sa.Boolean, nullable=True),
        sa.Column('resolution_time', sa.Integer, nullable=True),
        sa.Column('follow_up_scheduled', sa.Boolean, nullable=False, server_default='false'),
        
        # Feedback and notes
        sa.Column('caller_feedback', sa.Text, nullable=True),
        sa.Column('agent_notes', sa.Text, nullable=True),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vip_caller_id'], ['vip_caller.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        
        # Indexes
        sa.Index('ix_vip_call_history_tenant_vip', 'tenant_id', 'vip_caller_id'),
        sa.Index('ix_vip_call_history_tenant_date', 'tenant_id', 'created_at'),
    )
    
    # Create VIP escalation rules table
    op.create_table(
        'vip_escalation_rule',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Rule identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        
        # Trigger conditions
        sa.Column('vip_levels', postgresql.JSON, nullable=False, server_default='[]'),
        sa.Column('max_wait_time', sa.Integer, nullable=True),
        sa.Column('max_queue_position', sa.Integer, nullable=True),
        sa.Column('time_of_day_start', sa.String(5), nullable=True),
        sa.Column('time_of_day_end', sa.String(5), nullable=True),
        sa.Column('days_of_week', postgresql.JSON, nullable=False, server_default='[]'),
        
        # Escalation actions
        sa.Column('escalation_type', sa.String(50), nullable=False),
        sa.Column('escalation_target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notification_emails', postgresql.JSON, nullable=False, server_default='[]'),
        sa.Column('notification_message', sa.Text, nullable=True),
        
        # Rule configuration
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer, nullable=False, server_default='1'),
        
        # Usage tracking
        sa.Column('times_triggered', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        
        # Indexes
        sa.Index('ix_vip_escalation_rule_tenant_active', 'tenant_id', 'is_active'),
        sa.Index('ix_vip_escalation_rule_tenant_priority', 'tenant_id', 'priority'),
    )
    
    # Enable RLS on all VIP tables
    op.execute('ALTER TABLE vip_caller ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE vip_call_history ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE vip_escalation_rule ENABLE ROW LEVEL SECURITY')
    
    # Create RLS policies for VIP caller table
    op.execute("""
        CREATE POLICY vip_caller_tenant_isolation ON vip_caller
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY vip_caller_tenant_isolation_insert ON vip_caller
        FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Create RLS policies for VIP call history table
    op.execute("""
        CREATE POLICY vip_call_history_tenant_isolation ON vip_call_history
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY vip_call_history_tenant_isolation_insert ON vip_call_history
        FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Create RLS policies for VIP escalation rules table
    op.execute("""
        CREATE POLICY vip_escalation_rule_tenant_isolation ON vip_escalation_rule
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY vip_escalation_rule_tenant_isolation_insert ON vip_escalation_rule
        FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Add VIP-related columns to calls table
    op.add_column('calls', sa.Column('is_vip', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('calls', sa.Column('vip_caller_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('calls', sa.Column('vip_priority_score', sa.Integer, nullable=True))
    
    # Add foreign key constraint for VIP caller
    op.create_foreign_key(
        'fk_calls_vip_caller',
        'calls', 'vip_caller',
        ['vip_caller_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for VIP calls
    op.create_index('ix_calls_tenant_vip', 'calls', ['tenant_id', 'is_vip'])


def downgrade() -> None:
    """Remove VIP caller management tables."""
    
    # Remove VIP-related columns from calls table
    op.drop_constraint('fk_calls_vip_caller', 'calls', type_='foreignkey')
    op.drop_index('ix_calls_tenant_vip', 'calls')
    op.drop_column('calls', 'vip_priority_score')
    op.drop_column('calls', 'vip_caller_id')
    op.drop_column('calls', 'is_vip')
    
    # Drop VIP tables
    op.drop_table('vip_escalation_rule')
    op.drop_table('vip_call_history')
    op.drop_table('vip_caller')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS vipstatus')
    op.execute('DROP TYPE IF EXISTS vippriority')