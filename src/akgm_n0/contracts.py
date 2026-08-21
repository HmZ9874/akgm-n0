"""Load learner-visible contracts without importing evaluator resources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEARNER_CONTRACT_PATH = PROJECT_ROOT / "configs" / "learner_contract.yaml"
PRIMITIVE_MANIFEST_PATH = PROJECT_ROOT / "configs" / "primitive_manifest.yaml"
PUBLIC_CONTRACT_PATHS = (LEARNER_CONTRACT_PATH, PRIMITIVE_MANIFEST_PATH)
OPERATION_GROWTH_CONTRACT_PATH = (
    PROJECT_ROOT / "configs" / "operation_growth" / "learner_contract.yaml"
)
OPERATION_GROWTH_MANIFEST_PATH = (
    PROJECT_ROOT / "configs" / "operation_growth" / "primitive_manifest.yaml"
)
OPERATION_GROWTH_PUBLIC_PATHS = (
    OPERATION_GROWTH_CONTRACT_PATH,
    OPERATION_GROWTH_MANIFEST_PATH,
)
METAMACHINE_CONTRACT_PATH = (
    PROJECT_ROOT / "configs" / "metamachine" / "learner_contract.yaml"
)
METAMACHINE_MANIFEST_PATH = (
    PROJECT_ROOT / "configs" / "metamachine" / "substrate_manifest.yaml"
)
METAMACHINE_PUBLIC_PATHS = (METAMACHINE_CONTRACT_PATH, METAMACHINE_MANIFEST_PATH)
RELATION_GROWTH_CONTRACT_PATH = (
    PROJECT_ROOT / "configs" / "relation_growth" / "learner_contract.yaml"
)
RELATION_GROWTH_MANIFEST_PATH = (
    PROJECT_ROOT / "configs" / "relation_growth" / "primitive_manifest.yaml"
)
RELATION_GROWTH_PUBLIC_PATHS = (
    RELATION_GROWTH_CONTRACT_PATH,
    RELATION_GROWTH_MANIFEST_PATH,
)


class ContractError(ValueError):
    """Raised when a public contract violates its structural requirements."""


def load_json_compatible_yaml(path: Path) -> dict[str, Any]:
    """Load the JSON-compatible YAML subset used for frozen contracts."""

    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Cannot load contract {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Contract root must be an object: {path}")
    return value


def load_learner_contract() -> dict[str, Any]:
    contract = load_json_compatible_yaml(LEARNER_CONTRACT_PATH)
    _require_public_identity(contract, "contract_id")
    return contract


def load_primitive_manifest() -> dict[str, Any]:
    manifest = load_json_compatible_yaml(PRIMITIVE_MANIFEST_PATH)
    _require_public_identity(manifest, "manifest_id")
    primitives = manifest.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        raise ContractError("Primitive manifest must declare at least one primitive")
    return manifest


def _require_public_identity(value: dict[str, Any], id_key: str) -> None:
    if value.get("visibility") != "learner_visible":
        raise ContractError("Public contract must be marked learner_visible")
    if not isinstance(value.get(id_key), str) or not value[id_key]:
        raise ContractError(f"Public contract must define {id_key}")
    if not isinstance(value.get("protocol_version"), str):
        raise ContractError("Public contract must define protocol_version")
