"""Audit the success room and disqualify formulas with duplicate bottom logic."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import FormulaSuccessRoom


MINIMUM_DISTINCT_FORMULAS = 5


def logic_signature(definition: dict) -> str:
    operations: set[str] = set()
    maximum_depth = 0
    stack = [(definition, 1)]
    while stack:
        node, depth = stack.pop()
        maximum_depth = max(maximum_depth, depth)
        operation = str(node.get("op"))
        if operation != "r_value":
            operations.add(operation)
        stack.extend((child, depth + 1) for child in node.get("args", []))
    return json.dumps(
        {
            "substrate_family": "stateless_unary_relation_ast",
            "primitive_operations": sorted(operations),
            "control_state": False,
            "dynamic_storage": False,
            "independent_lineage_required": True,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def main() -> int:
    room_path = (
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    room = FormulaSuccessRoom(room_path)
    active_before = list(room.records)
    kept_by_signature = {}
    disqualified = []
    for record in active_before:
        signature = logic_signature(dict(record.definition))
        if signature not in kept_by_signature:
            kept_by_signature[signature] = record
            continue
        kept = kept_by_signature[signature]
        room.disqualify(
            record.room_record_id,
            reason="shared_underlying_logic_family",
            evidence={
                "logic_signature": signature,
                "retained_room_record_id": kept.room_record_id,
                "retained_operation_id": kept.operation_id,
                "new_policy": "distinct_bottom_logic_and_distinct_behavior_v0.1",
            },
        )
        disqualified.append(
            {
                "room_record_id": record.room_record_id,
                "operation_id": record.operation_id,
                "same_logic_as": kept.room_record_id,
                "logic_signature": signature,
            }
        )

    active_after = list(room.records)
    shortage = max(0, MINIMUM_DISTINCT_FORMULAS - len(active_after))
    report = {
        "report_version": "formula-logic-diversity-audit-v0.1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy": {
            "minimum_formula_count": MINIMUM_DISTINCT_FORMULAS,
            "distinct_bottom_logic_required": True,
            "distinct_verified_behavior_required": True,
            "ancestor_compositions_do_not_count_as_independent_logic": True,
        },
        "active_before": len(active_before),
        "disqualified_count": len(disqualified),
        "active_after": len(active_after),
        "formula_shortage": shortage,
        "minimum_requirement_met": shortage == 0,
        "retained_records": [record.to_dict() for record in active_after],
        "disqualified_records": disqualified,
        "historical_records_preserved": len(room.historical_records),
        "room_path": room_path.relative_to(PROJECT_ROOT).as_posix(),
    }
    report_path = room_path.parent / "diversity_audit_latest.json"
    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
