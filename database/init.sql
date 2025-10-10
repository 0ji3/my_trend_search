-- eBay Trend Research Tool - Database Initialization Script
-- PostgreSQL 16+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET timezone = 'UTC';

-- ============================================================
-- TABLE: tenants (ユーザー)
-- ============================================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    business_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster email lookups
CREATE INDEX idx_tenants_email ON tenants(email);
CREATE INDEX idx_tenants_status ON tenants(status);

-- ============================================================
-- TABLE: oauth_credentials (OAuth認証情報)
-- ============================================================
CREATE TABLE oauth_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    access_token_encrypted BYTEA NOT NULL,
    access_token_iv BYTEA NOT NULL,
    access_token_auth_tag BYTEA NOT NULL,
    refresh_token_encrypted BYTEA NOT NULL,
    refresh_token_iv BYTEA NOT NULL,
    refresh_token_auth_tag BYTEA NOT NULL,
    access_token_expires_at TIMESTAMPTZ NOT NULL,
    refresh_token_expires_at TIMESTAMPTZ,
    scopes TEXT[] NOT NULL,
    is_valid BOOLEAN DEFAULT true,
    last_refreshed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id)
);

-- Index for token expiration checks
CREATE INDEX idx_oauth_credentials_tenant_id ON oauth_credentials(tenant_id);
CREATE INDEX idx_oauth_credentials_access_expires ON oauth_credentials(access_token_expires_at);
CREATE INDEX idx_oauth_credentials_is_valid ON oauth_credentials(is_valid);

-- ============================================================
-- TABLE: ebay_accounts (eBayアカウント)
-- ============================================================
CREATE TABLE ebay_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    oauth_credential_id UUID NOT NULL REFERENCES oauth_credentials(id) ON DELETE CASCADE,
    ebay_user_id VARCHAR(255) NOT NULL,
    account_name VARCHAR(255),
    site_id VARCHAR(10) DEFAULT 'EBAY_US',
    marketplace VARCHAR(50) DEFAULT 'US',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error')),
    last_synced_at TIMESTAMPTZ,
    sync_status VARCHAR(50) DEFAULT 'pending' CHECK (sync_status IN ('pending', 'syncing', 'completed', 'failed')),
    sync_error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, ebay_user_id)
);

-- Indexes
CREATE INDEX idx_ebay_accounts_tenant_id ON ebay_accounts(tenant_id);
CREATE INDEX idx_ebay_accounts_oauth_id ON ebay_accounts(oauth_credential_id);
CREATE INDEX idx_ebay_accounts_status ON ebay_accounts(status);
CREATE INDEX idx_ebay_accounts_last_synced ON ebay_accounts(last_synced_at);

-- ============================================================
-- TABLE: listings (出品商品)
-- ============================================================
CREATE TABLE listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES ebay_accounts(id) ON DELETE CASCADE,
    item_id VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    price DECIMAL(12, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    category_id VARCHAR(50),
    category_name VARCHAR(255),
    listing_type VARCHAR(50) DEFAULT 'FixedPriceItem',
    quantity INTEGER DEFAULT 1,
    quantity_sold INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    listing_status VARCHAR(50) DEFAULT 'Active',
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    image_url TEXT,
    gallery_url TEXT,
    view_item_url TEXT,
    item_specifics JSONB,
    condition_id VARCHAR(20),
    condition_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, item_id)
);

-- Indexes
CREATE INDEX idx_listings_account_id ON listings(account_id);
CREATE INDEX idx_listings_item_id ON listings(item_id);
CREATE INDEX idx_listings_is_active ON listings(is_active);
CREATE INDEX idx_listings_category_id ON listings(category_id);
CREATE INDEX idx_listings_listing_status ON listings(listing_status);
CREATE INDEX idx_listings_updated_at ON listings(updated_at);

-- GIN index for JSONB column
CREATE INDEX idx_listings_item_specifics ON listings USING gin(item_specifics);

-- ============================================================
-- TABLE: daily_metrics (日次メトリクス)
-- ============================================================
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    recorded_date DATE NOT NULL,
    view_count INTEGER DEFAULT 0,
    watch_count INTEGER DEFAULT 0,
    bid_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    current_price DECIMAL(12, 2),
    quantity_available INTEGER,
    quantity_sold INTEGER DEFAULT 0,
    impression_count INTEGER DEFAULT 0,
    click_through_rate DECIMAL(5, 2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(listing_id, recorded_date)
);

-- Indexes
CREATE INDEX idx_daily_metrics_listing_id ON daily_metrics(listing_id);
CREATE INDEX idx_daily_metrics_recorded_date ON daily_metrics(recorded_date);
CREATE INDEX idx_daily_metrics_listing_date ON daily_metrics(listing_id, recorded_date);

-- ============================================================
-- TABLE: trend_analysis (トレンド分析結果)
-- ============================================================
CREATE TABLE trend_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,
    view_growth_rate DECIMAL(8, 2),
    watch_growth_rate DECIMAL(8, 2),
    view_7day_avg DECIMAL(10, 2),
    watch_7day_avg DECIMAL(10, 2),
    view_30day_avg DECIMAL(10, 2),
    watch_30day_avg DECIMAL(10, 2),
    price_momentum DECIMAL(8, 2),
    trend_score DECIMAL(10, 2) NOT NULL,
    rank INTEGER,
    is_trending BOOLEAN DEFAULT false,
    trend_direction VARCHAR(20) CHECK (trend_direction IN ('up', 'down', 'stable', 'new')),
    confidence_score DECIMAL(5, 2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(listing_id, analysis_date)
);

-- Indexes
CREATE INDEX idx_trend_analysis_listing_id ON trend_analysis(listing_id);
CREATE INDEX idx_trend_analysis_date ON trend_analysis(analysis_date);
CREATE INDEX idx_trend_analysis_score ON trend_analysis(trend_score DESC);
CREATE INDEX idx_trend_analysis_is_trending ON trend_analysis(is_trending);
CREATE INDEX idx_trend_analysis_rank ON trend_analysis(rank);
CREATE INDEX idx_trend_analysis_listing_date ON trend_analysis(listing_id, analysis_date);

-- ============================================================
-- TABLE: sync_jobs (同期ジョブ管理)
-- ============================================================
CREATE TABLE sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES ebay_accounts(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('full_sync', 'incremental_sync', 'metrics_sync')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    items_processed INTEGER DEFAULT 0,
    items_total INTEGER,
    error_message TEXT,
    error_details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_sync_jobs_account_id ON sync_jobs(account_id);
CREATE INDEX idx_sync_jobs_status ON sync_jobs(status);
CREATE INDEX idx_sync_jobs_created_at ON sync_jobs(created_at DESC);

-- ============================================================
-- TABLE: notifications (通知)
-- ============================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    listing_id UUID REFERENCES listings(id) ON DELETE SET NULL,
    notification_type VARCHAR(50) NOT NULL CHECK (notification_type IN ('trend_alert', 'sync_error', 'token_expiring', 'system')),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'error', 'success')),
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_notifications_tenant_id ON notifications(tenant_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(notification_type);

-- ============================================================
-- TABLE: audit_logs (監査ログ)
-- ============================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_credentials_updated_at BEFORE UPDATE ON oauth_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ebay_accounts_updated_at BEFORE UPDATE ON ebay_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_listings_updated_at BEFORE UPDATE ON listings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sync_jobs_updated_at BEFORE UPDATE ON sync_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on tenant-specific tables
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE trend_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE ebay_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- RLS Policy for listings
CREATE POLICY tenant_isolation_policy_listings ON listings
    USING (account_id IN (
        SELECT id FROM ebay_accounts
        WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
    ));

-- RLS Policy for ebay_accounts
CREATE POLICY tenant_isolation_policy_accounts ON ebay_accounts
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- RLS Policy for notifications
CREATE POLICY tenant_isolation_policy_notifications ON notifications
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- ============================================================
-- INITIAL DATA / SEED
-- ============================================================

-- Insert system notification for welcome message (optional)
-- INSERT INTO notifications (tenant_id, notification_type, title, message, severity)
-- VALUES (
--     (SELECT id FROM tenants LIMIT 1),
--     'system',
--     'Welcome to eBay Trend Research Tool',
--     'Your account has been created successfully. Connect your eBay account to start tracking trends.',
--     'info'
-- );

-- ============================================================
-- VIEWS (Optional - for convenience)
-- ============================================================

-- View: Active listings with latest metrics
CREATE OR REPLACE VIEW active_listings_with_metrics AS
SELECT
    l.id,
    l.account_id,
    l.item_id,
    l.title,
    l.price,
    l.currency,
    l.category_name,
    l.image_url,
    l.view_item_url,
    dm.view_count AS latest_view_count,
    dm.watch_count AS latest_watch_count,
    dm.recorded_date AS latest_metric_date,
    ta.trend_score,
    ta.rank AS trend_rank,
    ta.is_trending
FROM listings l
LEFT JOIN LATERAL (
    SELECT * FROM daily_metrics
    WHERE listing_id = l.id
    ORDER BY recorded_date DESC
    LIMIT 1
) dm ON true
LEFT JOIN LATERAL (
    SELECT * FROM trend_analysis
    WHERE listing_id = l.id
    ORDER BY analysis_date DESC
    LIMIT 1
) ta ON true
WHERE l.is_active = true;

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE tenants IS 'User accounts (tenant/multi-tenant support)';
COMMENT ON TABLE oauth_credentials IS 'Encrypted eBay OAuth tokens';
COMMENT ON TABLE ebay_accounts IS 'Connected eBay seller accounts';
COMMENT ON TABLE listings IS 'eBay product listings';
COMMENT ON TABLE daily_metrics IS 'Daily performance metrics (views, watches, etc.)';
COMMENT ON TABLE trend_analysis IS 'Calculated trend scores and rankings';
COMMENT ON TABLE sync_jobs IS 'Data synchronization job tracking';
COMMENT ON TABLE notifications IS 'User notifications and alerts';
COMMENT ON TABLE audit_logs IS 'Audit trail for security and compliance';

COMMENT ON COLUMN oauth_credentials.access_token_encrypted IS 'AES-256-GCM encrypted access token';
COMMENT ON COLUMN oauth_credentials.refresh_token_encrypted IS 'AES-256-GCM encrypted refresh token';
COMMENT ON COLUMN trend_analysis.trend_score IS 'Composite score: (view_growth * 0.4) + (watch_growth * 0.4) + (price_momentum * 0.2)';

-- ============================================================
-- GRANT PERMISSIONS (adjust as needed)
-- ============================================================

-- Grant permissions to application user (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ebayuser;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ebayuser;

-- ============================================================
-- END OF INITIALIZATION SCRIPT
-- ============================================================
