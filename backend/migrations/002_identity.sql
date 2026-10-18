ALTER TABLE demo_sessions ADD COLUMN mode text NOT NULL DEFAULT 'demo' CHECK(mode IN ('demo','merchant'));
ALTER TABLE demo_sessions ADD COLUMN name text NOT NULL DEFAULT 'Fictional sandbox';
CREATE TABLE accounts (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE memberships (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    role text NOT NULL CHECK(role IN ('owner','reviewer','editor','viewer')),
    PRIMARY KEY(tenant_id,account_id)
);
CREATE TABLE account_sessions (
    token_hash text PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    active_tenant_id uuid REFERENCES demo_sessions(tenant_id) ON DELETE SET NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX account_sessions_expiry ON account_sessions(expires_at);
CREATE TABLE shopify_bindings (
    shop text PRIMARY KEY,
    tenant_id uuid NOT NULL UNIQUE REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    installed_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'connected'
);
CREATE TABLE shopify_connections (
    tenant_id uuid PRIMARY KEY REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    shop text NOT NULL UNIQUE,
    shop_id text NOT NULL,
    encrypted_tokens text,
    scopes jsonb NOT NULL,
    token_expires_at timestamptz,
    status text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE shopify_oauth_states (
    state_hash text PRIMARY KEY,
    browser_hash text NOT NULL,
    session_hash text NOT NULL REFERENCES account_sessions(token_hash) ON DELETE CASCADE,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    shop text NOT NULL,
    expires_at timestamptz NOT NULL
);
CREATE TABLE shopify_receipts (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    event_id text NOT NULL,
    topic text NOT NULL,
    body_hash text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    event_at timestamptz NOT NULL,
    status text NOT NULL,
    PRIMARY KEY(tenant_id,event_id)
);
CREATE TABLE shopify_records (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    product_id text NOT NULL,
    payload jsonb NOT NULL,
    event_at timestamptz NOT NULL,
    deleted boolean NOT NULL DEFAULT false,
    PRIMARY KEY(tenant_id,product_id)
);
CREATE TABLE shopify_syncs (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    status text NOT NULL,
    products integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,id)
);
ALTER TABLE shopify_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopify_connections FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON shopify_connections USING
 (tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE shopify_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopify_receipts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON shopify_receipts USING
 (tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE shopify_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopify_records FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON shopify_records USING
 (tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE shopify_syncs ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopify_syncs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON shopify_syncs USING
 (tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id = nullif(current_setting('app.tenant_id',true),'')::uuid);
