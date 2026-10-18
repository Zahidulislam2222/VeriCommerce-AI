CREATE TABLE product_tombstones (
    tenant_id uuid NOT NULL REFERENCES demo_sessions(tenant_id) ON DELETE CASCADE,
    product_id text NOT NULL,
    deleted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,product_id),
    FOREIGN KEY(tenant_id,product_id) REFERENCES products(tenant_id,id) ON DELETE CASCADE
);
ALTER TABLE product_tombstones ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_tombstones FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_only ON product_tombstones USING
    (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
    WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
