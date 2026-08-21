from __future__ import annotations
import json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator.formula_rejection_room import FormulaRejectionRoom  # noqa:E402
from akgm_n0.evaluator.foundation_expansion_v8 import run_foundation_expansion_v8,replay_foundation_expansion_v8  # noqa:E402
from akgm_n0.evaluator.foundation_expansion_v8_room import FoundationExpansionV8Room  # noqa:E402

def main()->int:
    foundation=run_foundation_expansion_v8();replay=replay_foundation_expansion_v8(foundation)
    if not foundation["passed"] or not replay["passed"]:print(json.dumps({"foundation":foundation,"replay":replay},ensure_ascii=False,indent=2));return 1
    room=FoundationExpansionV8Room(ROOT/"artifacts/foundation/v8/success/foundation_expansion.jsonl");event=room.record(foundation)
    mistakes=FormulaRejectionRoom(ROOT/"artifacts/foundation/v8/mistakes/nonselected_mechanisms.jsonl")
    labels=("quotient_pair_candidates","bilinear_norm_candidates","inverse_enumeration_candidates","contraction_limit_candidates")
    for index,label in enumerate(labels):
        mistakes.record(reason="nonselected_anonymous_mechanisms",candidate={"anonymous_search":label},evidence={"candidate_count":foundation["expansion"]["candidate_counts"][index],"exact_count":foundation["expansion"]["exact_counts"][index],"selected_semantic_id":foundation["proof"]["foundations"][index]["semantic_id"],"nonselected_do_not_enter_foundation_room":True})
    now=datetime.now(timezone.utc);run_id="RUN-foundation-expansion-v8-"+now.strftime("%Y%m%dT%H%M%S%fZ");run_dir=ROOT/"artifacts/runs"/run_id;run_dir.mkdir(parents=True,exist_ok=False)
    report={"run_id":run_id,"created_at":now.isoformat().replace("+00:00","Z"),"verdict":"four_new_foundation_mechanisms_levels_17_to_20_verified","foundation":foundation,"verification":replay,"rooms":{"success_path":"artifacts/foundation/v8/success/foundation_expansion.jsonl","mistake_path":"artifacts/foundation/v8/mistakes/nonselected_mechanisms.jsonl","bundle_event_count":len(room.records),"verified_foundation_count":4,"mistake_summary_count":len(mistakes.records),"latest_event_hash":event["event_hash"]}}
    artifact=run_dir/"foundation_expansion_v8_report.json";artifact.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for destination in (ROOT/"reports/data/foundation_expansion_v8_latest.json",ROOT/"dashboard/data/foundation_expansion_v8_latest.json",ROOT/"artifacts/foundation/v8/foundation_expansion_v8_latest.json"):
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(artifact,destination)
    print(json.dumps({"run_id":run_id,"levels":"17-20","new_foundations":4,"candidate_counts":foundation["expansion"]["candidate_counts"],"exact_counts":foundation["expansion"]["exact_counts"],"artifact_path":artifact.relative_to(ROOT).as_posix()},ensure_ascii=True,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
