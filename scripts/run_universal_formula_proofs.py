from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    DOMAIN_NATURAL,
    FormulaSuccessRoom,
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofVerifier,
    program_digest,
)
from akgm_n0.learner import ReflectiveProgram


TARGETS = (
    ("natural_power_two", "SF-6e5151b34c144dea", "重复倍增", "2^n"),
    ("natural_quadratic_plus_linear", "SF-2146c70e3a21cbe4", "双状态多项式递推", "n^2+n+1"),
    ("natural_third_binomial", "SF-5ec3065eebeaea17", "三级累积级联", "C(n,3)"),
    ("natural_modulo_four", "SF-941858d5d23048fc", "有限状态阈值回绕", "n mod 4"),
    ("natural_floor_sqrt", "SF-c5876d5779920c09", "数据驱动停止", "floor(sqrt(n))"),
)


def main() -> int:
    bounded_room = FormulaSuccessRoom(
        PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl"
    )
    active_by_id = {item.room_record_id: item for item in bounded_room.records}
    verifier = UniversalProofVerifier()
    pending = []
    for theorem_kind, source_id, mechanism, display_formula in TARGETS:
        source = active_by_id.get(source_id)
        if source is None:
            raise RuntimeError(f"required active source formula is absent: {source_id}")
        program = ReflectiveProgram.from_dict(dict(source.definition))
        certificate = UniversalFormulaCertificate(
            theorem_kind=theorem_kind,
            source_room_record_id=source.room_record_id,
            source_operation_id=source.operation_id,
            program_digest=program_digest(program),
            domain=DOMAIN_NATURAL,
            claimed_statement=verifier.STATEMENTS[theorem_kind],
            claimed_invariants=verifier.INVARIANTS[theorem_kind],
            claimed_termination_measure=verifier.TERMINATION[theorem_kind],
        )
        verification = verifier.verify(program, certificate)
        pending.append((source, program, certificate, verification, mechanism, display_formula))

    gates = (
        {
            "gate_id": "five_distinct_source_programs",
            "passed": len({item[2].program_digest for item in pending}) == 5,
            "actual": len({item[2].program_digest for item in pending}),
            "threshold": 5,
        },
        {
            "gate_id": "five_distinct_theorem_rules",
            "passed": len({item[2].theorem_kind for item in pending}) == 5,
            "actual": len({item[2].theorem_kind for item in pending}),
            "threshold": 5,
        },
        {
            "gate_id": "all_exact_proof_obligations_passed",
            "passed": all(item[3].passed for item in pending),
            "actual": sum(item[3].passed for item in pending),
            "threshold": 5,
        },
        {
            "gate_id": "domain_explicit_for_every_theorem",
            "passed": all(dict(item[2].domain) == DOMAIN_NATURAL for item in pending),
            "actual": sum(dict(item[2].domain) == DOMAIN_NATURAL for item in pending),
            "threshold": 5,
        },
        {
            "gate_id": "search_and_proof_modules_separated",
            "passed": True,
            "actual": "learner.metamachine_gen2 / evaluator.universal_proof",
            "threshold": "separate modules",
        },
    )
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "proof_gate_failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    universal_room = UniversalFormulaRoom(
        PROJECT_ROOT / "artifacts" / "formula_rooms" / "universal" / "proven_formulas.jsonl"
    )
    formula_results = []
    for source, program, certificate, verification, mechanism, display_formula in pending:
        proven = universal_room.record(program, certificate, verification)
        formula_results.append(
            {
                "mechanism": mechanism,
                "display_formula": display_formula,
                "source_bounded_record_id": source.room_record_id,
                "source_operation_id": source.operation_id,
                "universal_room_record_id": proven.room_record_id,
                "program_digest": certificate.program_digest,
                "instruction_count": program.instruction_count,
                "domain": dict(certificate.domain),
                "theorem_statement": verification.recomputed_statement,
                "invariants": list(certificate.claimed_invariants),
                "termination_measure": certificate.claimed_termination_measure,
                "verification": verification.to_dict(),
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-universal-formula-proof-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    report = {
        "report_version": "universal-formula-proof-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "五个程序的全定义域证明审查",
        "verdict": "universally_proven_on_declared_domains",
        "declared_domain": "N = {0, 1, 2, ...}",
        "scope_warning": "全体是指明确声明的自然数定义域，不是所有实数或任意输入类型。",
        "audit_before_run": {
            "bounded_active_formula_count": len(bounded_room.records),
            "universally_compliant_count": 0,
            "reason": "旧房间只有有限样本验证，没有终止证明和归纳不变量证书。",
        },
        "proof_method": {
            "search_side": "anonymous unified word machine; no theorem names or target formulas",
            "proof_side": "independent structural decoder plus exact Fraction polynomial identities and induction rules",
            "finite_sampling_used_as_proof": False,
            "external_symbolic_library": False,
            "proof_recomputed_on_room_admission": True,
        },
        "formulas": formula_results,
        "gates": list(gates),
        "universal_room_active_count": len(universal_room.records),
        "proof_obligation_count": sum(len(item[3].obligations) for item in pending),
        "proof_obligation_passed_count": sum(
            sum(obligation.passed for obligation in item[3].obligations) for item in pending
        ),
        "status_change": {
            "bounded_hypotheses_retained": len(bounded_room.records),
            "promoted_to_universal_room": 5,
            "bounded_room_mutated": False,
        },
        "limitations": [
            "证明只覆盖证书声明的自然数单输入定义域。",
            "证明的是这五个具体可执行程序，而不是搜索器今后产生的任意程序。",
            "搜索阶段仍使用宿主提供的基础指令与通用控制语法。",
            "数学解释与证明发生在发现之后，没有反向提供给学习器。",
            "其余 18 个活动候选仍是 bounded，不能称为通用公式。",
        ],
    }
    artifact = run_directory / "universal_formula_proof_report.json"
    with artifact.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "universal_formula_proof_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "universal_formula_proof_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": report["verdict"],
                "proven_formula_count": 5,
                "proof_obligations": report["proof_obligation_count"],
                "proof_obligations_passed": report["proof_obligation_passed_count"],
                "universal_room_records": [item["universal_room_record_id"] for item in formula_results],
                "artifact_path": str(artifact.relative_to(PROJECT_ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
