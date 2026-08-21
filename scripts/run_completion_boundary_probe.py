from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import FormulaRejectionRoom  # noqa: E402
from akgm_n0.learner import interval_refinement  # noqa: E402


def _interval(value: tuple[int, int], depth: int) -> tuple[Fraction, Fraction]:
    lower, upper = interval_refinement(value, depth)
    return Fraction(*lower), Fraction(*upper)


def _candidate(mode: int, left: tuple[int, int], right: tuple[int, int], depth: int) -> bool:
    ll, lu = _interval(left, depth)
    rl, ru = _interval(right, depth)
    if mode == 0:
        return max(ll, rl) <= min(lu, ru)
    if mode == 1:
        return ll == rl
    if mode == 2:
        return lu == ru
    if mode == 3:
        return ll == rl and lu == ru
    if mode == 4:
        return (ll + lu) / 2 == (rl + ru) / 2
    if mode == 5:
        return Fraction(*left) == Fraction(*right)
    raise ValueError(mode)


def main() -> int:
    prior = json.loads(
        (ROOT / "reports/data/autonomous_interval_memory_latest.json").read_text(encoding="utf-8")
    )
    pairs = []
    values = ((0, 1), (1, 16), (1, 9), (1, 4), (1, 3), (1, 2), (2, 3), (3, 4), (1, 1), (2, 1), (3, 1), (5, 1))
    for value in values:
        pairs.append((value, value, True, "identity"))
        pairs.append((value, (value[0] * 7, value[1] * 7), True, "scaled_identity"))
    for depth in range(1, 9):
        denominator = 2 ** (2 * depth + 8)
        pairs.append(((1, 2), (denominator // 2 + 1, denominator), False, f"close_distinct_depth_{depth}"))
        pairs.append(((1, 3), (denominator // 3 + 1, denominator), False, f"close_distinct_third_depth_{depth}"))
    pairs.extend(
        ((left, right, False, "separated_control") for left, right in (((0, 1), (1, 1)), ((1, 4), (1, 2)), ((1, 1), (2, 1)), ((2, 1), (3, 1))))
    )
    results = []
    mistakes = FormulaRejectionRoom(
        ROOT / "artifacts/foundation/mistakes/completion_equivalence_candidates.jsonl"
    )
    for mode in range(6):
        counterexamples = []
        passed = 0
        total = 0
        for depth in range(1, 9):
            for left, right, expected, family in pairs:
                actual = _candidate(mode, left, right, depth)
                total += 1
                passed += actual == expected
                if actual != expected and len(counterexamples) < 12:
                    counterexamples.append(
                        {
                            "depth": depth,
                            "left": list(left),
                            "right": list(right),
                            "family": family,
                            "expected_equivalent": expected,
                            "actual_equivalent": actual,
                        }
                    )
        exact = passed == total
        novel = mode != 5
        candidate_id = "CEQ-" + hashlib.sha256(str(mode).encode()).hexdigest()[:16]
        result = {
            "candidate_id": candidate_id,
            "anonymous_mode": mode,
            "case_count": total,
            "passed_case_count": passed,
            "failed_case_count": total - passed,
            "observationally_exact": exact,
            "structurally_novel": novel,
            "promotable": exact and novel,
            "counterexamples": counterexamples,
            "posthoc_interpretation": (
                "finite-prefix overlap/equality rule" if mode < 5 else "canonical rational target equality"
            ),
        }
        results.append(result)
        mistakes.record(
            reason=(
                "finite_prefix_equivalence_has_close_distinct_counterexample"
                if not exact
                else "reuses_existing_rational_equality_not_a_completion_object"
            ),
            candidate={"candidate_id": candidate_id, "anonymous_mode": mode},
            evidence={**result, "does_not_enter_foundation_room": True},
        )
    promotable = [result for result in results if result["promotable"]]
    now = datetime.now(timezone.utc)
    run_id = "RUN-completion-boundary-probe-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    report = {
        "report_version": "completion-boundary-probe-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "no_new_completion_semantic_promoted",
        "resumed_from": {"run_id": prior["run_id"], "frontier": prior["next_frontier"]},
        "candidate_count": len(results),
        "promotable_candidate_count": len(promotable),
        "results": results,
        "foundation_count_before": 16,
        "foundation_count_after": 16,
        "mistake_room": "artifacts/foundation/mistakes/completion_equivalence_candidates.jsonl",
        "mistake_count": len(mistakes.records),
        "finding": "Every rule based only on a fixed finite interval prefix confuses sufficiently close distinct radicands. The only exact candidate compares the already-normalized rational inputs, so it reuses an old equality semantic and does not construct a quotient or limit object.",
        "required_new_mechanisms": [
            "a first-class infinite generator or universally quantified stream certificate",
            "an equivalence relation proved independent of finite prefix depth",
            "a quotient/object constructor whose identity is not the stored rational radicand",
        ],
        "next_frontier": {
            "world_id": "WORLD-completion-equivalence-121",
            "status": "dependency_blocked",
            "missing_dependency": "quotient_type_and_universal_stream_equivalence",
            "posthoc_math_name": None,
        },
        "limitations": [
            "Failure of these six candidates is not proof that no completion construction exists.",
            "The probe deliberately refuses to identify an infinite object from any fixed finite prefix.",
            "No new foundation is counted and no success-room event is written.",
        ],
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    artifact = run_dir / "completion_boundary_probe.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/completion_boundary_probe_latest.json",
        ROOT / "dashboard/data/completion_boundary_probe_latest.json",
        ROOT / "artifacts/foundation/completion_boundary_probe_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({"run_id": run_id, "verdict": report["verdict"], "candidate_count": len(results), "promotable_candidate_count": len(promotable), "failed_finite_prefix_modes": sum(not item["observationally_exact"] for item in results), "exact_but_non_novel_modes": sum(item["observationally_exact"] and not item["structurally_novel"] for item in results), "foundation_count": 16, "next_blocked_dependency": report["next_frontier"]["missing_dependency"], "artifact_path": artifact.relative_to(ROOT).as_posix()}, ensure_ascii=True, indent=2))
    return 0 if not promotable else 1


if __name__ == "__main__":
    raise SystemExit(main())
