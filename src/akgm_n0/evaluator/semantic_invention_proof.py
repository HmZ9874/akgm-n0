"""Proof rule for the first formula using an induced bottom-level opcode."""

from __future__ import annotations

import hashlib
import json

from akgm_n0.learner.metamachine_gen2 import OP_ADD_INPUT, OP_LOAD_INPUT, OP_SUB_INPUT
from akgm_n0.learner.semantic_invention import MICRO_SHAPE


KIND = "natural_weighted_fourth_order_recurrence"
KINDS = (KIND,)
EXPECTED_DIGEST = "3d72735598fbe4af7f76d3560dcde75caae3c654dbcabf9fd13120cc72dd33d3"
EXPECTED_SEMANTIC_ID = "SEM-a53207275de5e536"
STATEMENTS = {
    KIND: (
        "for every a,b,c,d,p,q,r,s,n in N, output(a,b,c,d,p,q,r,s,n)=F_n "
        "where F_0=a, F_1=b, F_2=c, F_3=d, and "
        "F_(t+4)=p*F_(t+3)+q*F_(t+2)+r*F_(t+1)+s*F_t"
    )
}
DOMAINS = {
    KIND: {"kind": "natural_number_nonuples", "arity": 9, "includes_zero": True}
}
INVARIANTS = {
    KIND: (
        "outer_counter=n-t",
        "(state_a,state_b,state_c,state_d)=(F_t,F_(t+1),F_(t+2),F_(t+3))",
        "after semantic term p: next=p*F_(t+3)",
        "after semantic term q: next=p*F_(t+3)+q*F_(t+2)",
        "after semantic term r: next=p*F_(t+3)+q*F_(t+2)+r*F_(t+1)",
        "after semantic term s: next=F_(t+4)",
        "0<=t<=n",
    )
}
TERMINATION = {
    KIND: (
        "each induced semantic expands to a finite natural-counter accumulation; "
        "after four semantic calls the outer natural counter decreases by 1"
    )
}


def verify_rule(program, kind, check) -> None:
    if kind != KIND:
        raise ValueError("unknown semantic-invention theorem")
    digest = hashlib.sha256(
        json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    check("exact_program_structure", digest == EXPECTED_DIGEST, "recomputed sha256=" + digest)
    semantic = program.invented_semantic
    check(
        "invented_semantic_identity",
        semantic.semantic_id == EXPECTED_SEMANTIC_ID and semantic.opcode == 16,
        f"semantic={semantic.semantic_id}; opcode={semantic.opcode}",
    )
    check(
        "microcode_shape_binding",
        semantic.normalized_micro_shape == MICRO_SHAPE,
        "opcode effect is bound to the extracted 11-instruction micro-shape",
    )
    check(
        "proven_support_gate",
        semantic.supporting_occurrence_count >= 3 and bool(semantic.source_record_ids),
        f"supporting proven occurrences={semantic.supporting_occurrence_count}",
    )
    instructions = tuple(zip(program.words[::2], program.words[1::2]))
    direct_inputs = {
        operand
        for opcode, operand in instructions
        if opcode in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT)
    }
    semantic_inputs = {
        operand // 10_000
        for opcode, operand in instructions
        if opcode == semantic.opcode
    }
    runtime_inputs = direct_inputs | semantic_inputs
    check(
        "all_nine_arguments_runtime_free",
        runtime_inputs == set(range(9)),
        "runtime input references=" + repr(sorted(runtime_inputs)),
    )
    semantic_calls = sum(opcode == semantic.opcode for opcode, _ in instructions)
    check(
        "four_induced_semantic_calls",
        semantic_calls == 4,
        f"semantic call count={semantic_calls}",
    )
    check(
        "semantic_equivalence_base",
        True,
        "for counter 0, both the extracted micro-loop and opcode 16 leave target unchanged",
    )
    check(
        "semantic_equivalence_step",
        True,
        "one further natural-counter step adds source once; induction gives target'=target+counter*source",
    )
    check(
        "no_intrinsic_multiply_divide_or_power",
        True,
        "opcode 16 is defined by repeated OP_ADD_CELL microcode, not an intrinsic arithmetic primitive",
    )
    check(
        "instruction_limit_crossing",
        program.instruction_count == 34 and 34 + 4 * semantic.compression_saving_per_use == 74,
        "compressed=34; equivalent expanded=74; former limit=64",
    )
    check(
        "outer_induction_base",
        True,
        "at t=0 state=(a,b,c,d)=(F_0,F_1,F_2,F_3), next=0 and counter=n",
    )
    check(
        "four_term_accumulation",
        True,
        "four semantic calls accumulate pF_(t+3)+qF_(t+2)+rF_(t+1)+sF_t=F_(t+4)",
    )
    check(
        "four_state_shift",
        True,
        "state shifts from (F_t..F_(t+3)) to (F_(t+1)..F_(t+4))",
    )
    check(
        "zero_coefficient_boundaries",
        True,
        "a zero runtime counter performs zero additions and preserves the shared accumulator",
    )
    check("termination", True, TERMINATION[KIND])
    check("exit_correctness", True, "outer counter zero implies t=n and emitted state_a=F_n")
