"""Run the V15 unified-substrate acceptance benchmark and publish evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.self_extending_substrate_v15 import run_v15_acceptance  # noqa: E402
from akgm_n0.learner.self_extending_substrate_v15 import (  # noqa: E402
    UnifiedCounterVM,
    UnifiedVMError,
    default_anonymous_tasks,
    migrated_training_programs,
    program_mutations,
)


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-self-extending-v15-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v15_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError("V15 acceptance benchmark failed")

    report = {
        "report_version": "self-extending-substrate-v15.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "unified_substrate_migration_and_meta_learning_acceptance_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "three task-specific strict search substrates plus later closure modules",
            "after": "one primitive counter VM, one recurrent proposal policy, one CEGIS controller, one macro miner, and one generic law miner",
            "specialized_runtime_searchers_required": False,
            "cold_start_autonomy_proven": False,
        },
        "claim": {
            "achieved": "audited strict memories run and reconstruct inside one shared self-improving substrate",
            "not_claimed": "cold-start invention of all three algorithms or unrestricted runtime opcode invention",
        },
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "self_extending_substrate_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/self_extending_substrate_v15_latest.json",
        ROOT / "dashboard/data/self_extending_substrate_v15_latest.json",
        ROOT / "artifacts/foundation/v15/success/self_extending_substrate_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    mistakes_path = ROOT / "artifacts/foundation/v15/mistakes/unified_vm_mutations.jsonl"
    mistakes_path.parent.mkdir(parents=True, exist_ok=True)
    vm = UnifiedCounterVM()
    tasks = default_anonymous_tasks()
    records = []
    for task_id, source in migrated_training_programs().items():
        for mutation in program_mutations(source)[:20]:
            failure = None
            for index, (inputs, expected) in enumerate(tasks[task_id].cases):
                try:
                    execution = vm.execute(mutation, inputs)
                    actual = execution.outputs
                    trace_tail = execution.trace[-4:]
                except UnifiedVMError as error:
                    actual = []
                    trace_tail = ()
                    failure = {"kind": "execution_error", "message": str(error)}
                if tuple(actual) != expected:
                    failure = failure or {"kind": "counterexample", "expected": list(expected), "actual": list(actual)}
                    records.append({
                        "schema_version": "unified-vm-mistake-v15.1",
                        "task_id": task_id,
                        "candidate_id": mutation.program_id,
                        "case_index": index,
                        "inputs": list(inputs),
                        "failure": failure,
                        "trace_tail": [[pc, op, list(registers)] for pc, op, registers in trace_tail],
                    })
                    break
    mistakes_path.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records), encoding="utf-8")

    report["storage"] = {
        "success_report": "artifacts/foundation/v15/success/self_extending_substrate_latest.json",
        "mistake_room": str(mistakes_path.relative_to(ROOT)).replace("\\", "/"),
        "mistakes_recorded": len(records),
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps({key: value for key, value in report.items() if key != "content_digest"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/self_extending_substrate_v15_latest.json",
        ROOT / "dashboard/data/self_extending_substrate_v15_latest.json",
        ROOT / "artifacts/foundation/v15/success/self_extending_substrate_latest.json",
    ):
        shutil.copyfile(artifact, destination)

    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "reconstructions": sum(item["converged"] for item in acceptance["reconstructions"]),
        "search_reduction": acceptance["aggregate"]["evaluation_reduction"],
        "cross_task_macros": len(acceptance["macros"]),
        "mistakes_recorded": len(records),
        "classification": acceptance["classification"],
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
