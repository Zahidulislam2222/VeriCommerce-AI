\set ON_ERROR_STOP on
SELECT format('SELECT %L AS relation, count(*)::bigint AS rows FROM %I.%I;',
              schemaname || '.' || tablename, schemaname, tablename)
FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename
\gexec
