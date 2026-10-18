"""OAuth credentials must not enter the project proxy access/error logs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_nginx_logs_only_method_path_status_and_suppresses_raw_error_context() -> None:
    source = (ROOT / "infra/core/nginx.conf").read_text()
    assert "log_format safe_request '$request_method $uri $status';" in source
    assert "access_log /dev/stdout safe_request;" in source
    assert "error_log /dev/null;" in source
    assert "add_header Referrer-Policy no-referrer always;" in source
    assert "$request " not in source and "$args" not in source and "$http_referer" not in source


def test_uvicorn_access_logging_disabled_for_oauth_queries() -> None:
    source = (ROOT / "infra/core/compose.yaml").read_text()
    api = source.split("  api:\n", 1)[1].split("  worker:\n", 1)[0]
    assert "--no-access-log" in api


def test_project_gateway_discards_access_and_handles_proxy_errors_without_debug() -> None:
    source = (ROOT / "infra/core/site.caddy.template").read_text()
    assert "output discard" in source
    assert "handle_errors {" in source
    assert 'respond "Upstream unavailable" {err.status_code}' in source
    assert source.count("header Referrer-Policy no-referrer") == 2
    assert "debug" not in source
    assert "{err.message}" not in source and "{uri}" not in source
