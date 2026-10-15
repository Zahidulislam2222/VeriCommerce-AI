"""CI safety gates fail on drift, unreviewed licenses, skipped tests and XML entities."""
from __future__ import annotations

import base64
import json
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from infra.ci.checks import Settings, lock_and_license_check, no_skipped_tests, runtime_config


@pytest.fixture
def config(tmp_path: Path, monkeypatch: Any) -> Settings:
    result = Settings('npm.json', 'requirements.lock', 'requirements.txt', 'dev.txt', 'NOTICES.txt',
                      'LICENSE', 'example.env', 'runtime.env', 'junit.xml', ['MIT'], 'package.json',
                      'All rights reserved.', 'UNLICENSED')
    package = {'version': '1.0.0', 'license': 'MIT',
               'integrity': 'sha512-' + base64.b64encode(bytes(64)).decode()}
    (tmp_path / result.npm_lock).write_text(json.dumps({'lockfileVersion': 3, 'packages': {
        '': {}, 'node_modules/fake-test-package': package,
    }}))
    (tmp_path / result.python_lock).write_text('fake-test-package==1.0.0 --hash=sha256:' + '0' * 64 + '\n')
    (tmp_path / result.python_direct).write_text('fake-test-package==1.0.0\n')
    (tmp_path / result.license_file).write_text('Test-only copyright. All rights reserved.\n')
    (tmp_path / result.npm_manifest).write_text(json.dumps({'license': 'UNLICENSED'}))
    (tmp_path / result.public_notices).write_text('SIL Open Font License\n' + 'test notice\n' * 100)
    info = Message()
    info['License-Expression'] = 'MIT'
    monkeypatch.setattr('infra.ci.checks.metadata.distribution', lambda _: SimpleNamespace(
        version='1.0.0', metadata=info,
    ))
    return result


def test_pinned_lock_license_inventory_passes(config: Settings, tmp_path: Path) -> None:
    assert lock_and_license_check(config, tmp_path) == {
        'npm_packages': 1, 'python_packages': 1, 'reviewed_npm_license_identifiers': 1,
    }


def test_direct_dependency_extras_match_base_package_lock(config: Settings, tmp_path: Path) -> None:
    (tmp_path / config.python_direct).write_text('fake-test-package[binary]==1.0.0\n')
    assert lock_and_license_check(config, tmp_path)['python_packages'] == 1


@pytest.mark.parametrize('change', ['missing-integrity', 'unknown-license', 'direct-version-drift'])
def test_dependency_drift_or_unreviewed_license_is_blocked(
    config: Settings, tmp_path: Path, change: str,
) -> None:
    if change == 'direct-version-drift':
        (tmp_path / config.python_direct).write_text('fake-test-package==2.0.0\n')
    else:
        lock = json.loads((tmp_path / config.npm_lock).read_text())
        package = lock['packages']['node_modules/fake-test-package']
        package['integrity' if change == 'missing-integrity' else 'license'] = 'unreviewed'
        (tmp_path / config.npm_lock).write_text(json.dumps(lock))
    with pytest.raises(ValueError):
        lock_and_license_check(config, tmp_path)


def test_installed_production_version_drift_is_blocked(
    config: Settings, tmp_path: Path, monkeypatch: Any,
) -> None:
    monkeypatch.setattr('infra.ci.checks.metadata.distribution', lambda _: SimpleNamespace(version='2.0.0'))
    with pytest.raises(ValueError, match='differs from lock'):
        lock_and_license_check(config, tmp_path)


def test_runtime_example_never_contains_administrator_or_database_credentials(
    config: Settings, tmp_path: Path,
) -> None:
    (tmp_path / config.backend_example).write_text(
        'VC_DATABASE_URL=test-only-dsn\nVC_MIGRATION_DATABASE_URL=test-only-admin-dsn\n'
        'VC_SETTINGS_FILE=test-only-file\nVC_COOKIE_SECURE=true\nVC_EMBEDDING_ENABLED=false\n'
    )
    runtime_config(config, tmp_path)
    actual = (tmp_path / config.runtime_output).read_text()
    assert actual == 'VC_COOKIE_SECURE=true\nVC_EMBEDDING_ENABLED=false\n'


@pytest.mark.parametrize('child', ['<skipped/>', '<failure/>', '<error/>'])
def test_ci_rejects_any_skipped_or_failed_case(config: Settings, tmp_path: Path, child: str) -> None:
    (tmp_path / config.pytest_report).write_text('<testsuite><testcase>' + child + '</testcase></testsuite>')
    with pytest.raises(ValueError, match='zero skips'):
        no_skipped_tests(config, tmp_path)


def test_junit_real_case_required_and_safe(config: Settings, tmp_path: Path) -> None:
    (tmp_path / config.pytest_report).write_text('<testsuite><testcase name="passed"/></testsuite>')
    assert no_skipped_tests(config, tmp_path) == {'backend_cases_executed': 1, 'skipped': 0}


def test_junit_external_entities_rejected(config: Settings, tmp_path: Path) -> None:
    from defusedxml.common import DefusedXmlException

    (tmp_path / config.pytest_report).write_text(
        '<!DOCTYPE testsuite [<!ENTITY marker "test-only">]>'
        '<testsuite><testcase>&marker;</testcase></testsuite>'
    )
    with pytest.raises(DefusedXmlException):
        no_skipped_tests(config, tmp_path)
