"""A deployment product quota must reach every application service unchanged."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from vericommerce_core.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_compose_forwards_configured_product_quota_to_api_and_worker(tmp_path: Path) -> None:
    template = (ROOT / "infra/core/compose.yaml").read_text()
    rendered = tmp_path / "compose.yaml"
    rendered.write_text(template.replace("__POSTGRES_SERVICE__", "postgres"))
    supplied = set(re.findall(r"\$\{([A-Z_]+)", template))
    environment = {key: value for key, value in os.environ.items() if key not in supplied}
    environment["MAX_PRODUCTS"] = "73"
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(ROOT / "infra/core/.env.example"),
            "-f",
            str(rendered),
            "--profile",
            "operations",
            "config",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        env=environment,
    )
    compiled = json.loads(result.stdout)
    for service in ("api", "worker", "migrate", "warmup"):
        assert compiled["services"][service]["environment"]["VC_MAX_PRODUCTS"] == "73"


def test_deployment_product_quota_schema_agrees_with_existing_typed_bounds() -> None:
    schema = json.loads((ROOT / "infra/core/deployment.schema.json").read_text())
    environment = schema["properties"]["environment"]
    assert "MAX_PRODUCTS" in environment["required"]
    pattern = environment["properties"]["MAX_PRODUCTS"]["pattern"]
    field = Settings.model_json_schema()["properties"]["max_products"]
    for value in (field["minimum"] - 1, field["minimum"], field["maximum"], field["maximum"] + 1):
        assert bool(re.fullmatch(pattern, str(value))) == (field["minimum"] <= value <= field["maximum"])
    example = json.loads((ROOT / "infra/core/deployment.example.json").read_text())
    assert re.fullmatch(pattern, example["environment"]["MAX_PRODUCTS"])
