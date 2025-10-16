"""Final database schema with all tables

Revision ID: 20251016_final
Revises:
Create Date: 2025-10-16 15:22:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251016_final'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('business_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create oauth_credentials table (multi-account support)
    op.create_table('oauth_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_token_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('access_token_iv', sa.LargeBinary(), nullable=False),
        sa.Column('access_token_auth_tag', sa.LargeBinary(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('refresh_token_iv', sa.LargeBinary(), nullable=False),
        sa.Column('refresh_token_auth_tag', sa.LargeBinary(), nullable=False),
        sa.Column('access_token_expires_at', sa.DateTime(), nullable=False),
        sa.Column('refresh_token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_oauth_credentials_tenant_id', 'oauth_credentials', ['tenant_id'], unique=False)

    # Create ebay_accounts table
    op.create_table('ebay_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('oauth_credential_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ebay_user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('marketplace_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['oauth_credential_id'], ['oauth_credentials.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ebay_accounts_ebay_user_id', 'ebay_accounts', ['ebay_user_id'], unique=False)
    op.create_index('ix_ebay_accounts_tenant_id', 'ebay_accounts', ['tenant_id'], unique=False)

    # Create listings table
    op.create_table('listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('listing_status', sa.String(), nullable=False),
        sa.Column('listing_type', sa.String(), nullable=True),
        sa.Column('category_id', sa.String(), nullable=True),
        sa.Column('category_name', sa.String(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('listing_url', sa.String(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['ebay_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_listings_account_id', 'listings', ['account_id'], unique=False)
    op.create_index('ix_listings_item_id', 'listings', ['item_id'], unique=False)

    # Create daily_metrics table
    op.create_table('daily_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recorded_date', sa.Date(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False),
        sa.Column('watch_count', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('quantity_available', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('listing_id', 'recorded_date', name='uq_daily_metrics_listing_date')
    )
    op.create_index('ix_daily_metrics_listing_id', 'daily_metrics', ['listing_id'], unique=False)
    op.create_index('ix_daily_metrics_recorded_date', 'daily_metrics', ['recorded_date'], unique=False)

    # Create trend_analysis table
    op.create_table('trend_analysis',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_date', sa.Date(), nullable=False),
        sa.Column('trend_score', sa.Float(), nullable=False),
        sa.Column('view_growth_rate', sa.Float(), nullable=False),
        sa.Column('watch_growth_rate', sa.Float(), nullable=False),
        sa.Column('price_momentum', sa.Float(), nullable=False),
        sa.Column('avg_daily_views', sa.Float(), nullable=False),
        sa.Column('avg_daily_watches', sa.Float(), nullable=False),
        sa.Column('is_trending', sa.Boolean(), nullable=False),
        sa.Column('trend_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('listing_id', 'analysis_date', name='uq_trend_analysis_listing_date')
    )
    op.create_index('ix_trend_analysis_analysis_date', 'trend_analysis', ['analysis_date'], unique=False)
    op.create_index('ix_trend_analysis_is_trending', 'trend_analysis', ['is_trending'], unique=False)
    op.create_index('ix_trend_analysis_listing_id', 'trend_analysis', ['listing_id'], unique=False)

    # Create analytics_metrics table
    op.create_table('analytics_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recorded_date', sa.Date(), nullable=False),
        sa.Column('click_through_rate', sa.Float(), nullable=True),
        sa.Column('impression_count', sa.Integer(), nullable=True),
        sa.Column('click_count', sa.Integer(), nullable=True),
        sa.Column('conversion_rate', sa.Float(), nullable=True),
        sa.Column('transaction_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('listing_id', 'recorded_date', name='uq_analytics_metrics_listing_date')
    )
    op.create_index('ix_analytics_metrics_listing_id', 'analytics_metrics', ['listing_id'], unique=False)
    op.create_index('ix_analytics_metrics_recorded_date', 'analytics_metrics', ['recorded_date'], unique=False)

    # Create sync_logs table
    op.create_table('sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('items_synced', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['ebay_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_logs_account_id', 'sync_logs', ['account_id'], unique=False)
    op.create_index('ix_sync_logs_started_at', 'sync_logs', ['started_at'], unique=False)
    op.create_index('ix_sync_logs_status', 'sync_logs', ['status'], unique=False)
    op.create_index('ix_sync_logs_sync_type', 'sync_logs', ['sync_type'], unique=False)


def downgrade() -> None:
    op.drop_table('sync_logs')
    op.drop_table('analytics_metrics')
    op.drop_table('trend_analysis')
    op.drop_table('daily_metrics')
    op.drop_table('listings')
    op.drop_table('ebay_accounts')
    op.drop_table('oauth_credentials')
    op.drop_table('tenants')
