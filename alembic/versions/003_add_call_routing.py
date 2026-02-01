"""Add call routing and queue management

Revision ID: 003_add_call_routing
Revises: 002_enhance_rls_policies
Create Date: 2024-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_call_routing'
down_revision = '002_enhance_rls_policies'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create call_queue table
    op.create_table('call_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('caller_number', sa.String(length=255), nullable=False),
        sa.Column('queue_position', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=2),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_wait_time', sa.Integer(), nullable=True),
        sa.Column('max_wait_time', sa.Integer(), nullable=False, default=300),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_call_queue_tenant_department', 'call_queue', ['tenant_id', 'department_id'])
    op.create_index('idx_call_queue_priority_position', 'call_queue', ['priority', 'queue_position'])
    op.create_index('idx_call_queue_queued_at', 'call_queue', ['queued_at'])
    op.create_index('idx_call_queue_assigned_agent', 'call_queue', ['assigned_agent_id'])
    
    # Enable RLS on call_queue table
    op.execute("ALTER TABLE call_queue ENABLE ROW LEVEL SECURITY")
    
    # Create RLS policy for call_queue
    op.execute("""
        CREATE POLICY call_queue_tenant_isolation ON call_queue
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Add routing-related columns to calls table
    op.add_column('calls', sa.Column('queue_entry_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('calls', sa.Column('routing_attempts', sa.Integer(), nullable=False, default=0))
    op.add_column('calls', sa.Column('last_routing_attempt', sa.DateTime(timezone=True), nullable=True))
    
    # Add foreign key constraint for queue_entry_id
    op.create_foreign_key('fk_calls_queue_entry', 'calls', 'call_queue', ['queue_entry_id'], ['id'], ondelete='SET NULL')
    
    # Add routing-related columns to agents table
    op.add_column('agents', sa.Column('current_calls', sa.Integer(), nullable=False, default=0))
    op.add_column('agents', sa.Column('max_concurrent_calls', sa.Integer(), nullable=False, default=1))
    op.add_column('agents', sa.Column('last_call_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agents', sa.Column('skills', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('agents', sa.Column('routing_weight', sa.Integer(), nullable=False, default=1))
    
    # Add routing strategy to departments table
    op.add_column('departments', sa.Column('routing_strategy', sa.String(50), nullable=False, default='round_robin'))
    op.add_column('departments', sa.Column('queue_timeout', sa.Integer(), nullable=False, default=300))
    op.add_column('departments', sa.Column('max_queue_size', sa.Integer(), nullable=False, default=10))
    op.add_column('departments', sa.Column('transfer_keywords', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('departments', sa.Column('priority', sa.Integer(), nullable=False, default=1))
    
    # Create indexes for new columns
    op.create_index('idx_calls_queue_entry', 'calls', ['queue_entry_id'])
    op.create_index('idx_calls_routing_attempts', 'calls', ['routing_attempts'])
    op.create_index('idx_agents_status_department', 'agents', ['status', 'department_id'])
    op.create_index('idx_agents_current_calls', 'agents', ['current_calls'])
    op.create_index('idx_departments_routing_strategy', 'departments', ['routing_strategy'])


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_departments_routing_strategy')
    op.drop_index('idx_agents_current_calls')
    op.drop_index('idx_agents_status_department')
    op.drop_index('idx_calls_routing_attempts')
    op.drop_index('idx_calls_queue_entry')
    
    # Remove columns from departments table
    op.drop_column('departments', 'priority')
    op.drop_column('departments', 'transfer_keywords')
    op.drop_column('departments', 'max_queue_size')
    op.drop_column('departments', 'queue_timeout')
    op.drop_column('departments', 'routing_strategy')
    
    # Remove columns from agents table
    op.drop_column('agents', 'routing_weight')
    op.drop_column('agents', 'skills')
    op.drop_column('agents', 'last_call_at')
    op.drop_column('agents', 'max_concurrent_calls')
    op.drop_column('agents', 'current_calls')
    
    # Remove foreign key constraint and columns from calls table
    op.drop_constraint('fk_calls_queue_entry', 'calls', type_='foreignkey')
    op.drop_column('calls', 'last_routing_attempt')
    op.drop_column('calls', 'routing_attempts')
    op.drop_column('calls', 'queue_entry_id')
    
    # Drop call_queue table indexes
    op.drop_index('idx_call_queue_assigned_agent')
    op.drop_index('idx_call_queue_queued_at')
    op.drop_index('idx_call_queue_priority_position')
    op.drop_index('idx_call_queue_tenant_department')
    
    # Drop call_queue table
    op.drop_table('call_queue')