from __future__ import annotations
import hashlib,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator.constraint_mechanics_v29 import run_v29_acceptance
def main():
    now=datetime.now(timezone.utc); rid="RUN-constraint-v29-"+now.strftime("%Y%m%dT%H%M%S%fZ"); a=run_v29_acceptance()
    if not a["passed"]: raise RuntimeError([i["obligation_id"] for i in a["proof_obligations"] if not i["passed"]])
    r={"report_version":"constraint-mechanics-v29.0","run_id":rid,"created_at":now.isoformat(),"verdict":"constraint_and_generalized_coordinate_discovered","acceptance":a,"claim":{"achieved":"planar constraint projection and reversible one-scalar tangent representation","not_claimed":"arbitrary nonlinear manifolds or multi-body constraint solvers"}}
    rd=ROOT/"artifacts/runs"/rid; rd.mkdir(parents=True,exist_ok=True); art=rd/"constraint_mechanics_report.json"; mp=ROOT/"artifacts/physics/v29/mistakes/rejected_constraint_mutations.jsonl"; mp.parent.mkdir(parents=True,exist_ok=True); mp.write_text("".join(json.dumps(i,ensure_ascii=False)+"\n" for i in a["mutation_audits"]),encoding="utf-8")
    r["storage"]={"success_room":"artifacts/physics/v29/success/constraint_latest.json","mistake_room":"artifacts/physics/v29/mistakes/rejected_constraint_mutations.jsonl"}; r["content_digest"]=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest(); art.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
    for d in (ROOT/"reports/data/constraint_mechanics_v29_latest.json",ROOT/"dashboard/data/constraint_mechanics_v29_latest.json",ROOT/"artifacts/physics/v29/success/constraint_latest.json"): d.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(art,d)
    g=a["mechanics_capability_graph"]; print(json.dumps({"run_id":rid,"acceptance":"12/12","metric":a["discovery"]["selected_metric"]["opaque_program"],"tangent":a["discovery"]["selected_tangent"]["opaque_program"],"projection":a["discovery"]["selected_projection"]["opaque_program"],"mechanics_domains":f"{g['verified_domains']}/{g['total_domains']}","next_gap":g["next_selected_gap"]},ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
