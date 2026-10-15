"""Local and CI lock, license metadata, runtime-config and no-skips checks."""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    npm_lock: str
    python_lock: str
    python_direct: str
    python_development: str
    public_notices: str
    license_file: str
    backend_example: str
    runtime_output: str
    pytest_report: str
    allowed_npm_licenses: list[str]
    npm_manifest: str
    project_license_marker: str
    project_package_license: str

    @classmethod
    def load(cls, root: Path = ROOT) -> Settings:
        values = json.loads((root / 'infra/ci/config.json').read_text())
        config = cls(**values)
        for key, value in values.items():
            if key in {'allowed_npm_licenses', 'project_license_marker', 'project_package_license'}:
                continue
            if not isinstance(value, str) or not (root / value).resolve().is_relative_to(root.resolve()):
                raise ValueError('CI paths must remain within this project')
        if (not config.allowed_npm_licenses
                or len(set(config.allowed_npm_licenses)) != len(config.allowed_npm_licenses)):
            raise ValueError('Expected unique explicit license metadata identifiers')
        return config


def pinned_requirements(path: Path, hashes: bool = False) -> dict[str, str]:
    requirements: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        pattern = r'([A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_,.-]+\])?==([A-Za-z0-9_.+-]+)'
        if hashes:
            pattern += r' --hash=sha256:[a-f0-9]{64}'
        match = re.fullmatch(pattern, line.strip())
        if not match:
            raise ValueError('Expected exact pinned requirement' + (' with a wheel hash' if hashes else ''))
        name = re.sub(r'[-_.]+', '-', match[1]).lower()
        if name in requirements:
            raise ValueError('Duplicate dependency pin')
        requirements[name] = match[2]
    if not requirements:
        raise ValueError('Dependency lock must not be empty')
    return requirements


def lock_and_license_check(config: Settings, root: Path = ROOT) -> dict[str, int]:
    lock = json.loads((root / config.npm_lock).read_text())
    if lock.get('lockfileVersion') != 3:
        raise ValueError('Expected npm lockfile version3')
    licenses = set(config.allowed_npm_licenses)
    count = 0
    for name, package in lock['packages'].items():
        if not name:
            continue
        if package.get('license') not in licenses:
            raise ValueError('Unreviewed npm license metadata: ' + name)
        integrity = package.get('integrity', '')
        try:
            valid_hash = integrity.startswith('sha512-') and len(
                base64.b64decode(integrity.removeprefix('sha512-'), validate=True)
            ) == 64
        except (ValueError, binascii.Error):
            valid_hash = False
        if not valid_hash:
            raise ValueError('Missing npm registry integrity: ' + name)
        count += 1
    if config.project_license_marker not in (root / config.license_file).read_text():
        raise ValueError('Project license must match the owner-selected license policy')
    project = json.loads((root / config.npm_manifest).read_text())
    if project.get('license') != config.project_package_license:
        raise ValueError('Package license metadata must match the owner-selected policy')
    notices = (root / config.public_notices).read_text()
    if 'SIL Open Font License' not in notices or len(notices) < 1000:
        raise ValueError('Bundled third-party/font license texts are required')
    production = pinned_requirements(root / config.python_lock, hashes=True)
    direct = pinned_requirements(root / config.python_direct)
    if any(production.get(name) != version for name, version in direct.items()):
        raise ValueError('Direct Python requirements differ from the hash lock')
    for name, version in production.items():
        installed = metadata.distribution(name)
        if installed.version != version:
            raise ValueError('Installed production dependency differs from lock: ' + name)
        info = installed.metadata
        license_metadata = info.get('License-Expression') or info.get('License') or any(
            line.startswith('License ::') for line in info.get_all('Classifier', [])
        )
        if not license_metadata:
            declared = {Path(value).name for value in info.get_all('License-File', [])}
            for file in installed.files or []:
                if Path(str(file)).name not in declared:
                    continue
                license_path = Path(str(installed.locate_file(file)))
                if license_path.is_file() and license_path.stat().st_size > 0:
                    license_metadata = True
                    break
        if not license_metadata:
            raise ValueError('Missing Python license metadata requires manual review: ' + name)
    # Metadata/completeness gate, not a legal certification or a license change.
    return {'npm_packages': count, 'python_packages': len(production),
            'reviewed_npm_license_identifiers': len(licenses)}


def runtime_config(config: Settings, root: Path = ROOT) -> None:
    output = root / config.runtime_output
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for line in (root / config.backend_example).read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        key, _, value = line.partition('=')
        if re.search(r'PASSWORD|SECRET|TOKEN|DATABASE_URL|SETTINGS_FILE', key):
            continue
        if not re.fullmatch(r'VC_[A-Z0-9_]+', key):
            raise ValueError('Unexpected backend example variable')
        lines.append(key + '=' + value)
    output.write_text('\n'.join(lines) + '\n')


def no_skipped_tests(config: Settings, root: Path = ROOT) -> dict[str, int]:
    from defusedxml.ElementTree import parse

    report = parse(root / config.pytest_report, forbid_dtd=True).getroot()
    cases = list(report.iter('testcase'))
    if not cases or any(case.find('skipped') is not None or case.find('failure') is not None
                        or case.find('error') is not None for case in cases):
        raise ValueError('CI requires actual backend tests with zero skips/failures/errors')
    return {'backend_cases_executed': len(cases), 'skipped': 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('check', choices=('locks', 'runtime-config', 'no-skips', 'bandit-requirement'))
    args = parser.parse_args()
    config = Settings.load()
    if args.check == 'locks':
        print(json.dumps(lock_and_license_check(config)))
    elif args.check == 'runtime-config':
        runtime_config(config)
        print('CI runtime example prepared without database or authentication credentials.')
    elif args.check == 'no-skips':
        print(json.dumps(no_skipped_tests(config)))
    else:
        text = (ROOT / config.python_development).read_text()
        matches = re.findall(r'^bandit==([A-Za-z0-9_.+-]+)$', text, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError('Exactly one authoritative Bandit pin is required')
        print('bandit==' + matches[0])


if __name__ == '__main__':
    main()
