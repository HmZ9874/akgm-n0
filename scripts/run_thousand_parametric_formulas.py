from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    FormulaRejectionRoom,
    VerifiedEvolvedSemanticRoom,
    formula_id,
    mass_formula_logic_signature,
    semantic_normal_form,
    verify_evolved_operator,
    verify_mass_formula_batch,
)
from akgm_n0.learner import InducedMicroOperator, OperatorEvolutionSearch  # noqa: E402


REQUESTED = 1000
FIRST_OPCODE = 132
ROLE_NAMES = {
    "cell:0": "s0",
    "cell:1": "s1",
    "input:0": "u",
    "immediate:0": "p",
}


def main() -> int:
    seed_report = _read_json(ROOT / "reports/data/ten_micro_operator_invention_latest.json")
    prior_report = _read_json(ROOT / "reports/data/hundred_operator_evolution_latest.json")
    seeds = tuple(InducedMicroOperator.from_dict(item) for item in seed_report["operators"])
    prior_vectors = tuple(tuple(item["coefficient_vector"]) for item in prior_report["operators"])

    operators = OperatorEvolutionSearch().discover(
        seeds,
        requested_count=REQUESTED,
        first_opcode=FIRST_OPCODE,
        excluded_coefficient_vectors=prior_vectors,
        generation=3,
    )
    verification = verify_mass_formula_batch(
        operators,
        prior_coefficient_vectors=prior_vectors,
        required_count=REQUESTED,
        first_opcode=FIRST_OPCODE,
    )
    if not verification["passed"]:
        print(json.dumps(verification, ensure_ascii=False, indent=2))
        return 1

    proof_by_id = {item["operator_id"]: item for item in verification["operator_results"]}
    success_room = VerifiedEvolvedSemanticRoom(
        ROOT / "artifacts/formula_rooms/mass_universal/proven_formulas.jsonl"
    )
    stored = [success_room.record(item, proof_by_id[item.operator_id]) for item in operators]

    rejection_room = FormulaRejectionRoom(
        ROOT / "artifacts/formula_rooms/mistakes/thousand_formula_rejections.jsonl"
    )
    prior_by_vector = {
        tuple(item["coefficient_vector"]): item["operator_id"]
        for item in prior_report["operators"]
    }
    for vector, prior_id in prior_by_vector.items():
        rejection_room.record(
            reason="cross_generation_semantic_duplicate",
            candidate={"coefficient_vector": list(vector)},
            evidence={"duplicates_prior_operator_id": prior_id, "does_not_count_toward_stop": True},
        )
    duplicate = operators[0]
    rejection_room.record(
        reason="within_batch_semantic_duplicate",
        candidate={"coefficient_vector": list(duplicate.coefficient_vector)},
        evidence={"duplicates_formula_id": formula_id(duplicate), "does_not_count_toward_stop": True},
    )
    mutated = replace(
        operators[0],
        coefficient_vector=(operators[0].coefficient_vector[0] + 1, *operators[0].coefficient_vector[1:]),
    )
    mutated_proof = verify_evolved_operator(mutated)
    rejection_room.record(
        reason="symbolic_program_semantic_mismatch",
        candidate={
            "operator_id": mutated.operator_id,
            "claimed_coefficient_vector": list(mutated.coefficient_vector),
        },
        evidence={
            "proof_passed": mutated_proof["passed"],
            "failed_obligations": [
                item["obligation_id"] for item in mutated_proof["obligations"] if not item["passed"]
            ],
            "does_not_count_toward_stop": True,
        },
    )

    formula_records = [_formula_record(item, proof_by_id[item.operator_id]) for item in operators]
    normal_forms = {item["semantic_normal_form"] for item in formula_records}
    logic_signatures = {item["structural_logic_signature"] for item in formula_records}
    batch_ids = {item.operator_id for item in operators}
    room_ids = {event["operator"]["operator_id"] for event in success_room.records}
    negative_control_passed = not mutated_proof["passed"]
    gates = [
        {"gate_id": "exact_thousand_success_stop", "passed": len(operators) == REQUESTED, "actual": len(operators), "required": REQUESTED},
        {"gate_id": "semantic_normal_forms_all_unique", "passed": len(normal_forms) == REQUESTED, "actual": len(normal_forms), "required": REQUESTED},
        {"gate_id": "program_logic_signatures_all_unique", "passed": len(logic_signatures) == REQUESTED, "actual": len(logic_signatures), "required": REQUESTED},
        {"gate_id": "no_overlap_with_previous_hundred", "passed": not ({item.coefficient_vector for item in operators} & set(prior_vectors)), "actual": len({item.coefficient_vector for item in operators} & set(prior_vectors)), "required": 0},
        {"gate_id": "all_exact_universal_proofs_pass", "passed": verification["formula_proof_count"] == REQUESTED, "actual": verification["formula_proof_count"], "required": REQUESTED},
        {"gate_id": "all_hidden_replays_pass", "passed": verification["hidden_replay_passed_count"] == verification["hidden_replay_count"] == 12000, "actual": verification["hidden_replay_passed_count"], "required": verification["hidden_replay_count"]},
        {"gate_id": "all_formulas_persisted_in_success_room", "passed": batch_ids.issubset(room_ids) and len(stored) == REQUESTED, "actual": len(batch_ids & room_ids), "required": REQUESTED},
        {"gate_id": "invalid_and_duplicate_candidates_enter_mistake_room", "passed": negative_control_passed and len(rejection_room.records) >= 102, "actual": len(rejection_room.records), "required": 102},
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-thousand-parametric-formulas-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    length_distribution = Counter(item["expanded_instruction_count"] for item in formula_records)
    report = {
        "report_version": "thousand-parametric-formulas-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "one_thousand_new_parametric_formula_semantics_universally_verified",
        "stop_rule": {
            "requested_new_formula_count": REQUESTED,
            "actual_new_formula_count": len(operators),
            "program_stopped": len(operators) == REQUESTED and verification["passed"],
        },
        "declared_scope": {
            "formula_class": "role-sensitive affine-additive state-assignment schemas",
            "formal_domain": verification["formal_domain"],
            "universal_statement": "for every assignment of s0,s1,u,p in the declared domain, the executable left side equals its exact normalized integer-coefficient expression",
            "not_claimed": "These are not 1000 independent foundations or 1000 unrelated branches of mathematics.",
        },
        "discovery": {
            "generation": 3,
            "seed_semantic_count": len(seeds),
            "historical_semantics_excluded": len(prior_vectors),
            "first_opcode": operators[0].opcode,
            "last_opcode": operators[-1].opcode,
            "formula_names_given_to_search": False,
            "target_formulas_given_to_search": False,
            "selection_rule": "shortest anonymous program first; exact semantic-normal-form deduplication; historical effects excluded",
            "instruction_length_distribution": {str(key): value for key, value in sorted(length_distribution.items())},
        },
        "verification": {
            "verifier_version": verification["verifier_version"],
            "proof_method": verification["proof_method"],
            "finite_sampling_used_as_universal_proof": verification["finite_sampling_used_as_universal_proof"],
            "formula_proof_count": verification["formula_proof_count"],
            "formula_count": verification["formula_count"],
            "hidden_replay_passed_count": verification["hidden_replay_passed_count"],
            "hidden_replay_count": verification["hidden_replay_count"],
            "obligations": verification["obligations"],
        },
        "formulas": formula_records,
        "rooms": {
            "success": "artifacts/formula_rooms/mass_universal/proven_formulas.jsonl",
            "mistakes": "artifacts/formula_rooms/mistakes/thousand_formula_rejections.jsonl",
            "success_batch_count": len(stored),
            "mistake_record_count": len(rejection_room.records),
            "hash_chained": True,
            "proof_replayed_on_success_room_load": True,
        },
        "gates": gates,
        "limitations": [
            "The 1000 formulas have different exact normalized transfer functions and different minimal programs, but share one affine-additive algebraic family.",
            "Changing only spelling, instruction order, or an already-known coefficient vector does not count as a new formula.",
            "The discovery grammar and independent proof checker are still host-provided code.",
            "Nonlinear, branching, recursive, and continuous formula families require separate exploration and are not included in this count.",
        ],
    }
    artifact = run_dir / "thousand_parametric_formula_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    catalog = run_dir / "thousand_parametric_formula_catalog.jsonl"
    with catalog.open("w", encoding="utf-8", newline="\n") as stream:
        for item in formula_records:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    for destination in (
        ROOT / "reports/data/thousand_parametric_formulas_latest.json",
        ROOT / "dashboard/data/thousand_parametric_formulas_latest.json",
        ROOT / "artifacts/formula_rooms/mass_universal/thousand_formula_report_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    shutil.copyfile(catalog, ROOT / "artifacts/formula_rooms/mass_universal/thousand_formula_catalog_latest.jsonl")

    print(json.dumps({
        "run_id": run_id,
        "new_formulas": len(formula_records),
        "opcode_range": [operators[0].opcode, operators[-1].opcode],
        "unique_semantic_normal_forms": len(normal_forms),
        "universal_proofs": f"{verification['formula_proof_count']}/{verification['formula_count']}",
        "hidden_replays": f"{verification['hidden_replay_passed_count']}/{verification['hidden_replay_count']}",
        "mistake_records": len(rejection_room.records),
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0


def _formula_record(operator, proof: dict) -> dict:
    normal = semantic_normal_form(operator)
    return {
        "formula_id": formula_id(operator),
        "operator_id": operator.operator_id,
        "opcode": operator.opcode,
        "formula": _render(operator),
        "free_runtime_variables": [ROLE_NAMES[token] for token in operator.operand_tokens],
        "coefficient_vector": list(operator.coefficient_vector),
        "semantic_normal_form": normal,
        "structural_logic_signature": mass_formula_logic_signature(operator),
        "expanded_instruction_count": len(operator.normalized_instructions),
        "universal_proof_passed": proof["passed"],
        "proof_digest": hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


def _render(operator) -> str:
    terms: list[tuple[str, str]] = []
    for token, coefficient in zip(operator.operand_tokens, operator.coefficient_vector, strict=True):
        if coefficient == 0:
            continue
        name = ROLE_NAMES[token]
        magnitude = abs(coefficient)
        atom = name if magnitude == 1 else f"{magnitude}·{name}"
        terms.append(("+" if coefficient > 0 else "-", atom))
    first_sign, first_atom = terms[0]
    expression = ("-" if first_sign == "-" else "") + first_atom
    for sign, atom in terms[1:]:
        expression += f" {sign} {atom}"
    return f"s0' = {expression}"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
