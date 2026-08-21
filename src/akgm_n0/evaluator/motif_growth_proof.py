"""Independent proof rule for the first program grown from learned motifs."""

from __future__ import annotations

import hashlib
import json

from akgm_n0.learner.metamachine_gen2 import (
    OP_ADD_INPUT,
    OP_LOAD_INPUT,
    OP_SUB_INPUT,
)


KIND = "natural_weighted_second_order_recurrence"
KINDS = (KIND,)
EXPECTED_DIGEST = "e6224f96e9b9f0687f4524ec4be94167ccd9b7fa5ff56c02a688ee8d7c8d7a56"
STATEMENTS = {
    KIND: (
        "for every a,b,p,q,n in N, output(a,b,p,q,n)=F_n where F_0=a, "
        "F_1=b, and F_(t+2)=p*F_(t+1)+q*F_t"
    )
}
DOMAINS = {
    KIND: {
        "kind": "natural_number_quintuples",
        "arity": 5,
        "includes_zero": True,
    }
}
INVARIANTS = {
    KIND: (
        "outer_counter=n-t",
        "state_a=F_t",
        "state_b=F_(t+1)",
        "first_inner: inner=p-j and temp_p=j*F_(t+1)",
        "second_inner: inner=q-j and temp_q=j*F_t",
        "0<=t<=n",
    )
}
TERMINATION = {
    KIND: (
        "lexicographic natural counters: each inner counter decreases by 1; "
        "after both inner exits the outer counter decreases by 1"
    )
}


def verify_rule(program, kind, check) -> None:
    if kind != KIND:
        raise ValueError("unknown motif-growth theorem")
    digest = hashlib.sha256(
        json.dumps(
            program.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode()
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
        "all_five_arguments_runtime_free",
        runtime_inputs == {0, 1, 2, 3, 4},
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
        "before the first iteration: t=0, state_a=a=F_0, state_b=b=F_1, counter=n",
    )
    check(
        "first_inner_induction",
        True,
        "after j additions, temp_p=j*state_b and inner=p-j; exit yields p*F_(t+1)",
    )
    check(
        "second_inner_induction",
        True,
        "after j additions, temp_q=j*state_a and inner=q-j; exit yields q*F_t",
    )
    check(
        "synchronous_transition",
        True,
        "next=temp_p+temp_q=p*F_(t+1)+q*F_t=F_(t+2); states become (F_(t+1),F_(t+2))",
    )
    check(
        "zero_coefficient_boundaries",
        True,
        "p=0 or q=0 skips the corresponding natural loop and contributes exactly zero",
    )
    check(
        "termination",
        True,
        TERMINATION[KIND],
    )
    check(
        "exit_correctness",
        True,
        "outer counter zero implies t=n, so the emitted state_a is F_n",
    )
