"""Add credit system and billing models

Revision ID: 007_add_credit_system
Revises: 006_add_security_models
Create Date: 2024-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_credit_system'
down_revision = '006_add_security_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add credit system and billing tables."""
    
    # Create credit_plans table
    op.create_table(
        'credit_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('monthly_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overage_rate', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0.0'),
        sa.Column('max_agents', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_concurrent_calls', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_storage_gb', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('features', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('monthly_price', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('setup_fee', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create tenant_subscriptions table
    op.create_table(
        'tenant_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('credit_plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ends_at', sa.DateTime(), nullable=True),
        sa.Column('billing_cycle', sa.String(length=20), nullable=False, server_default='monthly'),
        sa.Column('next_billing_date', sa.DateTime(), nullable=False),
        sa.Column('custom_monthly_credits', sa.Integer(), nullable=True),
        sa.Column('custom_overage_rate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('custom_features', sa.JSON(), nullable=True),
        sa.Column('payment_method_id', sa.String(length=100), nullable=True),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['credit_plan_id'], ['credit_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create credit_usage table
    op.create_table(
        'credit_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('usage_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('credits_consumed', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0.0'),
        sa.Column('total_cost', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('usage_date', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['tenant_subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create credit_balances table
    op.create_table(
        'credit_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allocated_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('remaining_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overage_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overage_cost', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('suspension_reason', sa.String(length=100), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['tenant_subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id')
    )
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('subscription_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('overage_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('paid_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('payment_date', sa.DateTime(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('payment_reference', sa.String(length=100), nullable=True),
        sa.Column('issued_date', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('line_items', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['tenant_subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number')
    )
    
    # Create payment_transactions table
    op.create_table(
        'payment_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('payment_processor', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('payment_method_type', sa.String(length=50), nullable=True),
        sa.Column('payment_method_details', sa.JSON(), nullable=True),
        sa.Column('processor_response', sa.JSON(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    
    # Create credit_alerts table
    op.create_table(
        'credit_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='info'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('threshold_percentage', sa.Integer(), nullable=True),
        sa.Column('current_usage', sa.Integer(), nullable=True),
        sa.Column('credit_limit', sa.Integer(), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('delivery_methods', sa.JSON(), nullable=True),
        sa.Column('delivery_status', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tenant_subscriptions
    op.create_index('idx_tenant_subscription_tenant', 'tenant_subscriptions', ['tenant_id'])
    op.create_index('idx_tenant_subscription_status', 'tenant_subscriptions', ['status'])
    op.create_index('idx_tenant_subscription_billing', 'tenant_subscriptions', ['next_billing_date'])
    
    # Create indexes for credit_usage
    op.create_index('idx_credit_usage_tenant', 'credit_usage', ['tenant_id'])
    op.create_index('idx_credit_usage_subscription', 'credit_usage', ['subscription_id'])
    op.create_index('idx_credit_usage_date', 'credit_usage', ['usage_date'])
    op.create_index('idx_credit_usage_type', 'credit_usage', ['usage_type'])
    
    # Create indexes for credit_balances
    op.create_index('idx_credit_balance_tenant', 'credit_balances', ['tenant_id'])
    op.create_index('idx_credit_balance_period', 'credit_balances', ['period_start', 'period_end'])
    
    # Create indexes for invoices
    op.create_index('idx_invoice_tenant', 'invoices', ['tenant_id'])
    op.create_index('idx_invoice_subscription', 'invoices', ['subscription_id'])
    op.create_index('idx_invoice_status', 'invoices', ['status'])
    op.create_index('idx_invoice_due_date', 'invoices', ['due_date'])
    
    # Create indexes for payment_transactions
    op.create_index('idx_payment_transaction_tenant', 'payment_transactions', ['tenant_id'])
    op.create_index('idx_payment_transaction_invoice', 'payment_transactions', ['invoice_id'])
    op.create_index('idx_payment_transaction_status', 'payment_transactions', ['status'])
    op.create_index('idx_payment_transaction_processor', 'payment_transactions', ['payment_processor'])
    
    # Create indexes for credit_alerts
    op.create_index('idx_credit_alert_tenant', 'credit_alerts', ['tenant_id'])
    op.create_index('idx_credit_alert_type', 'credit_alerts', ['alert_type'])
    op.create_index('idx_credit_alert_severity', 'credit_alerts', ['severity'])
    op.create_index('idx_credit_alert_acknowledged', 'credit_alerts', ['is_acknowledged'])
    
    # Add RLS policies for all tables
    
    # Enable RLS on all tables
    op.execute("ALTER TABLE credit_plans ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE credit_usage ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE credit_balances ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payment_transactions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE credit_alerts ENABLE ROW LEVEL SECURITY")
    
    # Credit plans - accessible to all (public catalog)
    op.execute("""
        CREATE POLICY credit_plans_select_policy ON credit_plans
        FOR SELECT USING (is_active = true)
    """)
    
    # Tenant subscriptions - tenant isolation
    op.execute("""
        CREATE POLICY tenant_subscriptions_tenant_isolation ON tenant_subscriptions
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Credit usage - tenant isolation
    op.execute("""
        CREATE POLICY credit_usage_tenant_isolation ON credit_usage
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Credit balances - tenant isolation
    op.execute("""
        CREATE POLICY credit_balances_tenant_isolation ON credit_balances
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Invoices - tenant isolation
    op.execute("""
        CREATE POLICY invoices_tenant_isolation ON invoices
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Payment transactions - tenant isolation
    op.execute("""
        CREATE POLICY payment_transactions_tenant_isolation ON payment_transactions
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Credit alerts - tenant isolation
    op.execute("""
        CREATE POLICY credit_alerts_tenant_isolation ON credit_alerts
        FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)
    
    # Insert default credit plans
    op.execute("""
        INSERT INTO credit_plans (id, name, description, monthly_credits, overage_rate, max_agents, max_concurrent_calls, max_storage_gb, features, monthly_price, setup_fee)
        VALUES 
        (gen_random_uuid(), 'Starter', 'Basic plan for small businesses', 1000, 0.01, 5, 3, 1, '{"ai_training": false, "analytics": true, "emotion_detection": false}', 29.99, 0.00),
        (gen_random_uuid(), 'Professional', 'Advanced plan for growing businesses', 5000, 0.008, 15, 10, 5, '{"ai_training": true, "analytics": true, "emotion_detection": true}', 99.99, 0.00),
        (gen_random_uuid(), 'Enterprise', 'Full-featured plan for large organizations', 20000, 0.005, 50, 25, 20, '{"ai_training": true, "analytics": true, "emotion_detection": true, "priority_support": true}', 299.99, 99.99)
    """)


def downgrade() -> None:
    """Remove credit system and billing tables."""
    
    # Drop indexes
    op.drop_index('idx_credit_alert_acknowledged', table_name='credit_alerts')
    op.drop_index('idx_credit_alert_severity', table_name='credit_alerts')
    op.drop_index('idx_credit_alert_type', table_name='credit_alerts')
    op.drop_index('idx_credit_alert_tenant', table_name='credit_alerts')
    
    op.drop_index('idx_payment_transaction_processor', table_name='payment_transactions')
    op.drop_index('idx_payment_transaction_status', table_name='payment_transactions')
    op.drop_index('idx_payment_transaction_invoice', table_name='payment_transactions')
    op.drop_index('idx_payment_transaction_tenant', table_name='payment_transactions')
    
    op.drop_index('idx_invoice_due_date', table_name='invoices')
    op.drop_index('idx_invoice_status', table_name='invoices')
    op.drop_index('idx_invoice_subscription', table_name='invoices')
    op.drop_index('idx_invoice_tenant', table_name='invoices')
    
    op.drop_index('idx_credit_balance_period', table_name='credit_balances')
    op.drop_index('idx_credit_balance_tenant', table_name='credit_balances')
    
    op.drop_index('idx_credit_usage_type', table_name='credit_usage')
    op.drop_index('idx_credit_usage_date', table_name='credit_usage')
    op.drop_index('idx_credit_usage_subscription', table_name='credit_usage')
    op.drop_index('idx_credit_usage_tenant', table_name='credit_usage')
    
    op.drop_index('idx_tenant_subscription_billing', table_name='tenant_subscriptions')
    op.drop_index('idx_tenant_subscription_status', table_name='tenant_subscriptions')
    op.drop_index('idx_tenant_subscription_tenant', table_name='tenant_subscriptions')
    
    # Drop tables
    op.drop_table('credit_alerts')
    op.drop_table('payment_transactions')
    op.drop_table('invoices')
    op.drop_table('credit_balances')
    op.drop_table('credit_usage')
    op.drop_table('tenant_subscriptions')
    op.drop_table('credit_plans')