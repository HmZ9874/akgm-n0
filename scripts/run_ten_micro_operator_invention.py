from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    UniversalFormulaRoom,
    VerifiedSemanticRoom,
    verify_micro_operator_batch,
)
from akgm_n0.learner import MicroOperatorMiner  # noqa: E402


def main() -> int:
    sources = _load_independently_proven_word_sources()
    operators = MicroOperatorMiner().discover(
        sources, requested_count=10, first_opcode=18, minimum_occurrences=2
    )
    verification = verify_micro_operator_batch(operators, required_count=10)
    if not verification["passed"]:
        print(json.dumps(verification, ensure_ascii=False, indent=2))
        return 1

    room = VerifiedSemanticRoom(
        ROOT / "artifacts/semantics/verified_semantics.jsonl"
    )
    proof_by_id = {
        item["operator_id"]: item for item in verification["operator_results"]
    }
    stored = [room.record(item, proof_by_id[item.operator_id]) for item in operators]
    stored_ids = {
        event["operator"]["operator_id"] for event in room.records
    }
    batch_ids = {item.operator_id for item in operators}

    gates = [
        {
            "gate_id": "exactly_ten_new_semantics",
            "passed": len(operators) == 10,
            "actual": len(operators),
            "required": 10,
        },
        {
            "gate_id": "ten_distinct_effects",
            "passed": len({item.effect_signature for item in operators}) == 10,
            "actual": len({item.effect_signature for item in operators}),
            "required": 10,
        },
        {
            "gate_id": "fresh_opcode_range",
            "passed": [item.opcode for item in operators] == list(range(18, 28)),
            "actual": [item.opcode for item in operators],
            "required": list(range(18, 28)),
        },
        {
            "gate_id": "all_have_multiple_proven_sources",
            "passed": all(len(item.source_record_ids) >= 2 for item in operators),
            "actual": min(len(item.source_record_ids) for item in operators),
            "required": 2,
        },
        {
            "gate_id": "independent_expansion_equivalence",
            "passed": verification["passed"],
            "actual": verification["passed_probe_case_count"],
            "required": verification["probe_case_count"],
        },
        {
            "gate_id": "success_operator_room_persisted",
            "passed": batch_ids.issubset(stored_ids) and len(stored) == 10,
            "actual": len(batch_ids & stored_ids),
            "required": 10,
        },
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-ten-micro-operators-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "ten-micro-operator-invention-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "ten_new_operators_verified_and_persisted",
        "stop_rule": {
            "requested_new_operator_count": 10,
            "actual_new_operator_count": len(operators),
            "program_stopped": len(operators) == 10 and verification["passed"],
        },
        "source_evidence": {
            "independently_proven_word_program_count": len(sources),
            "room_paths": [
                "artifacts/formula_rooms/universal/proven_formulas.jsonl",
                "artifacts/formula_rooms/parametric/proven_formulas.jsonl",
            ],
            "formula_or_operator_names_given_to_miner": False,
        },
        "operators": [
            {
                **item.to_dict(),
                "posthoc_effect": _render_effect(item.target_token, item.effect_ast),
                "source_program_count": len(item.source_record_ids),
                "verification": proof_by_id[item.operator_id],
            }
            for item in operators
        ],
        "verification": verification,
        "semantic_room": {
            "path": "artifacts/semantics/verified_semantics.jsonl",
            "batch_record_count": len(stored),
            "hash_chained": True,
            "proof_replayed_on_load": True,
        },
        "gates": gates,
        "learner_received": {
            "operator_names": False,
            "formula_names": False,
            "target_effects": False,
            "proven_anonymous_word_code": True,
            "normalization_grammar": True,
        },
        "limitations": [
            "These are induced straight-line micro-operators that compress previously proven word-code effects, not arbitrary new control-flow semantics.",
            "The miner, normalizer, and extended operator executor are host implementations; the system is not yet rewriting its own interpreter binary.",
            "Equivalence is structurally bound and independently replayed on diverse hidden numeric probes; it is not a proof over IEEE-754 exceptional values such as NaN and infinity.",
        ],
    }
    artifact = run_dir / "ten_micro_operator_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/ten_micro_operator_invention_latest.json",
        ROOT / "dashboard/data/ten_micro_operator_invention_latest.json",
        ROOT / "artifacts/semantics/ten_micro_operator_library_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": report["verdict"],
                "new_operator_count": len(operators),
                "opcodes": [item.opcode for item in operators],
                "operator_ids": [item.operator_id for item in operators],
                "independent_probes": (
                    f"{verification['passed_probe_case_count']}/"
                    f"{verification['probe_case_count']}"
                ),
                "minimum_proven_source_programs": min(
                    len(item.source_record_ids) for item in operators
                ),
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load_independently_proven_word_sources() -> list[tuple[str, tuple[int, ...]]]:
    sources: list[tuple[str, tuple[int, ...]]] = []
    seen: set[str] = set()
    for path in (
        ROOT / "artifacts/formula_rooms/universal/proven_formulas.jsonl",
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl",
    ):
        room = UniversalFormulaRoom(path)
        for record in room.records:
            if record.room_record_id in seen or "words" not in record.program:
                continue
            seen.add(record.room_record_id)
            sources.append(
                (
                    record.room_record_id,
                    tuple(int(item) for item in record.program["words"]),
                )
            )
    return sources


def _render_effect(target: str, node: Mapping[str, Any]) -> str:
    op = node["op"]
    if op == "token":
        return target + " <- " + str(node["token"])
    left, right = node["args"]
    symbol = "+" if op == "add" else "-"
    return target + " <- " + _render_node(left) + " " + symbol + " " + _render_node(right)


def _render_node(node: Mapping[str, Any]) -> str:
    if node["op"] == "token":
        return str(node["token"])
    left, right = node["args"]
    symbol = "+" if node["op"] == "add" else "-"
    return "(" + _render_node(left) + " " + symbol + " " + _render_node(right) + ")"


if __name__ == "__main__":
    raise SystemExit(main())

