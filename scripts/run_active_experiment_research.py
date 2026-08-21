"""Research whether one chosen numeric action can reject competing programs."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import KnowledgeLedger, RelationMistakeLibrary
from akgm_n0.learner import (
    NumericCollectionObservation,
    NumericExperimentPlanner,
    RelationExecutor,
    RelationNode,
    RelationProgramSearch,
    relation_constant,
    relation_subtract,
    relation_value,
)


MINIMUM_HYPOTHESES = 5


def observation(values: tuple[float, ...], session: str):
    return NumericCollectionObservation.create(
        opaque_session_id=session,
        numeric_values=values,
        validity_mask=[True] * len(values),
        action_receipt=f"RECEIPT-{session}",
    )


def render(program: RelationNode) -> str:
    if program.op == "r_value":
        return "x"
    if program.op == "r_constant":
        return str(program.constant)
    symbol = "+" if program.op == "r_add" else "-"
    return f"({render(program.args[0])} {symbol} {render(program.args[1])})"


def main() -> int:
    initial_values = (3.0, 7.0, 15.0, 31.0)
    search = RelationProgramSearch(maximum_nodes=5, top_k=MINIMUM_HYPOTHESES)
    search_report = search.search(observation(initial_values, "ACTIVE-INITIAL"))
    hypotheses = tuple(
        candidate.program for candidate in search_report.top_candidates[:MINIMUM_HYPOTHESES]
    )
    if len(hypotheses) < MINIMUM_HYPOTHESES:
        raise RuntimeError("search did not produce the registered hypothesis count")

    # Evaluator-only target. The learner receives hypotheses, allowed actions, and one
    # numeric result; it never receives this program or its readable interpretation.
    hidden_program = relation_subtract(
        relation_value(),
        relation_subtract(relation_constant(-1), relation_value()),
    )
    executor = RelationExecutor()
    planner = NumericExperimentPlanner(executor=executor)
    action_candidates = tuple(float(value) for value in range(-8, 21))
    plan = planner.choose(
        hypotheses,
        action_candidates,
        observed_actions=initial_values,
    )
    selected_action = plan.selected.action
    observed_result = executor.evaluate(hidden_program, selected_action)
    update = planner.update(
        hypotheses,
        action=selected_action,
        observed_value=observed_result,
    )

    candidate_by_id = {
        planner.candidate_id(program): program for program in hypotheses
    }
    retained_programs = tuple(
        candidate_by_id[candidate_id]
        for candidate_id in update.retained_candidate_ids
    )
    hidden_key = json.dumps(
        hidden_program.to_dict(), sort_keys=True, separators=(",", ":")
    )
    retained_keys = {
        json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))
        for program in retained_programs
    }

    passive_survivor_counts = []
    for action in action_candidates:
        if action in initial_values:
            continue
        result = executor.evaluate(hidden_program, action)
        passive_survivor_counts.append(
            len(
                planner.update(
                    hypotheses,
                    action=action,
                    observed_value=result,
                ).retained_candidate_ids
            )
        )
    average_passive_survivors = sum(passive_survivor_counts) / len(
        passive_survivor_counts
    )

    reverse_report = search.search(
        observation(tuple(reversed(initial_values)), "ACTIVE-ORDER-ABLATION")
    )
    reverse_hypotheses = tuple(
        candidate.program
        for candidate in reverse_report.top_candidates[:MINIMUM_HYPOTHESES]
    )
    reverse_plan = planner.choose(
        reverse_hypotheses,
        action_candidates,
        observed_actions=initial_values,
    )

    gates = [
        {
            "gate_id": "minimum_competing_hypotheses",
            "passed": len(hypotheses) >= MINIMUM_HYPOTHESES,
            "actual": len(hypotheses),
            "threshold": MINIMUM_HYPOTHESES,
        },
        {
            "gate_id": "selected_action_maximizes_registered_utility",
            "passed": plan.selected.utility
            == max(item.utility for item in plan.ranked_actions),
            "actual": plan.selected.utility,
            "threshold": max(item.utility for item in plan.ranked_actions),
        },
        {
            "gate_id": "input_order_ablation",
            "passed": reverse_plan.selected.action == selected_action,
            "actual": reverse_plan.selected.action,
            "threshold": selected_action,
        },
        {
            "gate_id": "hidden_program_survives_numeric_feedback",
            "passed": hidden_key in retained_keys,
            "actual": hidden_key in retained_keys,
            "threshold": True,
        },
        {
            "gate_id": "single_experiment_rejects_four_false_programs",
            "passed": len(update.rejected_candidate_ids) >= 4,
            "actual": len(update.rejected_candidate_ids),
            "threshold": 4,
        },
        {
            "gate_id": "single_hypothesis_remaining",
            "passed": len(update.retained_candidate_ids) == 1,
            "actual": len(update.retained_candidate_ids),
            "threshold": 1,
        },
        {
            "gate_id": "unseen_environment_family_transfer",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
    ]
    verdict = (
        "conditionally_passed"
        if all(gate["passed"] for gate in gates if gate["passed"] is not None)
        else "failed"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-active-research-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)

    condition_key = "active-set-" + hashlib.sha256(
        "|".join(sorted(candidate_by_id)).encode("utf-8")
    ).hexdigest()[:16]
    mistake_library = RelationMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "relation_mistakes.jsonl"
    )
    mistake_records = []
    prediction_by_id = {
        candidate_id: (predicted, error)
        for candidate_id, predicted, error in update.predictions
    }
    for candidate_id in update.rejected_candidate_ids:
        predicted, error = prediction_by_id[candidate_id]
        record = mistake_library.record(
            candidate_by_id[candidate_id],
            objective_id="active_numeric_hypothesis_discrimination",
            failed_scope="selected_intervention",
            condition_key=condition_key,
            counterexamples=(
                {
                    "action": selected_action,
                    "predicted_value": predicted,
                    "observed_value": observed_result,
                    "absolute_error": error,
                },
            ),
            source_candidate_id=candidate_id,
        )
        mistake_records.append(record.to_dict())

    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_records = []
    for candidate_id in update.retained_candidate_ids:
        program = candidate_by_id[candidate_id]
        knowledge_id = ledger.propose(
            program,
            parent_ids=("relation_search", "experiment_planner", "numeric_feedback"),
            provenance={"run_id": run_id, "candidate_id": candidate_id},
            evidence={"selected_experiment": update.to_dict()},
        )
        ledger.transition(
            knowledge_id,
            "fit_passed",
            reason="candidate_matches_initial_relations_and_selected_intervention",
            evidence={"initial_values": list(initial_values)},
        )
        ledger.transition(
            knowledge_id,
            "verified",
            reason="independent_numeric_intervention_retained_candidate",
            evidence={"action": selected_action, "observed": observed_result},
        )
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="unseen_environment_family_transfer_pending",
            evidence={"pending_gate": "unseen_environment_family_transfer"},
        )
        knowledge_records.append(
            {
                "knowledge_id": knowledge_id,
                "candidate_id": candidate_id,
                "status": ledger.get(knowledge_id).status,
            }
        )

    report = {
        "report_version": "active-experiment-research-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "竞争程序的主动区分实验",
        "verdict": verdict,
        "knowledge_status": (
            knowledge_records[0]["status"] if len(knowledge_records) == 1 else "rejected"
        ),
        "architecture": "numeric_program_committee_plus_information_gain_planner",
        "learner_received": {
            "initial_unordered_values": list(initial_values),
            "hypothesis_count": len(hypotheses),
            "allowed_numeric_actions": list(action_candidates),
            "hidden_program": False,
            "target_formula": False,
            "natural_language_labels": False,
            "feedback": {"action": selected_action, "numeric_result": observed_result},
        },
        "hypotheses_before_experiment": [
            {
                "candidate_id": planner.candidate_id(program),
                "program": program.to_dict(),
                "post_hoc_readable": render(program),
            }
            for program in hypotheses
        ],
        "experiment_plan": plan.to_dict(),
        "numeric_feedback_update": update.to_dict(),
        "passive_action_baseline": {
            "action_count": len(passive_survivor_counts),
            "average_remaining_hypotheses": average_passive_survivors,
            "selected_action_remaining_hypotheses": len(
                update.retained_candidate_ids
            ),
        },
        "evaluator_post_hoc": {
            "revealed_after_update": True,
            "hidden_program": hidden_program.to_dict(),
            "readable": render(hidden_program),
        },
        "mistake_records": mistake_records,
        "knowledge_records": knowledge_records,
        "gates": gates,
        "limitations": [
            "The action planner ranks a finite registered action set; it does not invent an unbounded experiment domain.",
            "Information gain assumes equal prior weight over the five executable hypotheses.",
            "This run tests one hidden numeric world and does not establish transfer across environment families.",
            "The planner improves hypothesis discrimination; it does not yet invent CPU-level control or storage semantics.",
        ],
    }
    artifact_path = run_directory / "active_experiment_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "active_experiment_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "active_experiment_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "initial_hypothesis_count": len(hypotheses),
                "selected_action": selected_action,
                "information_gain_bits": plan.selected.information_gain_bits,
                "observed_result": observed_result,
                "retained_count": len(update.retained_candidate_ids),
                "rejected_count": len(update.rejected_candidate_ids),
                "mistake_records_written": len(mistake_records),
                "knowledge_records": knowledge_records,
                "hypotheses": [
                    {
                        "candidate_id": planner.candidate_id(program),
                        "formula": render(program),
                    }
                    for program in hypotheses
                ],
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
