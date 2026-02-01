"""Add callback request system tables

Revision ID: 005_add_callback_system
Revises: 004_add_vip_management
Create Date: 2024-01-01 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_callback_system'
down_revision = '004_add_vip_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add callback request system tables."""
    
    # Create callback status enum
    callback_status_enum = postgresql.ENUM(
        'PENDING', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED', 'EXPIRED',
        name='callbackstatus',
        create_type=False
    )
    callback_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create callback priority enum
    callback_priority_enum = postgresql.ENUM(
        'LOW', 'NORMAL', 'HIGH', 'URGENT', 'VIP',
        name='callbackpriority',
        create_type=False
    )
    callback_priority_enum.create(op.get_bind(), checkfirst=True)
    
    # Create callback type enum
    callback_type_enum = postgresql.ENUM(
        'GENERAL', 'SALES', 'SUPPORT', 'TECHNICAL', 'BILLING', 'COMPLAINT', 'FOLLOW_UP',
        name='callbacktype',
        create_type=False
    )
    callback_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create callback request table
    op.create_table(
        'callback_request',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Original call reference
        sa.Column('original_call_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Caller information
        sa.Column('caller_number', sa.String(255), nullable=False, index=True),
        sa.Column('caller_name', sa.String(255), nullable=True),
        sa.Column('caller_email', sa.String(255), nullable=True),
        
        # Callback details
        sa.Column('callback_reason', sa.Text, nullable=True),
        sa.Column('callback_type', callback_type_enum, nullable=False, server_default='GENERAL'),
        sa.Column('priority', callback_priority_enum, nullable=False, server_default='NORMAL'),
        
        # Scheduling
        sa.Column('requested_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_window_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_window_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True),
        
        # Assignment and routing
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('preferred_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Status and tracking
        sa.Column('status', callback_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('attempts', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer, nullable=False, server_default='3'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        
        # Completion tracking
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        
        # Outcome and feedback
        sa.Column('outcome', sa.String(100), nullable=True),
        sa.Column('caller_satisfaction', sa.Integer, nullable=True),
        sa.Column('resolution_achieved', sa.Boolean, nullable=True),
        sa.Column('follow_up_required', sa.Boolean, nullable=False, server_default='false'),
        
        # Notes and metadata
        sa.Column('agent_notes', sa.Text, nullable=True),
        sa.Column('system_notes', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSON, nullable=False, server_default='{}'),
        
        # Notification settings
        sa.Column('sms_notifications', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('email_notifications', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('notification_sent', sa.Boolean, nullable=False, server_default='false'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['original_call_id'], ['calls.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['completion_call_id'], ['calls.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['preferred_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        
        # Indexes
        sa.Index('ix_callback_request_tenant_status', 'tenant_id', 'status'),
        sa.Index('ix_callback_request_tenant_priority', 'tenant_id', 'priority'),
        sa.Index('ix_callback_request_tenant_scheduled', 'tenant_id', 'scheduled_time'),
        sa.Index('ix_callback_request_tenant_next_attempt', 'tenant_id', 'next_attempt_at'),
    )
    
    # Create callback schedule table
    op.create_table(
        'callback_schedule',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Schedule identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        
        # Scope
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Time configuration
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('business_hours_start', sa.String(5), nullable=False, server_default='09:00'),
        sa.Column('business_hours_end', sa.String(5), nullable=False, server_default='17:00'),
        sa.Column('business_days', postgresql.JSON, nullable=False, server_default='["monday", "tuesday", "wednesday", "thursday", "friday"]'),
        
        # Capacity limits
        sa.Column('max_callbacks_per_hour', sa.Integer, nullable=False, server_default='10'),
        sa.Column('max_callbacks_per_day', sa.Integer, nullable=False, server_default='50'),
        sa.Column('callback_duration_minutes', sa.Integer, nullable=False, server_default='15'),
        
        # Scheduling rules
        sa.Column('min_advance_minutes', sa.Integer, nullable=False, server_default='30'),
        sa.Column('max_advance_days', sa.Integer, nullable=False, server_default='7'),
        sa.Column('allow_same_day', sa.Boolean, nullable=False, server_default='true'),
        
        # Configuration
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer, nullable=False, server_default='1'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        
        # Indexes
        sa.Index('ix_callback_schedule_tenant_active', 'tenant_id', 'is_active'),
        sa.Index('ix_callback_schedule_tenant_dept', 'tenant_id', 'department_id'),
        sa.Index('ix_callback_schedule_tenant_agent', 'tenant_id', 'agent_id'),
    )
    
    # Create callback attempt table
    op.create_table(
        'callback_attempt',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # References
        sa.Column('callback_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_number', sa.Integer, nullable=False),
        
        # Attempt details
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('attempted_by_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Call details
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=False),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        
        # Results
        sa.Column('caller_reached', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('issue_resolved', sa.Boolean, nullable=True),
        sa.Column('follow_up_needed', sa.Boolean, nullable=False, server_default='false'),
        
        # Notes and feedback
        sa.Column('agent_notes', sa.Text, nullable=True),
        sa.Column('caller_feedback', sa.Text, nullable=True),
        
        # Technical details
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('retry_recommended', sa.Boolean, nullable=False, server_default='true'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['callback_request_id'], ['callback_request.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attempted_by_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='SET NULL'),
        
        # Indexes
        sa.Index('ix_callback_attempt_tenant_request', 'tenant_id', 'callback_request_id'),
        sa.Index('ix_callback_attempt_tenant_date', 'tenant_id', 'attempted_at'),
        
        # Unique constraint for attempt number per callback request
        sa.UniqueConstraint('callback_request_id', 'attempt_number', name='uq_callback_attempt_number'),
    )
    
    # Enable RLS on all callback tables
    op.execute('ALTER TABLE callback_request ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE callback_schedule ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE callback_attempt ENABLE ROW LEVEL SECURITY')
    
    # Create RLS policies for callback request table
    op.execute("""
        CREATE POLICY callback_request_tenant_isolation ON callback_request
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY callback_request_tenant_isolation_insert ON callback_request
        FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Create RLS policies for callback schedule table
    op.execute("""
        CREATE POLICY callback_schedule_tenant_isolation ON callback_schedule
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY callback_schedule_tenant_isolation_insert ON callback_schedule
        FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Create RLS policies for callback attempt table
    op.execute("""
        CREATE POLICY callback_attempt_tenant_isolation ON callback_attempt
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY callback_attempt_tenant_isolation_insert ON callback_attempt
        FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Add callback-related columns to calls table
    op.add_column('calls', sa.Column('is_callback', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('calls', sa.Column('callback_request_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint for callback request
    op.create_foreign_key(
        'fk_calls_callback_request',
        'calls', 'callback_request',
        ['callback_request_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for callback calls
    op.create_index('ix_calls_tenant_callback', 'calls', ['tenant_id', 'is_callback'])


def downgrade() -> None:
    """Remove callback request system tables."""
    
    # Remove callback-related columns from calls table
    op.drop_constraint('fk_calls_callback_request', 'calls', type_='foreignkey')
    op.drop_index('ix_calls_tenant_callback', 'calls')
    op.drop_column('calls', 'callback_request_id')
    op.drop_column('calls', 'is_callback')
    
    # Drop callback tables
    op.drop_table('callback_attempt')
    op.drop_table('callback_schedule')
    op.drop_table('callback_request')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS callbacktype')
    op.execute('DROP TYPE IF EXISTS callbackpriority')
    op.execute('DROP TYPE IF EXISTS callbackstatus')