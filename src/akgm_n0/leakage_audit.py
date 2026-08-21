"""Evaluator-side audit for forbidden target information in public contracts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .contracts import PROJECT_ROOT, load_json_compatible_yaml


@dataclass(frozen=True)
class LeakageFinding:
    path: str
    location: str
    kind: str
    value: str


def load_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or PROJECT_ROOT / "evaluator" / "leakage_policy.json"
    with policy_path.open("r", encoding="utf-8") as stream:
        policy = json.load(stream)
    if policy.get("visibility") != "evaluator_only":
        raise ValueError("Leakage policy must be evaluator_only")
    return policy


def audit_public_contracts(
    root: Path = PROJECT_ROOT, policy_path: Path | None = None
) -> list[LeakageFinding]:
    policy = load_policy(policy_path)
    forbidden_terms = tuple(
        str(term).casefold() for term in policy["forbidden_terms_case_insensitive"]
    )
    forbidden_keys = {str(key).casefold() for key in policy["forbidden_keys"]}
    findings: list[LeakageFinding] = []

    for relative_path in policy["public_paths"]:
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(f"Public path escapes project root: {relative_path}")
        document = load_json_compatible_yaml(path)
        for location, key, value in _walk(document):
            if key is not None and key.casefold() in forbidden_keys:
                findings.append(
                    LeakageFinding(relative_path, location, "forbidden_key", key)
                )
            if isinstance(value, str):
                folded = value.casefold()
                for term in forbidden_terms:
                    if _contains_forbidden_term(folded, term):
                        findings.append(
                            LeakageFinding(relative_path, location, "forbidden_term", term)
                        )
    return findings


def _contains_forbidden_term(value: str, term: str) -> bool:
    """Match complete English words while retaining substring checks for CJK."""

    if term.isascii() and term.isalpha():
        return re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", value) is not None
    return term in value


def _walk(value: Any, location: str = "$") -> Iterable[tuple[str, str | None, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            yield child_location, str(key), child
            yield from _walk(child, child_location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_location = f"{location}[{index}]"
            yield child_location, None, child
            yield from _walk(child, child_location)
