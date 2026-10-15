"""Sanitized allocations, complete operator schemas and local private-value separation."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = (
    ('infra/deployment.example.json', 'infra/deployment.schema.json',
     'memory/deployment/config.json', '18180', '172.30.240.'),
    ('infra/core/deployment.example.json', 'infra/core/deployment.schema.json',
     'memory/deployment/core/config.json', '18181', '172.30.241.'),
)


@pytest.mark.parametrize('example,schema,private,port,network', EXAMPLES)
def test_examples_have_complete_schema_and_only_reserved_sample_allocations(
    example: str, schema: str, private: str, port: str, network: str,
) -> None:
    values = json.loads((ROOT / example).read_text())
    definition = json.loads((ROOT / schema).read_text())
    assert set(values) == set(definition['required']) == set(definition['properties'])
    assert str(values['loopback_port']) == port
    assert values['network_subnet'].startswith(network)
    assert values['slug'].startswith('example-')
    if 'hostname' in values:
        assert values['hostname'].endswith('.example.test')
    # Local secret values never enter this test or its output. CI has no private configs.
    actual_file = ROOT / private
    if actual_file.is_file():
        actual = json.loads(actual_file.read_text())
        for key in ('loopback_port', 'network_subnet', 'slug'):
            assert values[key] != actual[key], 'Public example must not reveal private allocation'
        if 'hostname' in values:
            assert values['hostname'] != actual['hostname'], 'Example must use a reserved domain'


@pytest.mark.parametrize('path,port,network', [
    ('infra/.env.example', '18180', '172.30.240.'),
    ('infra/core/.env.example', '18181', '172.30.241.'),
])
def test_compose_examples_use_same_sanitized_allocations(path: str, port: str, network: str) -> None:
    text = (ROOT / path).read_text()
    assert re.search(r'^LOOPBACK_PORT=' + re.escape(port) + r'$', text, re.MULTILINE)
    assert re.search(r'^NETWORK_SUBNET=' + re.escape(network), text, re.MULTILINE)
    assert not re.search(r'(?im)^[A-Z_]*(PASSWORD|TOKEN|SECRET|DATABASE_URL)[A-Z_]*=', text)
