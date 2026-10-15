CREATE TABLE IF NOT EXISTS demo_sessions (
    tenant_id uuid PRIMARY KEY,
    token_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS rate_limits (
    bucket_key text NOT NULL,
    scope text NOT NULL,
    bucket_start timestamptz NOT NULL,
    count integer NOT NULL,
    PRIMARY KEY (bucket_key, scope, bucket_start)
);
CREATE TABLE IF NOT EXISTS products (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id text NOT NULL,
    fields jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
);
CREATE TABLE IF NOT EXISTS source_revisions (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    source_id text NOT NULL,
    metadata jsonb NOT NULL,
    content_hash text NOT NULL,
    supersedes_revision_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, source_id, content_hash)
);
CREATE TABLE IF NOT EXISTS sources (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id text NOT NULL,
    current_revision_id uuid NOT NULL,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, current_revision_id) REFERENCES source_revisions(tenant_id, id)
);
CREATE TABLE IF NOT EXISTS passages (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    revision_id uuid NOT NULL,
    product_id text NOT NULL,
    label text NOT NULL,
    value text NOT NULL,
    text text NOT NULL,
    page text NOT NULL,
    position integer NOT NULL,
    embedding real[],
    embedding_revision text,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', text || ' ' || label || ' ' || value)
    ) STORED,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, revision_id) REFERENCES source_revisions(tenant_id, id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, product_id) REFERENCES products(tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS passages_fts ON passages USING gin(search_vector);
CREATE INDEX IF NOT EXISTS passages_revision ON passages(tenant_id, revision_id);
CREATE TABLE IF NOT EXISTS drafts (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    product_id text NOT NULL,
    text text NOT NULL,
    citations jsonb NOT NULL,
    source_fingerprint text NOT NULL,
    method text NOT NULL,
    status text NOT NULL CHECK(status IN ('draft','approved','stale')),
    created_at timestamptz NOT NULL DEFAULT now(),
    approved_at timestamptz,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, product_id) REFERENCES products(tenant_id, id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS jobs (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    kind text NOT NULL CHECK(kind IN ('ingest','draft')),
    status text NOT NULL CHECK(status IN ('queued','running','succeeded','failed')),
    payload jsonb NOT NULL,
    result jsonb,
    error text,
    attempts integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    lease_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(tenant_id, status, available_at);
CREATE TABLE IF NOT EXISTS audit_events (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    action text NOT NULL,
    entity_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
);
CREATE TABLE IF NOT EXISTS evaluations (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE products FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON products USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
ALTER TABLE source_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_revisions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON source_revisions USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON sources USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
ALTER TABLE passages ENABLE ROW LEVEL SECURITY;
ALTER TABLE passages FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON passages USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
ALTER TABLE drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE drafts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON drafts USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON jobs USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON audit_events USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON evaluations USING
    (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
