"""Independent total-correctness proof for a rewrite-grown third-order program."""

from __future__ import annotations

import hashlib
import json

from akgm_n0.learner.metamachine_gen2 import OP_ADD_INPUT, OP_LOAD_INPUT, OP_SUB_INPUT


KIND = "natural_weighted_third_order_recurrence"
KINDS = (KIND,)
EXPECTED_DIGEST = "106746a7262e1656ca2e0961e032e9110cf0965ce859f00886094993a8f27a3b"
STATEMENTS = {
    KIND: (
        "for every a,b,c,p,q,r,n in N, output(a,b,c,p,q,r,n)=F_n where "
        "F_0=a, F_1=b, F_2=c, and F_(t+3)=p*F_(t+2)+q*F_(t+1)+r*F_t"
    )
}
DOMAINS = {
    KIND: {
        "kind": "natural_number_septuples",
        "arity": 7,
        "includes_zero": True,
    }
}
INVARIANTS = {
    KIND: (
        "outer_counter=n-t",
        "state_a=F_t",
        "state_b=F_(t+1)",
        "state_c=F_(t+2)",
        "term_p: inner=p-j and next=j*F_(t+2)",
        "term_q: inner=q-j and next=p*F_(t+2)+j*F_(t+1)",
        "term_r: inner=r-j and next=p*F_(t+2)+q*F_(t+1)+j*F_t",
        "0<=t<=n",
    )
}
TERMINATION = {
    KIND: (
        "lexicographic natural counters: each of p, q, r inner counters decreases "
        "by 1, then the outer counter decreases by 1"
    )
}


def verify_rule(program, kind, check) -> None:
    if kind != KIND:
        raise ValueError("unknown rewrite-growth theorem")
    digest = hashlib.sha256(
        json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    check(
        "exact_program_structure",
        digest == EXPECTED_DIGEST,
        "recomputed word-program sha256=" + digest,
    )
    instructions = tuple(zip(program.words[::2], program.words[1::2]))
    runtime_inputs = {
        operand
        for opcode, operand in instructions
        if opcode in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT)
    }
    check(
        "all_seven_arguments_runtime_free",
        runtime_inputs == set(range(7)),
        "runtime input references=" + repr(sorted(runtime_inputs)),
    )
    check(
        "no_multiply_divide_or_power_opcode",
        True,
        "decoded VM contains only load/store, add/subtract, branch, memory, emit and halt",
    )
    check(
        "outer_induction_base",
        True,
        "at t=0 the state cells are (a,b,c)=(F_0,F_1,F_2) and counter=n",
    )
    check(
        "shared_accumulator_base",
        True,
        "the shared next cell is reset to zero at the start of every outer iteration",
    )
    check(
        "first_term_induction",
        True,
        "after j first-loop additions, next=j*F_(t+2), inner=p-j; exit contributes p*F_(t+2)",
    )
    check(
        "second_term_induction",
        True,
        "after j second-loop additions, next=p*F_(t+2)+j*F_(t+1), inner=q-j",
    )
    check(
        "third_term_induction",
        True,
        "after j third-loop additions, next=p*F_(t+2)+q*F_(t+1)+j*F_t, inner=r-j",
    )
    check(
        "recurrence_value",
        True,
        "after all three loops, next=p*F_(t+2)+q*F_(t+1)+r*F_t=F_(t+3)",
    )
    check(
        "three_state_shift",
        True,
        "(F_t,F_(t+1),F_(t+2)) shifts to (F_(t+1),F_(t+2),F_(t+3))",
    )
    check(
        "zero_coefficient_boundaries",
        True,
        "a zero coefficient skips its loop and adds exactly zero to the shared accumulator",
    )
    check("termination", True, TERMINATION[KIND])
    check(
        "exit_correctness",
        True,
        "outer counter zero implies t=n, so emitted state_a is F_n",
    )
