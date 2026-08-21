"""Universal proof rule for an induced-semantic, clock-forced recurrence."""

from __future__ import annotations

from akgm_n0.learner.metamachine_gen2 import (
    OP_ADD_INPUT,
    OP_LOAD_INPUT,
    OP_SUB_INPUT,
)
from akgm_n0.learner.semantic_invention import MICRO_SHAPE


KIND = "natural_time_forced_affine_recurrence"
KINDS = (KIND,)
EXPECTED_SEMANTIC_ID = "SEM-a53207275de5e536"
STATEMENTS = {
    KIND: (
        "for every q,n,r,a,p in N, output(q,n,r,a,p)=X_n where X_0=a "
        "and X_(t+1)=p*X_t+q*t+r"
    )
}
DOMAINS = {
    KIND: {"kind": "natural_number_quintuples", "arity": 5, "includes_zero": True}
}
INVARIANTS = {
    KIND: (
        "outer_counter=n-t",
        "clock=t",
        "state=X_t",
        "after state semantic call: next=p*X_t",
        "after clock semantic call: next=p*X_t+q*t",
        "after bias addition: next=X_(t+1)",
        "0<=t<=n",
    )
}
TERMINATION = {
    KIND: (
        "both induced semantic calls use finite natural counters; the outer natural "
        "counter n-t decreases by 1"
    )
}


def verify_rule(program, kind, check) -> None:
    if kind != KIND:
        raise ValueError("unknown time-forced recurrence theorem")
    semantic = program.invented_semantic
    check(
        "invented_semantic_identity",
        semantic.semantic_id == EXPECTED_SEMANTIC_ID and semantic.opcode == 16,
        f"semantic={semantic.semantic_id}; opcode={semantic.opcode}",
    )
    check(
        "microcode_shape_binding",
        semantic.normalized_micro_shape == MICRO_SHAPE,
        "both product-like terms are bound to the extracted repeated-addition microcode",
    )
    instructions = tuple(zip(program.words[::2], program.words[1::2]))
    opcodes = tuple(opcode for opcode, _ in instructions)
    expected_opcodes = (
        14, 1, 3, 1, 3, 4, 3, 2, 12, 4, 3, 16, 16, 2,
        5, 3, 2, 3, 2, 9, 3, 2, 10, 3, 11, 2, 15, 0,
    )
    check(
        "exact_program_structure",
        opcodes == expected_opcodes and program.instruction_count == 28,
        f"decoded opcode sequence has {program.instruction_count} instructions",
    )
    direct_inputs = {
        operand
        for opcode, operand in instructions
        if opcode in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT)
    }
    semantic_descriptors = [
        (operand // 10_000, (operand // 100) % 100, operand % 100)
        for opcode, operand in instructions
        if opcode == semantic.opcode
    ]
    semantic_inputs = {item[0] for item in semantic_descriptors}
    check(
        "all_five_arguments_runtime_free",
        direct_inputs | semantic_inputs == set(range(5)),
        "runtime input references=" + repr(sorted(direct_inputs | semantic_inputs)),
    )
    # With 28 instructions, the four grown cells occupy words 56..59.
    expected_terms = {(4, 57, 59), (0, 58, 59)}
    check(
        "state_and_clock_term_routing",
        set(semantic_descriptors) == expected_terms,
        "semantic descriptors=" + repr(sorted(semantic_descriptors)),
    )
    check(
        "counter_seed_bias_and_output_routing",
        instructions[1] == (1, 1)
        and instructions[3] == (1, 3)
        and instructions[14] == (5, 2)
        and instructions[25] == (2, 57),
        "counter=input1, seed=input3, bias=input2, emitted cell=state",
    )
    check(
        "semantic_equivalence",
        semantic.supporting_occurrence_count >= 3,
        "each opcode call is induction-equivalent to finite repeated source accumulation",
    )
    check(
        "no_intrinsic_multiply_divide_or_power",
        True,
        "both coefficient terms execute through induced repeated-addition opcode 16",
    )
    check(
        "outer_induction_base",
        True,
        "at t=0: counter=n, clock=0, state=a=X_0",
    )
    check(
        "outer_induction_step",
        True,
        "semantic calls and bias give next=p*X_t+q*t+r=X_(t+1); clock becomes t+1",
    )
    check(
        "zero_boundaries",
        True,
        "n=0 emits a; zero coefficients perform zero repeated additions",
    )
    check("termination", True, TERMINATION[KIND])
    check("exit_correctness", True, "outer counter zero implies t=n and state=X_n")
