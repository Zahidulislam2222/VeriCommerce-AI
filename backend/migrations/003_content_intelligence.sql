ALTER TABLE jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check CHECK(kind IN ('ingest','draft','upload'));
ALTER TABLE sources ADD COLUMN generation bigint NOT NULL DEFAULT 1;
ALTER TABLE jobs ADD COLUMN source_generations jsonb NOT NULL DEFAULT '{}';

CREATE TABLE evidence_uploads (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    product_id text NOT NULL,
    source_id text NOT NULL,
    filename text NOT NULL,
    media_type text NOT NULL,
    content_hash text NOT NULL,
    content bytea NOT NULL,
    metadata jsonb NOT NULL,
    source_generation bigint NOT NULL DEFAULT 0,
    deleted_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,id),
    UNIQUE(tenant_id,product_id,source_id,content_hash),
    FOREIGN KEY(tenant_id,product_id) REFERENCES products(tenant_id,id) ON DELETE CASCADE
);
CREATE TABLE image_reviews (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    upload_id uuid NOT NULL,
    product_id text NOT NULL,
    purpose text NOT NULL CHECK(purpose IN ('decorative','functional','informative')),
    observation text NOT NULL,
    alt text NOT NULL,
    function text NOT NULL,
    approved boolean NOT NULL DEFAULT false,
    approved_by uuid,
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,id),
    FOREIGN KEY(tenant_id,upload_id) REFERENCES evidence_uploads(tenant_id,id),
    FOREIGN KEY(tenant_id,product_id) REFERENCES products(tenant_id,id) ON DELETE CASCADE
);
CREATE TABLE knowledge_relations (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    subject_id text NOT NULL,
    predicate text NOT NULL CHECK(predicate IN ('compatible_with','documented_by','has_variant','supported_by')),
    object_id text NOT NULL,
    revision_id uuid NOT NULL,
    status text NOT NULL CHECK(status IN ('candidate','approved','stale')),
    approved_by uuid,
    valid_from timestamptz NOT NULL DEFAULT now(),
    valid_to timestamptz,
    PRIMARY KEY(tenant_id,id),
    FOREIGN KEY(tenant_id,revision_id) REFERENCES source_revisions(tenant_id,id)
);
CREATE TABLE source_tombstones (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    source_id text NOT NULL,
    deleted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,source_id)
);
CREATE TABLE benchmark_runs (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,id)
);
CREATE TABLE benchmark_reviews (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    dataset_hash text NOT NULL,
    question_ids jsonb NOT NULL,
    image_ids jsonb NOT NULL,
    decision text NOT NULL CHECK(decision IN ('approved','needs_changes')),
    notes text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,id)
);

ALTER TABLE evidence_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_uploads FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON evidence_uploads USING
    (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
    WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE image_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON image_reviews USING
    (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
    WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE knowledge_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_relations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON knowledge_relations USING
    (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
    WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE source_tombstones ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_tombstones FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON source_tombstones USING
    (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
    WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE benchmark_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON benchmark_runs USING
    (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
    WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE benchmark_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON benchmark_reviews USING
    (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
    WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
