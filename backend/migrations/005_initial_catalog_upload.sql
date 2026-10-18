ALTER TABLE evidence_uploads ALTER COLUMN product_id DROP NOT NULL;
ALTER TABLE evidence_uploads ADD CONSTRAINT upload_content_identity
    UNIQUE NULLS NOT DISTINCT (tenant_id,product_id,source_id,content_hash);
