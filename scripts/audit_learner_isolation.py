"""Run the static learner/evaluator isolation audit."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.isolation_audit import (
    EVALUATOR_PACKAGE,
    LEARNER_PACKAGE,
    LEARNER_SHARED_ALLOWLIST,
    audit_learner_isolation,
    build_project_import_graph,
)


def main() -> int:
    modules, _graph = build_project_import_graph()
    learner_count = sum(
        1
        for name in modules
        if name == LEARNER_PACKAGE or name.startswith(LEARNER_PACKAGE + ".")
    )
    evaluator_count = sum(
        1 for name in modules if name.startswith(EVALUATOR_PACKAGE)
    )
    print(f"Learner modules audited: {learner_count}")
    print(f"Evaluator modules present: {evaluator_count}")
    print(f"Shared allowlist: {sorted(LEARNER_SHARED_ALLOWLIST)}")

    findings = audit_learner_isolation()
    if findings:
        print(f"Isolation audit: FAILED ({len(findings)} findings)")
        for finding in findings:
            print(
                f"- {finding.path} {finding.location}: "
                f"{finding.kind}={finding.value!r}"
            )
        return 1
    print("Isolation audit: PASSED (0 findings)")
    print(
        "Boundary: static source audit only; runtime, subprocess, and "
        "data-file channels are not covered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
