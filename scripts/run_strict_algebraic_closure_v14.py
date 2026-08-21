"""Compose strict foundations into rational and modular algebraic closures."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.strict_algebraic_closure_v14 import prove_congruence, prove_modular_fold, prove_modular_product, prove_rational_product  # noqa: E402
from akgm_n0.learner.strict_algebraic_closure_v14 import StrictAlgebraicClosureSearch  # noqa: E402
from akgm_n0.learner.strict_counter_foundation_v10 import TargetFreeCounterExplorer  # noqa: E402
from akgm_n0.learner.strict_fold_foundation_v12 import TargetFreeFoldExplorer  # noqa: E402
from akgm_n0.learner.strict_foundation_expansion_v13 import StrictFoundationExpander, StrictFoundationRuntime  # noqa: E402
from akgm_n0.learner.strict_partition_foundation_v11 import TargetFreePartitionExplorer  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-strict-closure-v14-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    runtime = StrictFoundationRuntime(TargetFreeCounterExplorer().search().selected.program, TargetFreePartitionExplorer().search().selected.program, TargetFreeFoldExplorer().search().selected.program)
    expander = StrictFoundationExpander(runtime)
    searcher = StrictAlgebraicClosureSearch(runtime, expander.search_signed_product().selected.policy, expander.search_integer_partition().selected.policy)
    rational = searcher.search_rational_product()
    congruence = searcher.search_congruence()
    modular_product = searcher.search_modular_product(congruence.selected.policy)
    modular_fold = searcher.search_modular_fold(congruence.selected.policy, modular_product.selected.policy)
    searches = (rational, congruence, modular_product, modular_fold)
    proofs = (prove_rational_product(rational.selected), prove_congruence(congruence.selected), prove_modular_product(modular_product.selected), prove_modular_fold(modular_fold.selected))
    if not all(proof.passed for proof in proofs):
        raise RuntimeError("algebraic closure proof failed")
    report = {
        "report_version": "strict-algebraic-closure-v14.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "four_composed_algebraic_closures_universally_proven",
        "closures": [{"search": {"generated": search.generated, "behavior_classes": search.behavior_classes, "passing_behavior_classes": search.passing_behavior_classes, "selected": search.selected.to_dict()}, "proof": proof.to_dict()} for search, proof in zip(searches, proofs, strict=True)],
        "summary": {
            "verified_closures": 4,
            "new_foundations_claimed": 0,
            "proof_passed": sum(sum(item["passed"] for item in proof.obligations) for proof in proofs),
            "proof_total": sum(len(proof.obligations) for proof in proofs),
            "strict_foundation_count_unchanged": 3,
        },
        "classification": {"label": "verified_compositional_closure", "target_output_rows": False, "bounded_policy_grammars": True, "host_supplied": ["rational-pair representation", "congruence-class representation", "component/reduction/fold policy grammars", "universal proof schemas"], "human_novel_mathematics_claim": False},
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "strict_algebraic_closure_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (ROOT / "reports/data/strict_algebraic_closure_v14_latest.json", ROOT / "dashboard/data/strict_algebraic_closure_v14_latest.json", ROOT / "artifacts/foundation/v14/success/strict_algebraic_closures_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({"run_id": run_id, "closures": [proof.posthoc_name for proof in proofs], "proof": f"{report['summary']['proof_passed']}/{report['summary']['proof_total']}", "new_foundations_claimed": 0, "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/")}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
