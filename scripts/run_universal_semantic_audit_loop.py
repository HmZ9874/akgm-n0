from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    UniversalSemanticAuditLoop,
    UniversalSemanticAuditor,
    VerifiedEvolvedSemanticRoom,
)
from akgm_n0.learner import EvolvedMicroOperator  # noqa: E402


def main() -> int:
    source_report = json.loads(
        (ROOT / "reports/data/hundred_operator_evolution_latest.json").read_text(
            encoding="utf-8"
        )
    )
    operators = tuple(
        EvolvedMicroOperator.from_dict(item) for item in source_report["operators"]
    )
    # Loading this room replays the prior independent proof and its hash chain.
    source_room = VerifiedEvolvedSemanticRoom(
        ROOT / "artifacts/semantics/verified_evolved_semantics.jsonl"
    )
    source_ids = {event["operator"]["operator_id"] for event in source_room.records}
    if not {item.operator_id for item in operators}.issubset(source_ids):
        raise RuntimeError("source report contains a semantic absent from the proven room")

    loop = UniversalSemanticAuditLoop(maximum_rounds=10, stable_rounds_required=2)
    result = loop.run(operators)
    active_ids = {item["operator_id"] for item in result["active_operators"]}
    active_audit_by_id = {
        item["operator_id"]: item for item in result["active_audits"]
    }

    # A deliberately corrupted certificate is an evaluator-only negative control.
    # It never enters the active room and proves that removal is not a dead branch.
    first = operators[0]
    corrupted = replace(
        first,
        coefficient_vector=(999,) + first.coefficient_vector[1:],
    )
    negative_control = UniversalSemanticAuditor().audit(corrupted).to_dict()
    negative_control_loop = UniversalSemanticAuditLoop(
        maximum_rounds=10, stable_rounds_required=2
    ).run((corrupted,))
    negative_control_removed = (
        not negative_control["passed"]
        and negative_control_loop["converged"]
        and len(negative_control_loop["active_operators"]) == 0
        and len(negative_control_loop["rejected"]) == 1
    )

    active_catalog = {
        "schema_version": "active-universally-audited-semantics-v0.1",
        "source_run_id": source_report["run_id"],
        "active_count": len(result["active_operators"]),
        "active_digest": result["active_digest"],
        "domain_contract": UniversalSemanticAuditor.DOMAIN,
        "operators": [
            {
                "operator": operator,
                "universal_audit": active_audit_by_id[operator["operator_id"]],
            }
            for operator in result["active_operators"]
        ],
    }
    active_path = ROOT / "artifacts/semantics/active_evolved_semantics.json"
    active_path.write_text(
        json.dumps(active_catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rejected_path = ROOT / "artifacts/mistakes/rejected_semantics.jsonl"
    if result["rejected"]:
        rejected_path.parent.mkdir(parents=True, exist_ok=True)
        with rejected_path.open("a", encoding="utf-8", newline="\n") as stream:
            for item in result["rejected"]:
                stream.write(
                    json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
            stream.flush()
            os.fsync(stream.fileno())

    audits = result["active_audits"]
    natural_safe_count = sum(item["natural_number_safe"] for item in audits)
    total_obligations = sum(len(item["obligations"]) for item in audits)
    passed_obligations = sum(
        sum(obligation["passed"] for obligation in item["obligations"])
        for item in audits
    )
    gates = [
        {
            "gate_id": "audit_loop_reached_fixed_point",
            "passed": result["converged"],
            "actual": result["rounds"][-1]["stable_round_count"],
            "required": 2,
        },
        {
            "gate_id": "every_active_semantic_has_universal_domain_proof",
            "passed": all(item["passed"] for item in audits),
            "actual": sum(item["passed"] for item in audits),
            "required": len(audits),
        },
        {
            "gate_id": "all_free_group_normal_form_obligations_pass",
            "passed": passed_obligations == total_obligations,
            "actual": passed_obligations,
            "required": total_obligations,
        },
        {
            "gate_id": "failed_semantic_is_removed_from_active_catalog",
            "passed": negative_control_removed,
            "actual": 1 if negative_control_removed else 0,
            "required": 1,
        },
        {
            "gate_id": "active_catalog_contains_no_failed_audit",
            "passed": not any(not item["passed"] for item in audits),
            "actual": sum(not item["passed"] for item in audits),
            "required": 0,
        },
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-universal-semantic-audit-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    report = {
        "report_version": "universal-semantic-audit-loop-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "active_operator_library_reached_universally_proven_fixed_point",
        "meaning_of_universal": {
            "formal_domain": UniversalSemanticAuditor.DOMAIN,
            "proof_rule": "unique normal form in the free abelian group",
            "not_claimed": "valid in every possible mathematical structure regardless of whether subtraction is defined",
        },
        "loop": {
            "input_operator_count": len(operators),
            "active_operator_count": len(result["active_operators"]),
            "removed_operator_count": len(result["rejected"]),
            "round_count": len(result["rounds"]),
            "converged": result["converged"],
            "rounds": result["rounds"],
            "active_digest": result["active_digest"],
        },
        "proof_summary": {
            "active_semantics_passed": sum(item["passed"] for item in audits),
            "active_semantics_total": len(audits),
            "obligations_passed": passed_obligations,
            "obligations_total": total_obligations,
            "natural_number_safe_without_subtraction_count": natural_safe_count,
            "requires_additive_inverse_count": len(audits) - natural_safe_count,
        },
        "negative_control": {
            "description": "corrupt the first operator coefficient certificate to 999",
            "audit": negative_control,
            "isolated_loop_rounds": negative_control_loop["rounds"],
            "removed_from_active_catalog": negative_control_removed,
        },
        "active_catalog": {
            "path": "artifacts/semantics/active_evolved_semantics.json",
            "count": len(result["active_operators"]),
            "contains_only_passed_audits": True,
        },
        "rejection_room": {
            "path": "artifacts/mistakes/rejected_semantics.jsonl",
            "new_actual_rejections": len(result["rejected"]),
            "history_is_preserved": True,
        },
        "gates": gates,
        "limitations": [
            "No nontrivial expression is meaningful in literally every mathematical structure; the audit therefore uses an explicit algebraic domain contract.",
            "A semantic can be universally correct as an operator definition without being useful for every problem.",
            "Natural numbers are not closed under unrestricted subtraction, so subtraction-based operators are tagged as requiring additive inverses rather than falsely claimed as N-to-N total functions.",
            "Removal means exclusion from the active catalog; immutable proof and rejection history are retained for auditability.",
        ],
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    artifact = run_dir / "universal_semantic_audit_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/universal_semantic_audit_latest.json",
        ROOT / "dashboard/data/universal_semantic_audit_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    _append_ledger_event(
        ROOT / "artifacts/semantics/universal_audit_ledger.jsonl",
        {
            "run_id": run_id,
            "timestamp": report["created_at"],
            "source_run_id": source_report["run_id"],
            "active_count": len(result["active_operators"]),
            "removed_count": len(result["rejected"]),
            "active_digest": result["active_digest"],
            "gates": gates,
        },
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "loop_rounds": len(result["rounds"]),
                "input_operators": len(operators),
                "active_operators": len(result["active_operators"]),
                "removed_operators": len(result["rejected"]),
                "universal_proofs": f"{sum(item['passed'] for item in audits)}/{len(audits)}",
                "proof_obligations": f"{passed_obligations}/{total_obligations}",
                "negative_control_removed": negative_control_removed,
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _append_ledger_event(path: Path, payload: Mapping[str, Any]) -> None:
    previous_hash = "0" * 64
    event_index = 0
    if path.exists():
        lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        if lines:
            previous_hash = lines[-1]["event_hash"]
            event_index = len(lines)
    event = {
        "schema_version": "universal-audit-ledger-event-v0.1",
        "event_index": event_index,
        **dict(payload),
        "previous_event_hash": previous_hash,
    }
    event["event_hash"] = hashlib.sha256(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == "__main__":
    raise SystemExit(main())
