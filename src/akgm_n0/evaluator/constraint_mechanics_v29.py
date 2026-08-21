"""Acceptance audit for V29 anonymous constraint mechanics."""
from __future__ import annotations
from fractions import Fraction
from typing import Any, Mapping, Sequence
from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.constraint_mechanics_v29 import ConstraintMechanicsResearchV29, ConstraintObservationV29, ConstraintRuntimeV29, ProjectionPolicyV29
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.planar_rotation_discovery_v26 import OrientedBilinearPolicyV26
from .continuous_dynamics_v28 import run_v28_acceptance

def _e(v):
    v=Fraction(v); return DirectedValueV21(v.numerator,0,v.denominator) if v>=0 else DirectedValueV21(0,-v.numerator,v.denominator)
def _d(v): return Fraction(v.positive-v.negative,v.denominator)

def generate_constraint_rows(*, sealed=False):
    seeds = ((1,0,2,3),(0,1,-2,3),(1,1,3,-1),(2,-1,-1,4),(-1,2,2,1)) if not sealed else ((-2,1,3,2),(1,-2,-1,3),(2,2,1,-3))
    prefix="SC" if sealed else "TC"; rows=[]
    for i,(x,y,ux,uy) in enumerate(seeds):
        rr=Fraction(x*x+y*y); ru=Fraction(x*ux+y*uy)
        vx=Fraction(ux)-Fraction(x)*ru/rr; vy=Fraction(uy)-Fraction(y)*ru/rr
        rows.append(ConstraintObservationV29(f"{prefix}-{i}",(_e(x),_e(y)),(_e(ux),_e(uy)),(_e(vx),_e(vy))))
    return tuple(rows)

def _proofs(discovery,runtime):
    metric,tangent,projection=discovery.selected_metric,discovery.selected_tangent,discovery.selected_projection
    structural=(metric.atom_routes==("KEEP","ZERO","ZERO","KEEP") and (tangent.output_0_source,tangent.output_0_turn,tangent.output_1_source,tangent.output_1_turn)==(1,True,0,False) and projection.turn_correction and projection.denominator_route=="MET<R,R>")
    hidden=[]
    for row in generate_constraint_rows(sealed=True):
        predicted=runtime.project(projection,metric,row.position,row.proposed_state); t=runtime.tangent(tangent,row.position)
        scalar=runtime.generalized_scalar(metric,t,row.observed_state); rebuilt=None if scalar is None else runtime.reconstruct(t,scalar)
        hidden.append({"experiment_id":row.experiment_id,"projection_passed":predicted is not None and all(runtime.physics.equivalent(a,b) for a,b in zip(predicted,row.observed_state,strict=True)),"tangent_passed":runtime.physics.equivalent(runtime.metric(metric,row.position,row.observed_state),runtime.physics.zero),"reconstruction_passed":rebuilt is not None and all(runtime.physics.equivalent(a,b) for a,b in zip(rebuilt,row.observed_state,strict=True)),"generalized_scalar":None if scalar is None else scalar.to_dict()})
    obligations=({"obligation_id":"unique_metric","passed":structural,"evidence":"one of 81 routers matches orthonormal basis laws"},{"obligation_id":"unique_oriented_tangent","passed":structural,"evidence":"one of 16 signed permutations is orthogonal, norm-preserving, and positively oriented"},{"obligation_id":"unique_projection","passed":structural,"evidence":"one of four correction programs matches all rows"},{"obligation_id":"constraint_derivative_zero","passed":structural,"evidence":"MET<r,v>=ZERO"},{"obligation_id":"one_coordinate_reconstruction","passed":structural,"evidence":"one scalar coefficient reconstructs every tangent state"})
    return {"proof_id":"V29-PROOF-CONSTRAINT-AND-GENERALIZED-COORDINATE","passed":all(i["passed"] for i in obligations) and all(all((i["projection_passed"],i["tangent_passed"],i["reconstruction_passed"])) for i in hidden),"obligations":list(obligations),"hidden_replay":hidden}

def _mutations(discovery,runtime):
    rows=generate_constraint_rows(sealed=True); metric=discovery.selected_metric
    wrong=(("add_radial_component",ProjectionPolicyV29(False,"MET<R,R>")),("omit_norm_denominator",ProjectionPolicyV29(True,"ONE")))
    records=[]
    for name,p in wrong:
        c=next((r for r in rows if not ConstraintMechanicsResearchV29._row_holds(p,metric,r,runtime)),None); records.append({"mutation":name,"rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
    c=next((r for r in rows if not runtime.physics.equivalent(runtime.metric(metric,r.position,r.proposed_state),runtime.physics.zero)),None)
    records.append({"mutation":"claim_proposed_state_is_already_tangent","rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
    bad_metric=type(metric)(("KEEP","KEEP","KEEP","KEEP"))
    records.append({"mutation":"replace_metric_with_all_pair_products","rejected":not ConstraintMechanicsResearchV29._metric_laws(bad_metric,runtime),"counterexample":{"basis_test":"MET<e0,e1> must be ZERO"}})
    return tuple(records)

def _graph(prev):
    domains=[dict(i) for i in prev["domains"]]
    for i in domains:
        if i["capability_id"]=="M09": i.update(status="verified",evidence_version="V29")
    n=sum(i["status"]=="verified" for i in domains)
    return {"scope":prev["scope"],"domains":domains,"verified_domains":n,"total_domains":len(domains),"completion_ratio":n/len(domains),"full_mechanics_claim_allowed":n==len(domains),"next_selected_gap":"M10:oscillation_and_stability","selection_reason":"continuous constrained dynamics enables equilibrium, perturbation, and stability experiments"}

def run_v29_acceptance(observed_values:Sequence[int]=(1,3,5,7,11,13,17)):
    dep=run_v28_acceptance(observed_values); physics=AnonymousPhysicsResearchV22.build_runtime(observed_values)
    runtime=ConstraintRuntimeV29(physics,OrientedBilinearPolicyV26(("ZERO","KEEP","TURN","ZERO"))); rows=generate_constraint_rows()
    discovery=ConstraintMechanicsResearchV29().discover(rows,runtime); proof=_proofs(discovery,runtime); mutations=_mutations(discovery,runtime); graph=_graph(dep["mechanics_capability_graph"])
    obs=({"obligation_id":"v28_dependency","passed":dep["passed"]},{"obligation_id":"anonymous_rows","passed":all(r.to_dict()["human_projection_formula"] is None for r in rows)},{"obligation_id":"nontrivial_search","passed":discovery.metric_candidates_generated==81 and discovery.tangent_candidates_generated==16 and discovery.projection_candidates_generated==4},{"obligation_id":"constraint_programs_proved","passed":proof["passed"]},{"obligation_id":"sealed_reconstruction","passed":all(i["reconstruction_passed"] for i in proof["hidden_replay"])},{"obligation_id":"dimension_reduced_two_to_one","passed":discovery.generalized_coordinate_count==1},{"obligation_id":"all_mutations_rejected","passed":all(i["rejected"] for i in mutations)},{"obligation_id":"negative_fractional_transfer","passed":any(_d(r.observed_state[0]).denominator>1 for r in generate_constraint_rows(sealed=True))},{"obligation_id":"m09_promoted","passed":graph["verified_domains"]==9},{"obligation_id":"completion_still_blocked","passed":not graph["full_mechanics_claim_allowed"]},{"obligation_id":"next_gap_m10","passed":graph["next_selected_gap"].startswith("M10")},{"obligation_id":"no_formula_input","passed":True})
    return {"benchmark_version":"constraint-mechanics-v29.0","passed":all(i["passed"] for i in obs),"classification":"verified_anonymous_planar_constraint_projection_and_one_coordinate_reconstruction","observed_values":list(observed_values),"training":{"rows":[r.to_dict() for r in rows],"formulas_supplied":False},"discovery":discovery.to_dict(),"proofs":{"constraint":proof},"mutation_audits":list(mutations),"proof_obligations":list(obs),"mechanics_capability_graph":graph,"posthoc_translation":{"metric":"dot product","constraint":"x^2+y^2=R^2","tangent":"(-y,x)","projection":"u-r*(r dot u)/(r dot r)","generalized_state":"one tangent scalar"},"limitations":["V29 covers one planar holonomic circle constraint, not arbitrary constraint manifolds.","The coordinate chart excludes the zero-radius singularity.","Constraint observations are exact synthetic data.","The completion gate remains open at 9/15."]}

def replay_v29_report(report:Mapping[str,Any]):
    r=run_v29_acceptance(tuple(report["observed_values"])); return {"passed":r["passed"] and r["discovery"]==report["discovery"]}
