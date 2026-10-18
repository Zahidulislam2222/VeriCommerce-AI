"""Guard the zero-activation, IAM-only infrastructure and secret-free source boundary."""

from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path

from infra.cloud.settings import CloudSettings

ROOT = Path(__file__).resolve().parents[2]
CLOUD = ROOT / "infra/cloud"


def configuration(lane: str) -> dict:
    return json.loads((CLOUD / "tofu" / lane / "main.tf.json").read_text())


def test_cloud_configuration_has_one_typed_boundary_and_no_credentials() -> None:
    raw = json.loads((CLOUD / "config.json").read_text())
    assert set(raw) == {field.name for field in fields(CloudSettings)}
    assert CloudSettings.load() == CloudSettings(**raw)
    patterns = [
        r"AKIA[A-Z0-9]{16}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"(?i)(?:api_key|password|access_token|client_secret)\s*=\s*['\"][^'\"]{12,}",
    ]
    for path in CLOUD.glob("*.py"):
        source = path.read_text()
        assert not any(re.search(pattern, source) for pattern in patterns), path.name
        assert "os.getenv(" not in source and "os.environ[" not in source


def test_no_bundle_activates_billing_apis_or_adds_public_iam() -> None:
    prohibited = {
        "aws_lambda_function_url",
        "aws_api_gateway_rest_api",
        "aws_nat_gateway",
        "google_project_service",
        "google_billing_account_iam_member",
        "azurerm_service_plan",
        "azurerm_linux_function_app",
    }
    for lane in ["azure", "aws", "gcp"]:
        config = configuration(lane)
        assert not prohibited.intersection(config["resource"])
        assert "allUsers" not in json.dumps(config) and "allAuthenticatedUsers" not in json.dumps(config)
        versions = json.loads((CLOUD / "tofu" / lane / "versions.tf.json").read_text())
        for provider in versions["terraform"]["required_providers"].values():
            assert re.fullmatch(r"= \d+\.\d+\.\d+", provider["version"])
        assert (CLOUD / "tofu" / lane / ".terraform.lock.hcl").is_file()


def test_azure_free_only_and_no_automatic_provider_registration() -> None:
    config = configuration("azure")
    assert config["provider"]["azurerm"]["resource_provider_registrations"] == "none"
    site = config["resource"]["azurerm_static_web_app"]["shell"]
    assert site["sku_tier"] == site["sku_size"] == "Free"


def test_azure_group_creation_is_explicit_owned_metadata_only() -> None:
    config = configuration("azure")
    assert set(config["resource"]) == {"azurerm_resource_group", "azurerm_static_web_app"}
    variables = config["variable"]
    assert variables["create_resource_group"] == {"type": "bool", "default": False, "nullable": False}
    assert '^vericommerce-[a-z0-9-]+$' in variables["resource_group_name"]["validation"]["condition"]
    group = config["resource"]["azurerm_resource_group"]["owned"]
    assert group["count"] == "${var.create_resource_group ? 1 : 0}"
    site = config["resource"]["azurerm_static_web_app"]["shell"]
    assert "azurerm_resource_group.owned[0].name" in site["resource_group_name"]


def test_gcp_identity_and_cpu_caps_remain_explicit() -> None:
    config = configuration("gcp")
    resources = config["resource"]
    template = resources["google_cloud_run_v2_service"]["benchmark"]["template"][0]
    assert template["service_account"] == "${var.runtime_service_account}"
    assert template["max_instance_request_concurrency"] == 1
    assert template["scaling"] == [{"min_instance_count": 0, "max_instance_count": 1}]
    assert template["containers"][0]["resources"][0]["cpu_idle"] is True
    assert template["containers"][0]["resources"][0]["startup_cpu_boost"] is False
    service = resources["google_cloud_run_v2_service"]["benchmark"]
    assert service["deletion_protection"] == "${!var.allow_experiment_cleanup}"
    assert config["variable"]["allow_experiment_cleanup"]["default"] is False
    container = template["containers"][0]
    assert container["command"] == ["python", "-m", "uvicorn"]
    assert "--no-access-log" in container["args"]
    assert container["ports"][0]["container_port"] == "${var.container_port}"
    assert resources["google_cloud_run_v2_service_iam_member"]["invoker"]["member"].startswith(
        "serviceAccount:"
    )


def test_gcp_bootstrap_enables_only_free_prerequisites_and_owned_identity() -> None:
    config = configuration("gcp-bootstrap")
    resources = config["resource"]
    assert set(resources) == {
        "google_project_service", "google_service_account",
        "google_service_account_iam_member", "google_artifact_registry_repository",
    }
    apis = resources["google_project_service"]["prerequisites"]
    assert apis["disable_on_destroy"] is False
    assert set(re.findall(r'"([a-z]+\.googleapis\.com)"', apis["for_each"])) == {
        "iam.googleapis.com", "iamcredentials.googleapis.com",
        "run.googleapis.com", "artifactregistry.googleapis.com",
    }
    identity = resources["google_service_account_iam_member"]["operator_oidc"]
    assert identity["role"] == "roles/iam.serviceAccountOpenIdTokenCreator"
    assert identity["member"] == "${var.operator_member}"
    assert "^user:" in config["variable"]["operator_member"]["validation"]["condition"]
    repository = resources["google_artifact_registry_repository"]["synthetic"]
    assert repository["mode"] == "STANDARD_REPOSITORY"
    assert repository["vulnerability_scanning_config"] == [{"enablement_config": "DISABLED"}]
    assert "allUsers" not in json.dumps(config) and "allAuthenticatedUsers" not in json.dumps(config)


def test_cloud_hub_metadata_does_not_move_existing_resources() -> None:
    for lane in ["aws", "azure", "gcp", "gcp-bootstrap"]:
        config = configuration(lane)
        assert config["variable"]["hub_identifier"]["nullable"] is False
        assert config["variable"]["project_slug"]["nullable"] is False
        assert "moved" not in config and "import" not in config
    aws_tags = configuration("aws")["provider"]["aws"]["default_tags"][0]["tags"]
    assert aws_tags["Hub"] == "${var.hub_identifier}"
    assert aws_tags["Project"] == "${var.project_slug}"
    for lane in ["gcp", "gcp-bootstrap"]:
        assert configuration(lane)["provider"]["google"]["default_labels"] == {
            "hub": "${var.hub_identifier}", "project": "${var.project_slug}",
        }


def test_aws_validator_has_no_log_write_permissions_and_only_trusted_invoker() -> None:
    resources = configuration("aws")["resource"]
    assert not {"aws_iam_role_policy", "aws_iam_role_policy_attachment"}.intersection(resources)
    assert resources["aws_lambda_permission"]["invoker"]["principal"] == "${var.invoker_principal_arn}"
    function = resources["aws_lambda_function"]["validator"]
    assert function["reserved_concurrent_executions"] == (
        "${var.allow_unreserved_low_quota && var.account_concurrency_limit <= 10 ? -1 : 1}"
    )
    assert function["timeout"] == 3 and function["memory_size"] == 128


def test_aws_low_quota_exception_and_exact_iam_principal_are_explicit() -> None:
    config = configuration("aws")
    assert config["variable"]["allow_unreserved_low_quota"]["default"] is False
    principal = config["variable"]["invoker_principal_arn"]["validation"]["condition"]
    assert '(user|role)/' in principal and '[0-9]{12}' in principal
    lifecycle = config["resource"]["aws_lambda_function"]["validator"]["lifecycle"]
    assert lifecycle["precondition"][0]["condition"] == (
        "${!var.allow_unreserved_low_quota || var.account_concurrency_limit <= 10}"
    )


def test_minimal_cloud_runtime_contains_only_locked_http_dependencies() -> None:
    runtime = (CLOUD / "runtime-requirements.lock").read_text().splitlines()
    entries = [line for line in runtime if line and not line.startswith("#")]
    assert {line.split("==")[0] for line in entries} == {"uvicorn", "click", "h11"}
    application = (ROOT / "backend/requirements.lock").read_text().splitlines()
    assert all(entry in application for entry in entries)
    dockerfile = (CLOUD / "Dockerfile").read_text()
    assert "ARG PYTHON_IMAGE" in dockerfile and "FROM ${PYTHON_IMAGE}" in dockerfile
    assert "--require-hashes" in dockerfile and "USER 10001:10001" in dockerfile
    assert "fastembed" not in dockerfile and "huggingface" not in dockerfile
