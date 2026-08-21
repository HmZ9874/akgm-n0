from __future__ import annotations
import hashlib,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator.hamiltonian_mechanics_v33 import run_v33_acceptance
def main():
 now=datetime.now(timezone.utc);rid="RUN-hamiltonian-v33-"+now.strftime("%Y%m%dT%H%M%S%fZ");a=run_v33_acceptance()
 if not a["passed"]:raise RuntimeError([i["obligation_id"] for i in a["proof_obligations"] if not i["passed"]])
 r={"report_version":"hamiltonian-mechanics-v33.0","run_id":rid,"created_at":now.isoformat(),"verdict":"canonical_hamiltonian_and_symplectic_map_verified","acceptance":a,"claim":{"achieved":"canonical momentum, phase flows, Hamiltonian, and area-preserving step","not_claimed":"general nonlinear symplectic geometry"}}
 rd=ROOT/"artifacts/runs"/rid;rd.mkdir(parents=True,exist_ok=True);art=rd/"hamiltonian_report.json";mp=ROOT/"artifacts/physics/v33/mistakes/rejected_hamiltonian_mutations.jsonl";mp.parent.mkdir(parents=True,exist_ok=True);mp.write_text("".join(json.dumps(i,ensure_ascii=False)+"\n" for i in a["mutation_audits"]),encoding="utf-8");r["storage"]={"success_room":"artifacts/physics/v33/success/hamiltonian_latest.json","mistake_room":"artifacts/physics/v33/mistakes/rejected_hamiltonian_mutations.jsonl"};r["content_digest"]=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest();art.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 for d in (ROOT/"reports/data/hamiltonian_mechanics_v33_latest.json",ROOT/"dashboard/data/hamiltonian_mechanics_v33_latest.json",ROOT/"artifacts/physics/v33/success/hamiltonian_latest.json"):d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(art,d)
 g=a["mechanics_capability_graph"];print(json.dumps({"run_id":rid,"acceptance":"12/12","momentum":a["discovery"]["selected_momentum"]["opaque_program"],"q_flow":a["discovery"]["selected_q_flow"]["opaque_program"],"p_flow":a["discovery"]["selected_p_flow"]["opaque_program"],"hamiltonian":a["discovery"]["selected_hamiltonian"]["opaque_program"],"mechanics_domains":f"{g['verified_domains']}/{g['total_domains']}","next_gap":g["next_selected_gap"]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
