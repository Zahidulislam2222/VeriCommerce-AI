\set ON_ERROR_STOP on
SELECT format('SELECT %L AS relation, encode(sha256(convert_to(coalesce(string_agg(to_jsonb(t)::text, chr(10) ORDER BY to_jsonb(t)::text), %L), %L)), %L) AS payload_sha256 FROM %I.%I AS t;',
              schemaname || '.' || tablename, '', 'UTF8', 'hex', schemaname, tablename)
FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename
\gexec
