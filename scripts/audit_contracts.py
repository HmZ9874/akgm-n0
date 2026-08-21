"""Run the Gen 0 public-contract leakage audit."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.contracts import load_learner_contract, load_primitive_manifest
from akgm_n0.leakage_audit import audit_public_contracts


def main() -> int:
    contract = load_learner_contract()
    manifest = load_primitive_manifest()
    findings = audit_public_contracts()

    print(f"Protocol: {contract['protocol_version']}")
    print(f"Learner contract: {contract['contract_id']}")
    print(f"Primitive manifest: {manifest['manifest_id']}")
    print(f"Declared primitives: {len(manifest['primitives'])}")
    if findings:
        print(f"Leakage audit: FAILED ({len(findings)} findings)")
        for finding in findings:
            print(
                f"- {finding.path} {finding.location}: "
                f"{finding.kind}={finding.value!r}"
            )
        return 1
    print("Leakage audit: PASSED (0 findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

