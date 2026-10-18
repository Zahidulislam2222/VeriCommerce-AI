"""Local synthetic adapters and non-destructive authenticated backup operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backup import decrypt_file, encrypt_file, regular, retention_plan
from .benchmark import Benchmark
from .package import package_container, package_lambda, package_static
from .settings import CloudSettings
from .validator import load_json, validate_archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("archive", type=Path)
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("request", type=Path)
    for name in ("package-lambda", "package-static", "package-container"):
        package = commands.add_parser(name)
        package.add_argument("destination", type=Path)
    for name in ("encrypt", "decrypt"):
        command = commands.add_parser(name)
        command.add_argument("source", type=Path)
        command.add_argument("destination", type=Path)
        command.add_argument("--key-file", type=Path, required=True)
    retention = commands.add_parser("retention-plan")
    retention.add_argument("directory", type=Path)
    arguments = parser.parse_args()
    settings = CloudSettings.load(arguments.config)
    if arguments.command == "validate":
        result = validate_archive(regular(arguments.archive, settings.max_archive_bytes), settings)
    elif arguments.command == "benchmark":
        engine = Benchmark(settings, Path(__file__).parent)
        result = engine.query(load_json(regular(arguments.request, settings.max_archive_bytes)))
    elif arguments.command == "package-lambda":
        result = package_lambda(arguments.destination, settings)
    elif arguments.command == "package-static":
        result = package_static(arguments.destination, settings)
    elif arguments.command == "package-container":
        result = package_container(arguments.destination, settings)
    elif arguments.command == "encrypt":
        result = encrypt_file(arguments.source, arguments.destination, arguments.key_file, settings)
    elif arguments.command == "decrypt":
        result = decrypt_file(arguments.source, arguments.destination, arguments.key_file, settings)
    else:
        result = retention_plan(arguments.directory, settings)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
