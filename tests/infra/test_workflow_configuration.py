"""Keep hosted browser feature flags and security fixtures explicit."""
from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_hosted_browser_job_enables_the_hero_video_it_exercises() -> None:
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert workflow['jobs']['application']['env']['VITE_HERO_VIDEO'] == 'true'
    # No developer-local .env file exists on a clean hosted checkout.
    steps = workflow['jobs']['application']['steps']
    assert any('npm run test:browser' in step.get('run', '') for step in steps)


def test_insecure_cookie_override_stays_out_of_backend_security_test_environment() -> None:
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    job = workflow['jobs']['application']
    assert 'VC_COOKIE_SECURE' not in job['env']
    launch = next(step['run'] for step in job['steps'] if 'VC_COOKIE_SECURE=false' in step.get('run', ''))
    assert 'VC_COOKIE_SECURE=false python -m uvicorn' in launch


def test_hosted_browser_exercises_the_built_production_artifact() -> None:
    """Request-count contracts must run against the same React mode as deployment."""
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    steps = workflow['jobs']['application']['steps']
    browser_index = next(i for i, step in enumerate(steps) if 'npm run test:browser' in step.get('run', ''))
    launch = steps[browser_index]['run']
    assert 'npm run preview --' in launch
    assert 'npm run dev --' not in launch
    assert any('npm run build' in step.get('run', '') for step in steps[:browser_index])


def test_hosted_quality_audits_every_runtime_pin_before_integration_tests() -> None:
    """Current advisory lookup must fail closed instead of checking a fixed version floor."""
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    steps = workflow['jobs']['application']['steps']
    audits = [(i, step) for i, step in enumerate(steps) if 'python -m pip_audit' in step.get('run', '')]
    assert len(audits) == 1
    index, audit = audits[0]
    command = shlex.split(audit['run'])
    assert command[:7] == ['python', '-m', 'pip_audit', '-r', 'backend/build-requirements.lock',
                          '-r', 'backend/requirements.lock']
    assert command[7:] == ['--require-hashes', '--disable-pip', '--strict', '--progress-spinner', 'off']
    assert not audit.get('continue-on-error') and 'if' not in audit
    assert any('python -m pytest' in step.get('run', '') for step in steps[index + 1:])
    tools = (ROOT / '.github/ci-requirements.txt').read_text()
    assert re.search(r'^pip-audit==[0-9]+\.[0-9]+\.[0-9]+$', tools, re.MULTILINE)


def test_one_hash_locked_installer_is_build_only_and_shared_by_container_and_ci() -> None:
    """A build-tool update must reach every builder without adding runtime tooling."""
    lock = ROOT / 'backend/build-requirements.lock'
    entries = [line for line in lock.read_text().splitlines() if line and not line.startswith('#')]
    assert len(entries) == 1
    assert re.fullmatch(r'pip==[0-9]+\.[0-9]+(?:\.[0-9]+)? --hash=sha256:[a-f0-9]{64}', entries[0])
    assert not re.search(r'^pip==', (ROOT / 'backend/requirements.lock').read_text(), re.MULTILINE)
    for name in ('core', 'cloud'):
        docker = (ROOT / 'infra' / name / 'Dockerfile').read_text()
        assert 'ARG PYTHON_IMAGE\nFROM ${PYTHON_IMAGE}' in docker
        assert not re.search(r'pip==[0-9]', docker)
        assert 'build-requirements.lock' in docker
        bootstrap = docker.index('-r build-requirements.lock')
        runtime = docker.index('-r requirements.lock')
        check = docker.index('python -m pip check')
        remove = docker.index('python -m pip uninstall --yes pip')
        assert bootstrap < runtime < check < remove
        assert 'sysconfig.get_path' in docker and 'ensurepip' in docker
    for filename, job in [('ci.yml', 'application'), ('security.yml', 'secret-and-code')]:
        workflow = yaml.safe_load((ROOT / '.github/workflows' / filename).read_text())
        commands = [line.strip() for step in workflow['jobs'][job]['steps']
                    for line in step.get('run', '').splitlines()
                    if line.strip().startswith('python -m pip install ')]
        assert commands and shlex.split(commands[0])[-2:] == ['-r', 'backend/build-requirements.lock']
        assert '--require-hashes' in commands[0] and '--only-binary=:all:' in commands[0]
        assert not any(re.search(r'pip==[0-9]', command) for command in commands)


def test_one_os_patch_lock_and_helper_reach_both_builders_before_python_install() -> None:
    import json
    lock = json.loads((ROOT / 'backend/os-requirements.lock').read_text())
    assert len(lock['packages']) == 1
    package = lock['packages'][0]
    for name in ('core', 'cloud'):
        docker = (ROOT / 'infra' / name / 'Dockerfile').read_text()
        assert 'os-requirements.lock' in docker and 'build_os.py' in docker
        os_patch = docker.index('python build_os.py --lock os-requirements.lock --execute')
        assert os_patch < docker.index('python -m pip install')
        assert package['version'] not in docker and package['sha256'] not in docker
        assert 'apt-get upgrade' not in docker
