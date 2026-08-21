from __future__ import annotations
import json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator.formula_rejection_room import FormulaRejectionRoom  # noqa:E402
from akgm_n0.evaluator.linear_algebra_foundation_v9 import run_linear_algebra_foundation_v9,replay_linear_algebra_foundation_v9  # noqa:E402
from akgm_n0.evaluator.linear_algebra_foundation_v9_room import LinearAlgebraFoundationV9Room  # noqa:E402
def main()->int:
    foundation=run_linear_algebra_foundation_v9();replay=replay_linear_algebra_foundation_v9(foundation)
    if not foundation["passed"] or not replay["passed"]:return 1
    room=LinearAlgebraFoundationV9Room(ROOT/"artifacts/foundation/v9/success/linear_algebra_foundation.jsonl");event=room.record(foundation);mistakes=FormulaRejectionRoom(ROOT/"artifacts/foundation/v9/mistakes/nonselected_linear_mechanisms.jsonl")
    labels=("index_contractions","quadratic_invariants","inverse_permutations","characteristic_reductions")
    for index,label in enumerate(labels):mistakes.record(reason="nonselected_anonymous_linear_mechanisms",candidate={"anonymous_search":label},evidence={"candidate_count":foundation["foundation"]["candidate_counts"][index],"exact_count":foundation["foundation"]["exact_counts"][index],"selected_semantic_id":foundation["proof"]["foundations"][index]["semantic_id"],"not_promoted":True})
    now=datetime.now(timezone.utc);run_id="RUN-linear-algebra-foundation-v9-"+now.strftime("%Y%m%dT%H%M%S%fZ");run_dir=ROOT/"artifacts/runs"/run_id;run_dir.mkdir(parents=True,exist_ok=False);report={"run_id":run_id,"created_at":now.isoformat().replace("+00:00","Z"),"verdict":"four_new_linear_algebra_foundations_levels_21_to_24_verified","foundation":foundation,"verification":replay,"rooms":{"success_path":"artifacts/foundation/v9/success/linear_algebra_foundation.jsonl","mistake_path":"artifacts/foundation/v9/mistakes/nonselected_linear_mechanisms.jsonl","verified_foundation_count":4,"bundle_event_count":len(room.records),"mistake_summary_count":len(mistakes.records),"latest_event_hash":event["event_hash"]}}
    artifact=run_dir/"linear_algebra_foundation_v9_report.json";artifact.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for d in (ROOT/"reports/data/linear_algebra_foundation_v9_latest.json",ROOT/"dashboard/data/linear_algebra_foundation_v9_latest.json",ROOT/"artifacts/foundation/v9/linear_algebra_foundation_v9_latest.json"):d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(artifact,d)
    print(json.dumps({"run_id":run_id,"levels":"21-24","new_foundations":4,"candidate_counts":foundation["foundation"]["candidate_counts"],"exact_counts":foundation["foundation"]["exact_counts"],"artifact_path":artifact.relative_to(ROOT).as_posix()},ensure_ascii=True,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
