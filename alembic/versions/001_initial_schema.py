"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create custom types
    op.execute("CREATE TYPE agent_status AS ENUM ('available', 'busy', 'not_available')")
    op.execute("CREATE TYPE call_status AS ENUM ('initiated', 'ringing', 'in_progress', 'on_hold', 'transferred', 'completed', 'failed', 'no_answer', 'busy', 'cancelled')")
    op.execute("CREATE TYPE call_direction AS ENUM ('inbound', 'outbound')")
    op.execute("CREATE TYPE call_type AS ENUM ('customer', 'sales', 'support', 'spam', 'internal', 'vip', 'emergency')")
    op.execute("CREATE TYPE knowledge_category AS ENUM ('general', 'company_info', 'services', 'policies', 'procedures', 'faq', 'troubleshooting', 'emergency')")
    op.execute("CREATE TYPE metric_type AS ENUM ('call_volume', 'call_duration', 'agent_performance', 'ai_performance', 'customer_satisfaction', 'system_performance', 'spam_detection', 'cost_tracking')")
    
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('subdomain', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('plan_type', sa.String(length=50), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('monthly_credit_limit', sa.Integer(), nullable=False),
        sa.Column('current_usage', sa.Integer(), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=False),
        sa.Column('twilio_phone_number', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain'),
        sa.UniqueConstraint('subdomain')
    )
    
    # Enable RLS on tenants
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    
    # Create tenant_settings table
    op.create_table('tenant_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_name', sa.String(length=100), nullable=False),
        sa.Column('ai_gender', sa.String(length=10), nullable=False),
        sa.Column('ai_voice_id', sa.String(length=50), nullable=False),
        sa.Column('ai_personality', sa.Text(), nullable=True),
        sa.Column('company_description', sa.Text(), nullable=True),
        sa.Column('company_services', sa.JSON(), nullable=False),
        sa.Column('max_transfer_attempts', sa.Integer(), nullable=False),
        sa.Column('default_department', sa.String(length=100), nullable=False),
        sa.Column('business_hours_start', sa.String(length=5), nullable=False),
        sa.Column('business_hours_end', sa.String(length=5), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('business_days', sa.JSON(), nullable=False),
        sa.Column('enable_spam_detection', sa.Boolean(), nullable=False),
        sa.Column('enable_call_recording', sa.Boolean(), nullable=False),
        sa.Column('enable_transcription', sa.Boolean(), nullable=False),
        sa.Column('enable_emotion_detection', sa.Boolean(), nullable=False),
        sa.Column('enable_vip_handling', sa.Boolean(), nullable=False),
        sa.Column('primary_language', sa.String(length=10), nullable=False),
        sa.Column('supported_languages', sa.JSON(), nullable=False),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('afterhours_message', sa.Text(), nullable=True),
        sa.Column('voicemail_message', sa.Text(), nullable=True),
        sa.Column('transfer_rules', sa.JSON(), nullable=False),
        sa.Column('spam_keywords', sa.JSON(), nullable=False),
        sa.Column('vip_phone_numbers', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id')
    )
    
    # Enable RLS on tenant_settings
    op.execute("ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY")
    
    # Create departments table
    op.create_table('departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('max_queue_size', sa.Integer(), nullable=False),
        sa.Column('queue_timeout', sa.Integer(), nullable=False),
        sa.Column('transfer_keywords', sa.JSON(), nullable=False),
        sa.Column('business_hours', sa.JSON(), nullable=False),
        sa.Column('voicemail_enabled', sa.Boolean(), nullable=False),
        sa.Column('voicemail_greeting', sa.String(length=500), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('routing_strategy', sa.String(length=50), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CreateIndex('ix_departments_tenant_id', ['tenant_id'])
    )
    
    # Enable RLS on departments
    op.execute("ALTER TABLE departments ENABLE ROW LEVEL SECURITY")
    
    # Create agents table
    op.create_table('agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('extension', sa.String(length=10), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_manager', sa.Boolean(), nullable=False),
        sa.Column('manager_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('available', 'busy', 'not_available', name='agent_status'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_status_change', sa.DateTime(timezone=True), nullable=True),
        sa.Column('work_schedule', sa.JSON(), nullable=False),
        sa.Column('is_afterhours', sa.Boolean(), nullable=False),
        sa.Column('max_concurrent_calls', sa.Integer(), nullable=False),
        sa.Column('auto_answer', sa.Boolean(), nullable=False),
        sa.Column('skills', sa.JSON(), nullable=False),
        sa.Column('languages', sa.JSON(), nullable=False),
        sa.Column('total_calls_handled', sa.Integer(), nullable=False),
        sa.Column('average_call_duration', sa.Integer(), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['manager_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CreateIndex('ix_agents_tenant_id', ['tenant_id'])
    )
    
    # Enable RLS on agents
    op.execute("ALTER TABLE agents ENABLE ROW LEVEL SECURITY")
    
    # Create calls table
    op.create_table('calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('twilio_call_sid', sa.String(length=255), nullable=False),
        sa.Column('twilio_parent_call_sid', sa.String(length=255), nullable=True),
        sa.Column('from_number', sa.String(length=20), nullable=False),
        sa.Column('to_number', sa.String(length=20), nullable=False),
        sa.Column('caller_name', sa.String(length=255), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('initiated', 'ringing', 'in_progress', 'on_hold', 'transferred', 'completed', 'failed', 'no_answer', 'busy', 'cancelled', name='call_status'), nullable=False),
        sa.Column('direction', sa.Enum('inbound', 'outbound', name='call_direction'), nullable=False),
        sa.Column('call_type', sa.Enum('customer', 'sales', 'support', 'spam', 'internal', 'vip', 'emergency', name='call_type'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=False),
        sa.Column('talk_time', sa.Integer(), nullable=False),
        sa.Column('wait_time', sa.Integer(), nullable=False),
        sa.Column('ai_handled', sa.Boolean(), nullable=False),
        sa.Column('ai_duration', sa.Integer(), nullable=False),
        sa.Column('ai_transfer_attempts', sa.Integer(), nullable=False),
        sa.Column('ai_resolution_attempted', sa.Boolean(), nullable=False),
        sa.Column('call_quality_score', sa.Float(), nullable=True),
        sa.Column('customer_satisfaction', sa.Integer(), nullable=True),
        sa.Column('recording_url', sa.String(length=500), nullable=True),
        sa.Column('recording_duration', sa.Integer(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('transcript_confidence', sa.Float(), nullable=True),
        sa.Column('detected_language', sa.String(length=10), nullable=True),
        sa.Column('spam_score', sa.Float(), nullable=False),
        sa.Column('spam_reasons', sa.JSON(), nullable=False),
        sa.Column('is_blocked', sa.Boolean(), nullable=False),
        sa.Column('is_vip', sa.Boolean(), nullable=False),
        sa.Column('priority_level', sa.Integer(), nullable=False),
        sa.Column('emotion_detected', sa.String(length=50), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('escalation_triggered', sa.Boolean(), nullable=False),
        sa.Column('resolution_status', sa.String(length=50), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('follow_up_required', sa.Boolean(), nullable=False),
        sa.Column('callback_requested', sa.Boolean(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('cost_cents', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twilio_call_sid'),
        sa.CreateIndex('ix_calls_tenant_id', ['tenant_id'])
    )
    
    # Enable RLS on calls
    op.execute("ALTER TABLE calls ENABLE ROW LEVEL SECURITY")
    
    # Create knowledge_base table
    op.create_table('knowledge_base',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category', sa.Enum('general', 'company_info', 'services', 'policies', 'procedures', 'faq', 'troubleshooting', 'emergency', name='knowledge_category'), nullable=False),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('confidence_threshold', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_approved', sa.Boolean(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('context_conditions', sa.JSON(), nullable=False),
        sa.Column('department_specific', sa.Boolean(), nullable=False),
        sa.Column('departments', sa.JSON(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('success_rate', sa.Float(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('alternative_questions', sa.JSON(), nullable=False),
        sa.Column('keywords', sa.JSON(), nullable=False),
        sa.Column('follow_up_questions', sa.JSON(), nullable=False),
        sa.Column('related_entries', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CreateIndex('ix_knowledge_base_tenant_id', ['tenant_id'])
    )
    
    # Enable RLS on knowledge_base
    op.execute("ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY")
    
    # Create spam_rules table
    op.create_table('spam_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('pattern', sa.Text(), nullable=False),
        sa.Column('is_regex', sa.Boolean(), nullable=False),
        sa.Column('case_sensitive', sa.Boolean(), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('response_message', sa.Text(), nullable=True),
        sa.Column('apply_to_numbers', sa.JSON(), nullable=False),
        sa.Column('exclude_numbers', sa.JSON(), nullable=False),
        sa.Column('time_conditions', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_global', sa.Boolean(), nullable=False),
        sa.Column('match_count', sa.Integer(), nullable=False),
        sa.Column('false_positive_count', sa.Integer(), nullable=False),
        sa.Column('last_matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('auto_learn', sa.Boolean(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CreateIndex('ix_spam_rules_tenant_id', ['tenant_id'])
    )
    
    # Enable RLS on spam_rules
    op.execute("ALTER TABLE spam_rules ENABLE ROW LEVEL SECURITY")
    
    # Create RLS policies
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(tenant_uuid UUID)
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_tenant', tenant_uuid::text, true);
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create RLS policies for all tenant-scoped tables
    tables_with_rls = [
        'tenant_settings', 'departments', 'agents', 'calls', 
        'knowledge_base', 'spam_rules'
    ]
    
    for table in tables_with_rls:
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant')::UUID);
        """)


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('spam_rules')
    op.drop_table('knowledge_base')
    op.drop_table('calls')
    op.drop_table('agents')
    op.drop_table('departments')
    op.drop_table('tenant_settings')
    op.drop_table('tenants')
    
    # Drop custom types
    op.execute("DROP TYPE IF EXISTS metric_type")
    op.execute("DROP TYPE IF EXISTS knowledge_category")
    op.execute("DROP TYPE IF EXISTS call_type")
    op.execute("DROP TYPE IF EXISTS call_direction")
    op.execute("DROP TYPE IF EXISTS call_status")
    op.execute("DROP TYPE IF EXISTS agent_status")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS set_tenant_context(UUID)")