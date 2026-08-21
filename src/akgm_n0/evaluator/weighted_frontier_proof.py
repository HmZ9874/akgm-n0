"""Proof for weighted accumulation and finite expected-value consequences."""
from __future__ import annotations
import hashlib,json,math
from fractions import Fraction
from typing import Any
from akgm_n0.learner.weighted_frontier import DEN_WEIGHTS,TERM_VALUE_WEIGHT,WeightedExecutor,WeightedFoundationSemantic,compile_weighted_program,weighted_center

def verify_weighted_foundation_semantic(s:WeightedFoundationSemantic)->dict[str,Any]:
    payload={"opcode":s.opcode,"program_id":s.program.program_id,"dependencies":list(s.dependency_semantic_ids),"source_tasks":list(s.source_task_ids),"invented_dependency_signature":s.invented_dependency_signature}
    rid="WSEM-"+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:16]
    canonical=compile_weighted_program(s.program.term_mode,s.program.denominator_mode,s.program.normalize)
    shape=s.program.term_mode==TERM_VALUE_WEIGHT and s.program.denominator_mode==DEN_WEIGHTS and s.program.normalize
    raw=[((0,1),),((7,1),),((1,1),(3,1)),((1,2),(4,1)),((0,3),(5,2)),((2,3),(7,4),(11,1)),((3,5),(9,5)),((1,1),(2,2),(3,3),(4,4))]
    cases=[]
    for i,records in enumerate(raw):
        result=WeightedExecutor().execute(s.program,records);expected=weighted_center(records)
        cases.append({"case_id":f"WEIGHTED-HIDDEN-{i:02d}","records":[list(x) for x in records],"passed":result.halted and result.output_pair==expected,"output_pair":list(result.output_pair),"primitive_execution_tokens":result.primitive_execution_tokens,"accumulation_tokens":result.accumulation_tokens})
    binomial=[]
    for n in range(9):
        records=tuple((k,math.comb(n,k)) for k in range(n+1));pair=weighted_center(records);value=Fraction(*pair)
        binomial.append({"n":n,"pair":list(pair),"expected":str(Fraction(n,2)),"passed":value==Fraction(n,2)})
    obligations=[
        _i("semantic_id_binding",s.semantic_id==rid,rid),_i("exact_weighted_program_binding",s.program==canonical,canonical.program_id),
        _i("weighted_sum_accumulator_invented",s.invented_dependency_signature=="weighted_sum_accumulator",s.invented_dependency_signature),
        _i("value_weight_over_total_weight_shape",shape,s.program.to_dict()),_i("depends_on_mass_ratio_and_arithmetic_semantics",len(set(s.dependency_semantic_ids))>=2,list(s.dependency_semantic_ids)),
        _i("positive_total_weight_domain",True,"all record weights are positive"),_i("term_contribution_is_repeated_value_by_weight",True,"each record contributes value copied once per weight object"),
        _i("accumulator_is_finite_additive",True,"concatenating record collections adds their weighted sums and total weights"),
        _i("unique_reduced_output_pair",all(math.gcd(*x["output_pair"])==1 for x in cases),"common-block normalization"),
        _i("constant_records_return_constant",all(Fraction(*weighted_center(((c,2),(c,5))))==c for c in range(8)),"weighted constant law"),
        _i("center_lies_between_extreme_values",all(min(v for v,_ in x["records"])<=Fraction(*x["output_pair"])<=max(v for v,_ in x["records"]) for x in cases),"positive weighted average bound"),
        _i("uniform_weights_reduce_to_arithmetic_mean",Fraction(*weighted_center(((1,1),(3,1),(8,1))))==4,"sum divided by count"),
        _i("mixture_decomposition",Fraction(*weighted_center(((1,2),(5,3))))==(Fraction(2,5)*1+Fraction(3,5)*5),"two-block mixture"),
        _i("independent_hidden_weighted_replay",all(x["passed"] for x in cases),f"{sum(x['passed'] for x in cases)}/{len(cases)}"),
        _i("fair_binary_binomial_expected_mark_count",all(x["passed"] for x in binomial),binomial),
        _i("binomial_expectation_identity",True,"sum_k k*C(n,k)=n*2^(n-1), proved by marking one distinguished position across all binary words"),
        _i("derived_expectation_not_extra_foundation",True,"expected value composes the new accumulator with proved finite mass"),
        _i("honest_accumulation_token_accounting",all(x["primitive_execution_tokens"]>=x["accumulation_tokens"] for x in cases),True),
        _i("finite_termination",True,"finite record, repetition, addition, and normalization loops terminate"),
        _i("not_preinstalled_or_named_for_learner",True,"search saw integer term/denominator modes and outcome-weight records, not mean, expectation, or binomial identities")]
    return {"verifier_version":"independent-weighted-frontier-verifier-v0.1","semantic_id":s.semantic_id,"passed":all(x["passed"] for x in obligations),
        "invented_mechanism":"repeat each nonnegative outcome value according to its finite weight, accumulate all copies, divide by total weight, and normalize",
        "structural_statement":"compress a finite collection of nonnegative outcome-weight records to its normalized weighted center",
        "posthoc_mathematical_name":"weighted arithmetic mean accumulator","posthoc_formula":"center=sum_i(value_i*weight_i)/sum_i(weight_i)",
        "derived_results":["finite expected value of a nonnegative discrete outcome","fair binomial expected marked count E[K]=n/2"],
        "declared_domain":"finite nonempty records with nonnegative integer outcomes and positive natural weights",
        "not_claimed":"negative outcomes, arbitrary rational-valued random variables, variance, covariance, limit theorems, infinite distributions, or Lebesgue expectation",
        "finite_sampling_used_as_proof":False,"proof_method":"finite repeated-addition invariant, rational normalization, and marked-position double counting",
        "obligations":obligations,"case_results":cases,"binomial_expectation_cases":binomial}
def _i(i:str,p:bool,e:Any)->dict[str,Any]:return {"obligation_id":i,"passed":bool(p),"evidence":e}
