from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from run_calce_v52_discovery import common_effect


ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    sealed_report = json.loads(
        (ROOT / "artifacts" / "v522_calce_sealed_report.json").read_text(encoding="utf-8")
    )
    rows = read_jsonl(ROOT / "data" / "calce_v522" / "all_nonsealed_anonymous.jsonl")
    rows += read_jsonl(ROOT / "data" / "calce_v522" / "sealed_anonymous.jsonl")
    effects = []
    for window in (0.2, 0.6, 1.0):
        subset = [
            row
            for row in rows
            if float(row["control_0"]) == 0.5 and float(row["control_1"]) == window
        ]
        effects.append({"soc_window": window, **common_effect(subset, 0.5, 2.0)})
    report = {
        "schema": "akgm-n0-calce-v52.2-dashboard-v1",
        "verdict": "REAL_DATA_EXPERIMENT_COMPLETED_NO_BREAKTHROUGH",
        "sealed_status": sealed_report["status"],
        "sealed_prediction": {
            "forged_rmse": sealed_report["integrated_capacity_metrics"]["forged_program"],
            "best_baseline": sealed_report["integrated_best_baseline"],
            "best_baseline_rmse": sealed_report["integrated_capacity_metrics"][
                sealed_report["integrated_best_baseline"]
            ],
            "error_ratio": sealed_report["integrated_prediction_error_ratio"],
            "threshold": sealed_report["registered_threshold"],
            "logger_crosscheck_ratio": sealed_report["logger_prediction_error_ratio"],
            "crosscheck_preserved_conclusion": sealed_report[
                "parser_crosscheck_preserves_conclusion"
            ],
        },
        "matched_rate_effects": effects,
        "development_search": {
            "candidate_programs": 6675,
            "anonymous_atoms": 35,
            "leave_group_out_rmse": 0.0436627360531,
            "selected_expression": "response_hat = 1 - 0.141097440053*index - 0.671259934756*square_throughput*c1 - 0.1175932029*square_throughput*c2",
        },
        "experiment_timeline": [
            {
                "version": "V52",
                "status": "registered_validation_failure",
                "reason": "Program error ratio 1.1909; a doubled first-cycle layout exposed a parser defect.",
            },
            {
                "version": "V52.1",
                "status": "preprocessing_failure_before_search",
                "reason": "A micro-discharge bookkeeping tail passed the absolute threshold.",
            },
            {
                "version": "V52.2",
                "status": "registered_sealed_failure",
                "reason": "Parser audit passed, but the frozen program did not beat the online last-observation baseline.",
            },
        ],
        "capability_scores": {
            "autonomous_representation_creation": 9,
            "causal_mechanism_reasoning": 9,
            "human_unknown_scientific_law": 3,
        },
        "prior_art_audit": {
            "novelty": "not_novel",
            "official_experiment_article": "https://web.calce.umd.edu/articles/abstracts/2016/16_cycle_life_testing_modeling_li-ion_battery_different_SOC_ranges.html",
            "finding": "The 2016 CALCE study already reported significant capacity-loss effects from mean SOC, delta SOC, and discharge rate.",
        },
        "honest_boundary": [
            "The assigned-rate effects are bounded to the CALCE graphite/LiCoO2 pouch-cell experiment.",
            "Internal heating was not measured in the registered snapshot, so direct and temperature-mediated rate effects are not separated.",
            "The matched groups contain two cells per condition; this is not broad independent replication.",
            "No human-unknown law or breakthrough was established.",
        ],
    }
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    targets = [
        ROOT / "reports" / "data" / "calce_v522_latest.json",
        ROOT / "dashboard" / "data" / "calce_v522_latest.json",
    ]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        print(target.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
