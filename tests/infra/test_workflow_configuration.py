"""Keep hosted browser feature flags and security fixtures explicit."""
from __future__ import annotations

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
