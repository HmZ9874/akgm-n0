from __future__ import annotations
import hashlib,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator.continuum_mechanics_v34 import run_v34_acceptance
def main():
 now=datetime.now(timezone.utc);rid="RUN-continuum-v34-"+now.strftime("%Y%m%dT%H%M%S%fZ");a=run_v34_acceptance()
 if not a["passed"]:raise RuntimeError([i["obligation_id"] for i in a["proof_obligations"] if not i["passed"]])
 r={"report_version":"continuum-mechanics-v34.0","run_id":rid,"created_at":now.isoformat(),"verdict":"finite_volume_continuum_conservation_verified","acceptance":a,"claim":{"achieved":"local mass/momentum fluxes, finite-volume balance, global conservation, and refinement transfer","not_claimed":"general viscous multidimensional continuum mechanics"}}
 rd=ROOT/"artifacts/runs"/rid;rd.mkdir(parents=True,exist_ok=True);art=rd/"continuum_report.json";mp=ROOT/"artifacts/physics/v34/mistakes/rejected_continuum_mutations.jsonl";mp.parent.mkdir(parents=True,exist_ok=True);mp.write_text("".join(json.dumps(i,ensure_ascii=False)+"\n" for i in a["mutation_audits"]),encoding="utf-8");r["storage"]={"success_room":"artifacts/physics/v34/success/continuum_latest.json","mistake_room":"artifacts/physics/v34/mistakes/rejected_continuum_mutations.jsonl"};r["content_digest"]=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest();art.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 for d in (ROOT/"reports/data/continuum_mechanics_v34_latest.json",ROOT/"dashboard/data/continuum_mechanics_v34_latest.json",ROOT/"artifacts/physics/v34/success/continuum_latest.json"):d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(art,d)
 g=a["mechanics_capability_graph"];print(json.dumps({"run_id":rid,"acceptance":"12/12","mass_flux":a["discovery"]["selected_mass_flux"]["opaque_program"],"momentum_flux":a["discovery"]["selected_momentum_flux"]["opaque_program"],"balance":a["discovery"]["selected_balance"]["opaque_program"],"mechanics_domains":f"{g['verified_domains']}/{g['total_domains']}","next_gap":g["next_selected_gap"]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
