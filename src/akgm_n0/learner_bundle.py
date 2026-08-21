"""Create an allowlisted filesystem bundle for a learner process."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .contracts import (
    METAMACHINE_PUBLIC_PATHS,
    OPERATION_GROWTH_PUBLIC_PATHS,
    PROJECT_ROOT,
    PUBLIC_CONTRACT_PATHS,
    RELATION_GROWTH_PUBLIC_PATHS,
)
from .leakage_audit import audit_public_contracts


class LearnerBundleError(ValueError):
    """Raised when a learner-visible bundle cannot be built safely."""


def build_learner_bundle(
    destination: Path, *, profile: str = "gen0"
) -> dict[str, Any]:
    """Copy only learner-visible contracts into a new, empty directory.

    The experiment runner will use this bundle as the learner process working
    directory. Evaluator files are excluded by construction rather than by a
    filename blacklist.
    """

    profiles = {
        "gen0": ("gen0-v0.1", PUBLIC_CONTRACT_PATHS),
        "operation_growth": ("operation-growth-v0.1", OPERATION_GROWTH_PUBLIC_PATHS),
        "metamachine": ("metamachine-gen1-v0.1", METAMACHINE_PUBLIC_PATHS),
        "relation_growth": ("relation-growth-v0.1", RELATION_GROWTH_PUBLIC_PATHS),
    }
    try:
        source_protocol, public_paths = profiles[profile]
    except KeyError as exc:
        raise LearnerBundleError(f"unknown learner bundle profile: {profile}") from exc

    destination = destination.resolve()
    if destination == PROJECT_ROOT.resolve():
        raise LearnerBundleError("Destination cannot be the project root")
    if destination.exists() and any(destination.iterdir()):
        raise LearnerBundleError("Destination must be absent or empty")

    findings = audit_public_contracts()
    if findings:
        raise LearnerBundleError(
            f"Public contracts failed leakage audit with {len(findings)} finding(s)"
        )

    destination.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    for source in public_paths:
        relative_path = source.relative_to(PROJECT_ROOT)
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        records.append(
            {
                "path": relative_path.as_posix(),
                "sha256": _sha256(target),
            }
        )

    manifest: dict[str, Any] = {
        "bundle_version": "learner-bundle-v0.1",
        "source_protocol": source_protocol,
        "allowlisted_files": records,
    }
    manifest_path = destination / "bundle_manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
