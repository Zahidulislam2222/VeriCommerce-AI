ALTER TABLE demo_sessions ADD COLUMN last_worker_scan_at timestamptz;
CREATE INDEX demo_sessions_worker_scan ON demo_sessions(last_worker_scan_at NULLS FIRST, created_at, tenant_id);
