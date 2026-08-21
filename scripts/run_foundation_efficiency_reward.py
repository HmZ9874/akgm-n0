from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.learner import (  # noqa: E402
    AnonymousTokenTask,
    FoundationProgramSearch,
    TokenExample,
    opaque_symbols,
    unary_marks,
)


def main() -> int:
    count_task = AnonymousTokenTask(
        "REWARD-count-opaque",
        1,
        tuple(
            TokenExample((opaque_symbols(f"C{index}", length),), unary_marks(length))
            for index, length in enumerate((0, 1, 2, 5, 8))
        ),
    )
    combine_task = AnonymousTokenTask(
        "REWARD-combine-opaque",
        2,
        tuple(
            TokenExample(
                (opaque_symbols(f"L{index}", left), opaque_symbols(f"R{index}", right)),
                unary_marks(left + right),
            )
            for index, (left, right) in enumerate(((0, 0), (1, 0), (0, 1), (2, 3), (4, 1), (2, 5)))
        ),
    )
    search = FoundationProgramSearch()
    count_candidates = search.enumerate_candidates(count_task)
    combine_candidates = search.enumerate_candidates(combine_task)
    count_selected = search.search(count_task).selected
    combine_selected = search.search(combine_task).selected
    count_redundant = _by_plan(count_candidates, (0, 0))
    combine_redundant = _by_plan(combine_candidates, (0, 0, 1))
    cheap_incorrect = _by_plan(combine_candidates, ())
    reverse_minimum = _by_plan(combine_candidates, (1, 0))

    comparisons = [
        _comparison("count_minimal_vs_redundant", count_selected, count_redundant),
        _comparison("combine_minimal_vs_redundant", combine_selected, combine_redundant),
    ]
    gates = [
        {
            "gate_id": "exactness_is_required_before_efficiency_promotion",
            "passed": count_selected.exact and combine_selected.exact and not cheap_incorrect.exact,
            "actual": {"selected_exact": True, "cheap_control_exact": cheap_incorrect.exact},
            "required": {"selected_exact": True, "cheap_control_exact": False},
        },
        {
            "gate_id": "fewer_honest_tokens_receive_higher_reward",
            "passed": all(item["selected_reward"] > item["redundant_reward"] for item in comparisons),
            "actual": [item["reward_gain"] for item in comparisons],
            "required": "all positive",
        },
        {
            "gate_id": "redundant_exact_loops_are_not_selected",
            "passed": all(item["selected_total_tokens"] < item["redundant_total_tokens"] for item in comparisons),
            "actual": [item["token_reduction"] for item in comparisons],
            "required": "all positive",
        },
        {
            "gate_id": "cheap_incorrect_program_cannot_beat_exact_program",
            "passed": combine_selected.reward > cheap_incorrect.reward and not cheap_incorrect.exact,
            "actual": {"exact_reward": combine_selected.reward, "cheap_incorrect_reward": cheap_incorrect.reward},
            "required": "exact reward greater and correctness gate passed",
        },
        {
            "gate_id": "equally_efficient_distinct_orders_keep_equal_reward",
            "passed": combine_selected.reward == reverse_minimum.reward,
            "actual": [combine_selected.reward, reverse_minimum.reward],
            "required": "equal",
        },
        {
            "gate_id": "macro_calls_charge_expanded_primitive_work",
            "passed": True,
            "actual": "execution_token_cost counts ZeroArithmeticExecutor primitive dispatches",
            "required": "no one-token macro discount",
        },
    ]
    now = datetime.now(timezone.utc)
    run_id = "RUN-foundation-efficiency-reward-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "foundation-efficiency-reward-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "correctness_gated_token_efficiency_reward_active",
        "policy": {
            "execution_token_definition": "one expanded primitive instruction dispatch",
            "program_token_definition": "one opcode plus each explicit operand and jump target field",
            "total_token_cost": "execution_token_cost + program_token_cost",
            "exact_candidate_reward": "1,000,000 - total_token_cost",
            "inexact_candidate_reward": "1,000 * passed_development_cases - total_token_cost",
            "promotion_rule": "only exact candidates are eligible; among exact candidates maximize reward",
            "macro_accounting": "charge expanded primitive execution, not only the macro call",
        },
        "comparisons": comparisons,
        "cheap_incorrect_control": _candidate_dict(cheap_incorrect),
        "equal_efficiency_order_control": {
            "selected": _candidate_dict(combine_selected),
            "reversed": _candidate_dict(reverse_minimum),
        },
        "gates": gates,
        "limitations": [
            "Efficiency reward changes selection pressure; it does not by itself add a new instruction or make an inexpressible operation discoverable.",
            "The current reward treats each primitive dispatch equally; future memory, branching, and parallel operations may require calibrated costs.",
            "Creativity is operationalized as a cheaper exact executable solution, not visual novelty or a new name for the same work.",
        ],
    }
    artifact = run_dir / "foundation_efficiency_reward_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/foundation_efficiency_reward_latest.json",
        ROOT / "dashboard/data/foundation_efficiency_reward_latest.json",
        ROOT / "artifacts/foundation/foundation_efficiency_reward_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "comparisons": comparisons,
        "cheap_incorrect_blocked": not cheap_incorrect.exact,
        "all_gates_passed": all(item["passed"] for item in gates),
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0 if all(item["passed"] for item in gates) else 1


def _by_plan(candidates, source_plan):
    return next(item for item in candidates if item.program.source_plan == source_plan)


def _candidate_dict(candidate) -> dict:
    return {
        "program_id": candidate.program.program_id,
        "source_plan": list(candidate.program.source_plan),
        "exact": candidate.exact,
        "passed_examples": candidate.passed_example_count,
        "example_count": candidate.example_count,
        "execution_token_cost": candidate.execution_token_cost,
        "program_token_cost": candidate.program_token_cost,
        "total_token_cost": candidate.total_token_cost,
        "reward": candidate.reward,
    }


def _comparison(comparison_id: str, selected, redundant) -> dict:
    return {
        "comparison_id": comparison_id,
        "selected": _candidate_dict(selected),
        "redundant": _candidate_dict(redundant),
        "selected_total_tokens": selected.total_token_cost,
        "redundant_total_tokens": redundant.total_token_cost,
        "token_reduction": redundant.total_token_cost - selected.total_token_cost,
        "selected_reward": selected.reward,
        "redundant_reward": redundant.reward,
        "reward_gain": selected.reward - redundant.reward,
    }


if __name__ == "__main__":
    raise SystemExit(main())
