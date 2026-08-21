"""Expand every strictly admitted V10-V12 foundation into a larger domain."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.strict_foundation_expansion_v13 import (  # noqa: E402
    prove_integer_partition,
    prove_rational_integer_power,
    prove_signed_product,
)
from akgm_n0.learner.strict_counter_foundation_v10 import TargetFreeCounterExplorer  # noqa: E402
from akgm_n0.learner.strict_fold_foundation_v12 import TargetFreeFoldExplorer  # noqa: E402
from akgm_n0.learner.strict_foundation_expansion_v13 import StrictFoundationExpander, StrictFoundationRuntime  # noqa: E402
from akgm_n0.learner.strict_partition_foundation_v11 import TargetFreePartitionExplorer  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-strict-expansion-v13-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    runtime = StrictFoundationRuntime(
        TargetFreeCounterExplorer().search().selected.program,
        TargetFreePartitionExplorer().search().selected.program,
        TargetFreeFoldExplorer().search().selected.program,
    )
    expander = StrictFoundationExpander(runtime)
    searches = (
        expander.search_signed_product(),
        expander.search_integer_partition(),
        expander.search_rational_integer_power(),
    )
    proofs = (
        prove_signed_product(runtime, searches[0].selected),
        prove_integer_partition(runtime, searches[1].selected),
        prove_rational_integer_power(runtime, searches[2].selected),
    )
    if not all(proof.passed for proof in proofs):
        raise RuntimeError("one or more strict foundation expansions failed proof")
    report = {
        "report_version": "strict-foundation-expansion-v13.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "all_three_strict_foundations_expanded_and_universally_proven",
        "source_foundations": [
            {"version": "V10", "semantic": "STRICT-FSEM-82df58ba4ce6f41c", "domain": "N×N→N"},
            {"version": "V11", "semantic": "strict_v11_two_output", "domain": "N×N+→N×N"},
            {"version": "V12", "semantic": "strict_v12_fold", "domain": "N×N→N"},
        ],
        "expansions": [
            {
                "source": source,
                "search": {
                    "policies_generated": search.generated,
                    "behavior_classes": search.behavior_classes,
                    "passing_behavior_classes": search.passing_behavior_classes,
                    "selected": search.selected.to_dict(),
                },
                "proof": proof.to_dict(),
            }
            for source, search, proof in zip(("V10", "V11", "V12"), searches, proofs, strict=True)
        ],
        "summary": {
            "foundations_considered": 3,
            "foundations_expanded": 3,
            "new_foundations_claimed": 0,
            "verified_domain_extensions": 3,
            "proof_obligations_passed": sum(sum(item["passed"] for item in proof.obligations) for proof in proofs),
            "proof_obligations_total": sum(len(proof.obligations) for proof in proofs),
        },
        "classification": {
            "label": "verified_domain_closure_of_strict_foundations",
            "target_output_rows": False,
            "policy_search_is_bounded": True,
            "host_supplied": ["domain representations", "policy grammars", "law detectors", "universal case proof schemas"],
            "human_novel_mathematics_claim": False,
        },
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "strict_foundation_expansion_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/strict_foundation_expansion_v13_latest.json",
        ROOT / "dashboard/data/strict_foundation_expansion_v13_latest.json",
        ROOT / "artifacts/foundation/v13/success/strict_foundation_expansions_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "expanded": "3/3",
        "proof": f"{report['summary']['proof_obligations_passed']}/{report['summary']['proof_obligations_total']}",
        "expansions": [proof.posthoc_name for proof in proofs],
        "new_foundations_claimed": 0,
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
