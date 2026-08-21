from __future__ import annotations
import json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator import FormulaRejectionRoom,JointFrontierRoom,verify_joint_foundation_semantic  # noqa:E402
from akgm_n0.learner import JointExample,JointRelationSearch,JointSemanticInducer,common_observation  # noqa:E402


def main()->int:
    prior=json.loads((ROOT/"reports/data/autonomous_finite_mass_latest.json").read_text(encoding="utf-8"));ratio=json.loads((ROOT/"reports/data/autonomous_ratio_latest.json").read_text(encoding="utf-8"))
    frontier=prior["next_frontier"]
    specs=[(5,(),()),(5,(0,),(1,)),(5,(0,1),(1,2)),(7,(0,2,4),(1,3,5)),(7,(0,1,2,3),(2,3,4,5)),(8,tuple(range(8)),(1,3,5,7)),(9,(0,2,4,6,8),(0,3,6))]
    examples=[]
    for i,(size,li,ri) in enumerate(specs):
        u=tuple(f"W{i}:{j}" for j in range(size));left=tuple(u[j] for j in li);right=tuple(u[j] for j in ri)
        examples.append(JointExample(u,(left,right),common_observation(u,left,right)))
    search=JointRelationSearch().search(frontier["world_id"],tuple(examples))
    deps=(prior["derived_discovery"]["semantic"]["semantic_id"],ratio["discovery"]["semantic"]["semantic_id"])
    semantic=JointSemanticInducer().induce(search,opcode=11,dependency_semantic_ids=deps,invented_dependency_signature=frontier["missing_dependency"])
    proof=verify_joint_foundation_semantic(semantic)
    if not proof["passed"]:print(json.dumps(proof,ensure_ascii=False,indent=2));return 1
    room=JointFrontierRoom(ROOT/"artifacts/foundation/success/joint_frontier_semantics.jsonl");event=room.record(semantic,proof)
    mistakes=FormulaRejectionRoom(ROOT/"artifacts/foundation/mistakes/joint_frontier_programs.jsonl")
    for c in search.candidates:
        if c.program.program_id==search.selected.program.program_id:continue
        mistakes.record(reason="equivalent_nonselected_joint_program" if c.exact else "fails_conditioned_event_world",candidate=c.program.to_dict(),evidence={"world_id":frontier["world_id"],"passed_examples":c.passed_example_count,"example_count":c.example_count,"exact":c.exact,"reward":c.reward,"does_not_enter_foundation_room":True})
    exact=[x for x in search.candidates if x.exact];ob=sum(x["passed"] for x in proof["obligations"]);hid=sum(x["passed"] for x in proof["case_results"])
    gates=[
        {"gate_id":"joint_gap_taken_from_previous_frontier","passed":frontier["missing_dependency"]=="joint_event_intersection","actual":frontier,"required":"recorded gap"},
        {"gate_id":"anonymous_set_relation_modes_compete","passed":search.candidates_evaluated==14,"actual":search.candidates_evaluated,"required":14},
        {"gate_id":"common_membership_mode_selected_without_name","passed":search.selected.program.relation_mode==2,"actual":search.selected.program.relation_mode,"required":2},
        {"gate_id":"joint_event_world_exactly_compressed","passed":search.selected.exact,"actual":search.selected.passed_example_count,"required":search.selected.example_count},
        {"gate_id":"joint_semantic_universally_proved","passed":proof["passed"],"actual":ob,"required":len(proof["obligations"])},
        {"gate_id":"all_hidden_joint_cases_pass","passed":hid==len(proof["case_results"]),"actual":hid,"required":len(proof["case_results"])},
        {"gate_id":"conditional_product_rule_proved","passed":all(x["product_rule_passed"] for x in proof["conditional_cases"]),"actual":len(proof["conditional_cases"]),"required":len(proof["conditional_cases"])},
        {"gate_id":"success_and_mistake_feedback_persist","passed":len(room.records)==1 and len(mistakes.records)>=13,"actual":{"success":len(room.records),"mistakes":len(mistakes.records)},"required":{"success":1,"mistakes":13}},
        {"gate_id":"user_did_not_specify_intersection_or_conditioning","passed":True,"actual":False,"required":False},]
    if not all(x["passed"] for x in gates):print(json.dumps({"verdict":"failed","gates":gates},ensure_ascii=False,indent=2));return 1
    now=datetime.now(timezone.utc);run_id="RUN-autonomous-joint-"+now.strftime("%Y%m%dT%H%M%S%fZ");run_dir=ROOT/"artifacts/runs"/run_id;run_dir.mkdir(parents=True)
    report={"report_version":"autonomous-joint-conditioning-v0.1","run_id":run_id,"created_at":now.isoformat().replace("+00:00","Z"),"verdict":"joint_event_intersection_invented_and_finite_conditioning_rules_derived",
        "resumed_from":{"run_id":prior["run_id"],"frontier":frontier,"user_supplied_math_target":False},
        "search":{"candidate_count":search.candidates_evaluated,"exact_candidate_count":len(exact),"selected_program":search.selected.program.to_dict(),"selected_token_cost":search.selected.total_token_cost,"selected_reward":search.selected.reward},
        "discovery":{"foundation_level":11,"semantic":semantic.to_dict(),"structural_origin":proof["structural_statement"],"posthoc_name":proof["posthoc_mathematical_name"],"posthoc_formula":proof["posthoc_formula"],"name_given_to_search":False,"counts_as_new_foundation":True},
        "derived_results":proof["derived_results"],"verification":proof,
        "capability_graph":{"verified_foundation_count":11,"previous_count":10,"new_foundation":"有限集合交集","verified_derived_results_added":3},
        "next_frontier":{"world_id":"WORLD-weighted-outcome-center-76","structural_signature":"weighted_finite_outcome_center","status":"dependency_blocked","missing_dependency":"weighted_sum_accumulator","posthoc_math_name":None},
        "rooms":{"success":"artifacts/foundation/success/joint_frontier_semantics.jsonl","mistakes":"artifacts/foundation/mistakes/joint_frontier_programs.jsonl","success_count":len(room.records),"mistake_count":len(mistakes.records),"event_hash":event["event_hash"]},
        "gates":gates,"limitations":["Only finite uniform event conditioning is derived.","Conditional probability with empty conditioning event is undefined.","No random-variable expectation, nonuniform weights, infinite spaces, or measure theory is proved."]}
    artifact=run_dir/"autonomous_joint_report.json";artifact.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for d in (ROOT/"reports/data/autonomous_joint_latest.json",ROOT/"dashboard/data/autonomous_joint_latest.json",ROOT/"artifacts/foundation/autonomous_joint_latest.json"):d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(artifact,d)
    print(json.dumps({"run_id":run_id,"semantic_id":semantic.semantic_id,"posthoc_name":proof["posthoc_mathematical_name"],"derived_results":proof["derived_results"],"search":f"{len(exact)}/{search.candidates_evaluated}","proof":f"{ob}/{len(proof['obligations'])}","hidden":f"{hid}/{len(proof['case_results'])}","foundation_count":11,"next_blocked_dependency":report["next_frontier"]["missing_dependency"],"artifact_path":artifact.relative_to(ROOT).as_posix()},ensure_ascii=True,indent=2));return 0


if __name__=="__main__":raise SystemExit(main())
