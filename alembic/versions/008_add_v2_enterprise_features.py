"""Add VoiceCore AI 2.0 enterprise features

Revision ID: 008_add_v2_enterprise_features
Revises: 007_add_credit_system
Create Date: 2024-02-07 12:00:00.000000

Adds AI Personality, CRM, and enhanced analytics models for v2.0
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_add_v2_enterprise_features'
down_revision = '007_add_credit_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add v2.0 enterprise feature tables."""
    
    # ========== AI PERSONALITY TABLES ==========
    
    # Create ai_personalities table
    op.create_table(
        'ai_personalities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('voice_settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('supported_languages', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('conversation_style', sa.Text(), nullable=False),
        sa.Column('greeting_message', sa.Text(), nullable=True),
        sa.Column('fallback_message', sa.Text(), nullable=True),
        sa.Column('transfer_message', sa.Text(), nullable=True),
        sa.Column('knowledge_base', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('company_info', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('faq_data', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('training_data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('fine_tuning_model_id', sa.String(length=100), nullable=True),
        sa.Column('training_status', sa.String(length=50), nullable=False, server_default='not_trained'),
        sa.Column('last_trained_at', sa.DateTime(), nullable=True),
        sa.Column('max_conversation_turns', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('confidence_threshold', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('enable_sentiment_analysis', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('enable_emotion_detection', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('total_conversations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_resolutions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_satisfaction_score', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    
    # Create conversation_templates table
    op.create_table(
        'conversation_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_personality_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('intent', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('trigger_phrases', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('response_template', sa.Text(), nullable=False),
        sa.Column('follow_up_questions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('required_information', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requires_confirmation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('actions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('escalation_rules', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ai_personality_id'], ['ai_personalities.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create ai_training_sessions table
    op.create_table(
        'ai_training_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_personality_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('training_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('training_data_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('training_data_source', sa.String(length=100), nullable=True),
        sa.Column('training_parameters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('model_id', sa.String(length=100), nullable=True),
        sa.Column('performance_metrics', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('improvement_percentage', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ai_personality_id'], ['ai_personalities.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create ai_feedback table
    op.create_table(
        'ai_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_personality_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conversation_id', sa.String(length=100), nullable=True),
        sa.Column('message_id', sa.String(length=100), nullable=True),
        sa.Column('feedback_type', sa.String(length=50), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('user_message', sa.Text(), nullable=True),
        sa.Column('ai_response', sa.Text(), nullable=True),
        sa.Column('expected_response', sa.Text(), nullable=True),
        sa.Column('provided_by', sa.String(length=100), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ai_personality_id'], ['ai_personalities.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    
    # ========== CRM TABLES ==========
    
    # Create crm_contacts table
    op.create_table(
        'crm_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('mobile', sa.String(length=20), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('job_title', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('lead_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='new'),
        sa.Column('lifecycle_stage', sa.String(length=50), nullable=False, server_default='lead'),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('campaign', sa.String(length=100), nullable=True),
        sa.Column('referrer', sa.String(length=255), nullable=True),
        sa.Column('total_interactions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_interaction_date', sa.DateTime(), nullable=True),
        sa.Column('first_interaction_date', sa.DateTime(), nullable=True),
        sa.Column('preferred_contact_method', sa.String(length=50), nullable=True),
        sa.Column('preferred_language', sa.String(length=10), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('custom_fields', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('linkedin_url', sa.String(length=255), nullable=True),
        sa.Column('twitter_handle', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_vip', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('do_not_call', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('do_not_email', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create crm_pipelines table
    op.create_table(
        'crm_pipelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('total_leads', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create crm_pipeline_stages table
    op.create_table(
        'crm_pipeline_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('stage_type', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('probability', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('leads_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_time_in_stage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['pipeline_id'], ['crm_pipelines.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    
    # Create crm_leads table
    op.create_table(
        'crm_leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('estimated_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('probability', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expected_close_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('is_qualified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('campaign', sa.String(length=100), nullable=True),
        sa.Column('won_date', sa.DateTime(), nullable=True),
        sa.Column('lost_date', sa.DateTime(), nullable=True),
        sa.Column('lost_reason', sa.String(length=255), nullable=True),
        sa.Column('actual_value', sa.Integer(), nullable=True),
        sa.Column('last_activity_date', sa.DateTime(), nullable=True),
        sa.Column('next_follow_up_date', sa.DateTime(), nullable=True),
        sa.Column('custom_fields', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ),
        sa.ForeignKeyConstraint(['pipeline_id'], ['crm_pipelines.id'], ),
        sa.ForeignKeyConstraint(['stage_id'], ['crm_pipeline_stages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create crm_interactions table
    op.create_table(
        'crm_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('interaction_date', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('outcome', sa.String(length=100), nullable=True),
        sa.Column('sentiment', sa.String(length=50), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['crm_leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create crm_activities table
    op.create_table(
        'crm_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(), nullable=True),
        sa.Column('completed_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='planned'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('outcome', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['crm_leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    
    # ========== CREATE INDEXES ==========
    
    # AI Personality indexes
    op.create_index('idx_ai_personality_tenant', 'ai_personalities', ['tenant_id'])
    op.create_index('idx_ai_personality_active', 'ai_personalities', ['is_active'])
    op.create_index('idx_ai_personality_default', 'ai_personalities', ['tenant_id', 'is_default'])
    
    op.create_index('idx_conversation_template_personality', 'conversation_templates', ['ai_personality_id'])
    op.create_index('idx_conversation_template_intent', 'conversation_templates', ['intent'])
    op.create_index('idx_conversation_template_active', 'conversation_templates', ['is_active'])
    
    op.create_index('idx_ai_training_personality', 'ai_training_sessions', ['ai_personality_id'])
    op.create_index('idx_ai_training_status', 'ai_training_sessions', ['status'])
    op.create_index('idx_ai_training_type', 'ai_training_sessions', ['training_type'])
    
    op.create_index('idx_ai_feedback_personality', 'ai_feedback', ['ai_personality_id'])
    op.create_index('idx_ai_feedback_type', 'ai_feedback', ['feedback_type'])
    op.create_index('idx_ai_feedback_processed', 'ai_feedback', ['is_processed'])
    
    # CRM indexes
    op.create_index('idx_crm_contact_tenant', 'crm_contacts', ['tenant_id'])
    op.create_index('idx_crm_contact_email', 'crm_contacts', ['email'])
    op.create_index('idx_crm_contact_phone', 'crm_contacts', ['phone'])
    op.create_index('idx_crm_contact_status', 'crm_contacts', ['status'])
    op.create_index('idx_crm_contact_score', 'crm_contacts', ['lead_score'])
    op.create_index('idx_crm_contact_name', 'crm_contacts', ['first_name', 'last_name'])
    
    op.create_index('idx_crm_pipeline_tenant', 'crm_pipelines', ['tenant_id'])
    op.create_index('idx_crm_pipeline_active', 'crm_pipelines', ['is_active'])
    
    op.create_index('idx_crm_stage_pipeline', 'crm_pipeline_stages', ['pipeline_id'])
    op.create_index('idx_crm_stage_order', 'crm_pipeline_stages', ['pipeline_id', 'order'])
    
    op.create_index('idx_crm_lead_tenant', 'crm_leads', ['tenant_id'])
    op.create_index('idx_crm_lead_contact', 'crm_leads', ['contact_id'])
    op.create_index('idx_crm_lead_pipeline', 'crm_leads', ['pipeline_id'])
    op.create_index('idx_crm_lead_stage', 'crm_leads', ['stage_id'])
    op.create_index('idx_crm_lead_status', 'crm_leads', ['status'])
    op.create_index('idx_crm_lead_owner', 'crm_leads', ['owner_id'])
    
    op.create_index('idx_crm_interaction_tenant', 'crm_interactions', ['tenant_id'])
    op.create_index('idx_crm_interaction_contact', 'crm_interactions', ['contact_id'])
    op.create_index('idx_crm_interaction_type', 'crm_interactions', ['interaction_type'])
    op.create_index('idx_crm_interaction_date', 'crm_interactions', ['interaction_date'])
    
    op.create_index('idx_crm_activity_tenant', 'crm_activities', ['tenant_id'])
    op.create_index('idx_crm_activity_lead', 'crm_activities', ['lead_id'])
    op.create_index('idx_crm_activity_type', 'crm_activities', ['activity_type'])
    op.create_index('idx_crm_activity_status', 'crm_activities', ['status'])
    op.create_index('idx_crm_activity_assigned', 'crm_activities', ['assigned_to'])
    op.create_index('idx_crm_activity_due', 'crm_activities', ['due_date'])

    
    # ========== ENABLE ROW LEVEL SECURITY ==========
    
    # Enable RLS on AI Personality tables
    op.execute("ALTER TABLE ai_personalities ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE conversation_templates ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_training_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_feedback ENABLE ROW LEVEL SECURITY")
    
    # Enable RLS on CRM tables
    op.execute("ALTER TABLE crm_contacts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE crm_pipelines ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE crm_pipeline_stages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE crm_leads ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE crm_interactions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE crm_activities ENABLE ROW LEVEL SECURITY")
    
    # Create RLS policies for tenant isolation
    
    # AI Personality policies
    op.execute("""
        CREATE POLICY ai_personalities_tenant_isolation ON ai_personalities
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY conversation_templates_tenant_isolation ON conversation_templates
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY ai_training_sessions_tenant_isolation ON ai_training_sessions
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY ai_feedback_tenant_isolation ON ai_feedback
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # CRM policies
    op.execute("""
        CREATE POLICY crm_contacts_tenant_isolation ON crm_contacts
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY crm_pipelines_tenant_isolation ON crm_pipelines
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY crm_pipeline_stages_tenant_isolation ON crm_pipeline_stages
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY crm_leads_tenant_isolation ON crm_leads
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY crm_interactions_tenant_isolation ON crm_interactions
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    op.execute("""
        CREATE POLICY crm_activities_tenant_isolation ON crm_activities
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)


def downgrade() -> None:
    """Remove v2.0 enterprise feature tables."""
    
    # Drop CRM tables
    op.drop_table('crm_activities')
    op.drop_table('crm_interactions')
    op.drop_table('crm_leads')
    op.drop_table('crm_pipeline_stages')
    op.drop_table('crm_pipelines')
    op.drop_table('crm_contacts')
    
    # Drop AI Personality tables
    op.drop_table('ai_feedback')
    op.drop_table('ai_training_sessions')
    op.drop_table('conversation_templates')
    op.drop_table('ai_personalities')
