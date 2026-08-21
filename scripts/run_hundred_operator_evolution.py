from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    VerifiedEvolvedSemanticRoom,
    verify_evolved_operator_batch,
    verify_micro_operator_batch,
)
from akgm_n0.learner import (  # noqa: E402
    InducedMicroOperator,
    OperatorEvolutionSearch,
)


def main() -> int:
    seed_report = json.loads(
        (ROOT / "reports/data/ten_micro_operator_invention_latest.json").read_text(
            encoding="utf-8"
        )
    )
    seeds = tuple(
        InducedMicroOperator.from_dict(item) for item in seed_report["operators"]
    )
    seed_proof = verify_micro_operator_batch(seeds, required_count=10)
    if not seed_proof["passed"]:
        print(json.dumps(seed_proof, ensure_ascii=False, indent=2))
        return 1

    operators = OperatorEvolutionSearch().discover(
        seeds, requested_count=100, first_opcode=28
    )
    verification = verify_evolved_operator_batch(operators, required_count=100)
    if not verification["passed"]:
        print(json.dumps(verification, ensure_ascii=False, indent=2))
        return 1

    room = VerifiedEvolvedSemanticRoom(
        ROOT / "artifacts/semantics/verified_evolved_semantics.jsonl"
    )
    proof_by_id = {
        item["operator_id"]: item for item in verification["operator_results"]
    }
    stored = [room.record(item, proof_by_id[item.operator_id]) for item in operators]
    room_ids = {event["operator"]["operator_id"] for event in room.records}
    batch_ids = {item.operator_id for item in operators}

    gates = [
        {
            "gate_id": "exact_hundred_stop_count",
            "passed": len(operators) == 100,
            "actual": len(operators),
            "required": 100,
        },
        {
            "gate_id": "hundred_unique_coefficient_structures",
            "passed": len({item.coefficient_vector for item in operators}) == 100,
            "actual": len({item.coefficient_vector for item in operators}),
            "required": 100,
        },
        {
            "gate_id": "new_opcode_range_28_to_127",
            "passed": [item.opcode for item in operators] == list(range(28, 128)),
            "actual": f"{operators[0].opcode}-{operators[-1].opcode}",
            "required": "28-127",
        },
        {
            "gate_id": "all_effects_use_multiple_operand_roles",
            "passed": all(
                sum(value != 0 for value in item.coefficient_vector) >= 2
                for item in operators
            ),
            "actual": min(
                sum(value != 0 for value in item.coefficient_vector)
                for item in operators
            ),
            "required": 2,
        },
        {
            "gate_id": "all_symbolic_and_replay_proofs_pass",
            "passed": verification["passed"],
            "actual": sum(item["passed"] for item in verification["operator_results"]),
            "required": 100,
        },
        {
            "gate_id": "all_1200_hidden_replays_pass",
            "passed": verification["passed_probe_case_count"]
            == verification["probe_case_count"]
            == 1200,
            "actual": verification["passed_probe_case_count"],
            "required": verification["probe_case_count"],
        },
        {
            "gate_id": "hundred_success_semantics_persisted",
            "passed": batch_ids.issubset(room_ids) and len(stored) == 100,
            "actual": len(batch_ids & room_ids),
            "required": 100,
        },
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-hundred-operator-evolution-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    length_distribution = Counter(
        len(item.normalized_instructions) for item in operators
    )
    report = {
        "report_version": "hundred-operator-evolution-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "exactly_one_hundred_new_composite_operators_verified",
        "stop_rule": {
            "requested_new_operator_count": 100,
            "actual_new_operator_count": len(operators),
            "program_stopped": len(operators) == 100 and verification["passed"],
        },
        "evolution": {
            "generation": 2,
            "seed_operator_count": len(seeds),
            "seed_operator_ids": [item.operator_id for item in seeds],
            "formula_or_operator_names_given_to_search": False,
            "selection_rule": "shortest expansion first, normalized coefficient-vector deduplication",
            "target_cell_selected_from_seed_frequency": operators[0].target_token,
            "operand_roles_discovered_from_seeds": list(operators[0].operand_tokens),
            "expanded_instruction_length_distribution": {
                str(key): value for key, value in sorted(length_distribution.items())
            },
        },
        "operators": [
            {
                **operator.to_dict(),
                "posthoc_effect": _render(operator),
                "expanded_instruction_count": len(operator.normalized_instructions),
                "verification": proof_by_id[operator.operator_id],
            }
            for operator in operators
        ],
        "verification": verification,
        "semantic_room": {
            "path": "artifacts/semantics/verified_evolved_semantics.jsonl",
            "batch_record_count": len(stored),
            "hash_chained": True,
            "proof_replayed_on_load": True,
        },
        "gates": gates,
        "learner_received": {
            "operator_names": False,
            "target_formulas": False,
            "list_of_one_hundred_effects": False,
            "ten_verified_seed_semantics": True,
            "additive_program_grammar": True,
            "shorter_expansion_reward": True,
        },
        "limitations": [
            "The 100 results are distinct fused affine-additive micro-operators, not 100 newly discovered foundations of mathematics.",
            "Uniqueness is exact at the normalized coefficient-vector level, so address renaming and algebraically equivalent instruction order do not create extra counts.",
            "This generation cannot yet invent nonlinear state transitions, new branching laws, loops, or new memory topology.",
            "The search grammar, proof checker, and runtime remain host code; the framework is not rewriting its own interpreter binary.",
        ],
    }
    artifact = run_dir / "hundred_operator_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/hundred_operator_evolution_latest.json",
        ROOT / "dashboard/data/hundred_operator_evolution_latest.json",
        ROOT / "artifacts/semantics/hundred_operator_library_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": report["verdict"],
                "new_operator_count": len(operators),
                "opcode_range": [operators[0].opcode, operators[-1].opcode],
                "unique_coefficient_structures": len(
                    {item.coefficient_vector for item in operators}
                ),
                "symbolic_proofs": f"{sum(item['passed'] for item in verification['operator_results'])}/100",
                "independent_replays": (
                    f"{verification['passed_probe_case_count']}/"
                    f"{verification['probe_case_count']}"
                ),
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _render(operator) -> str:
    terms = []
    for token, coefficient in zip(
        operator.operand_tokens, operator.coefficient_vector, strict=True
    ):
        if coefficient == 0:
            continue
        magnitude = abs(coefficient)
        atom = token if magnitude == 1 else f"{magnitude}*{token}"
        terms.append(("+" if coefficient > 0 else "-", atom))
    if not terms:
        expression = "0"
    else:
        first_sign, first_atom = terms[0]
        expression = ("-" if first_sign == "-" else "") + first_atom
        for sign, atom in terms[1:]:
            expression += f" {sign} {atom}"
    return f"{operator.target_token} <- {expression}"


if __name__ == "__main__":
    raise SystemExit(main())

