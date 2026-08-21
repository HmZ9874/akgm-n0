"""Deeper proof portfolio and structural library learning for meta-autonomy.

This module remains symbolic and non-neural.  It adds a scaling-conservation
proof domain for constant-coefficient recurrences and mines reusable transition
macros from independently synthesized programs.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .meta_autonomy_v3 import (
    AnonymousWorld,
    AffineExpression,
    EvolvedProgram,
    InvariantCertificate,
    PolynomialInvariantKernel,
    PolynomialInvariantMiner,
    SynthesisCandidate,
    compile_fold_program,
)


@dataclass(frozen=True, slots=True)
class ScalingInvariantCertificate:
    certificate_id: str
    program_id: str
    register_index: int
    counter_input: int
    scale: int
    initial_expression: AffineExpression

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "program_id": self.program_id,
            "register_index": self.register_index,
            "counter_input": self.counter_input,
            "scale": self.scale,
            "initial_expression": self.initial_expression.to_dict(),
            "conserved_shape": "register * scale^remaining_counter",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScalingInvariantCertificate":
        return cls(
            str(value["certificate_id"]), str(value["program_id"]),
            int(value["register_index"]), int(value["counter_input"]),
            int(value["scale"]),
            AffineExpression.from_dict(value["initial_expression"]),
        )


class ScalingInvariantKernel:
    """Fixed exact checker for a discovered multiplicative conservation law."""

    def verify(
        self, program: EvolvedProgram, certificate: ScalingInvariantCertificate
    ) -> dict[str, Any]:
        register = certificate.register_index
        state_width = program.state_width
        row = (
            program.update_matrix[register]
            if program.kind == "counter_fold" and 0 <= register < state_width
            else ()
        )
        expected_row = tuple(
            certificate.scale if index == register else 0
            for index in range(state_width + program.input_width)
        )
        initial_matches = (
            0 <= register < len(program.initial_registers)
            and program.initial_registers[register] == certificate.initial_expression
        )
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "counter_fold", "passed": program.kind == "counter_fold"},
            {"id": "counter_binding", "passed": certificate.counter_input == program.counter_input},
            {"id": "nontrivial_scale", "passed": abs(certificate.scale) > 1},
            {"id": "pure_scaled_update", "passed": row == expected_row and not any(any(item) for item in program.state_input_coefficients)},
            {"id": "zero_update_bias", "passed": bool(row) and program.update_bias[register] == 0},
            {"id": "initial_expression_binding", "passed": initial_matches},
            {
                "id": "symbolic_conservation_step",
                "passed": bool(row) and row == expected_row,
                "identity": "(scale*r)*scale^(c-1) = r*scale^c",
            },
            {
                "id": "natural_counter_termination",
                "passed": program.counter_input >= 0,
                "ranking": "c' = c - 1 while c > 0",
            },
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class ScalingInvariantMiner:
    """Discover scaling laws directly from transition matrices."""

    def __init__(self) -> None:
        self.kernel = ScalingInvariantKernel()

    def mine(self, program: EvolvedProgram) -> tuple[ScalingInvariantCertificate, ...]:
        if program.kind != "counter_fold":
            return ()
        certificates = []
        width = program.state_width + program.input_width
        for register, row in enumerate(program.update_matrix):
            scale = row[register]
            expected = tuple(scale if index == register else 0 for index in range(width))
            if abs(scale) <= 1 or row != expected or program.update_bias[register] != 0:
                continue
            payload = {
                "program": program.program_id, "register": register,
                "counter": program.counter_input, "scale": scale,
                "initial": program.initial_registers[register].to_dict(),
            }
            certificate = ScalingInvariantCertificate(
                "SINV-" + hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()[:16],
                program.program_id, register, program.counter_input, scale,
                program.initial_registers[register],
            )
            if self.kernel.verify(program, certificate)["passed"]:
                certificates.append(certificate)
        return tuple(certificates)


@dataclass(frozen=True, slots=True)
class AffineScalingInvariantCertificate:
    certificate_id: str
    program_id: str
    state_weights: tuple[int, ...]
    input_weights: tuple[int, ...]
    bias: int
    scale: int
    counter_input: int
    initial_expression: AffineExpression

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "program_id": self.program_id,
            "state_weights": list(self.state_weights),
            "input_weights": list(self.input_weights),
            "bias": self.bias,
            "scale": self.scale,
            "counter_input": self.counter_input,
            "initial_expression": self.initial_expression.to_dict(),
            "conserved_shape": "affine_state_form * scale^remaining_counter",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AffineScalingInvariantCertificate":
        return cls(
            str(value["certificate_id"]), str(value["program_id"]),
            tuple(map(int, value["state_weights"])),
            tuple(map(int, value["input_weights"])), int(value["bias"]),
            int(value["scale"]), int(value["counter_input"]),
            AffineExpression.from_dict(value["initial_expression"]),
        )


class AffineScalingInvariantKernel:
    """Verify q(next)=scale*q(now) coefficient by coefficient."""

    def verify(
        self, program: EvolvedProgram,
        certificate: AffineScalingInvariantCertificate,
    ) -> dict[str, Any]:
        state_width = program.state_width
        input_width = program.input_width
        weights = certificate.state_weights
        input_weights = certificate.input_weights
        dimensions_match = (
            program.kind == "counter_fold"
            and len(weights) == state_width
            and len(input_weights) == input_width
            and not any(any(item) for item in program.state_input_coefficients)
        )
        if dimensions_match:
            next_state = tuple(
                sum(weights[row_index] * program.update_matrix[row_index][column]
                    for row_index in range(state_width))
                for column in range(state_width)
            )
            next_input = tuple(
                input_weights[column]
                + sum(weights[row_index] * program.update_matrix[row_index][state_width + column]
                      for row_index in range(state_width))
                for column in range(input_width)
            )
            next_bias = certificate.bias + sum(
                weights[index] * program.update_bias[index]
                for index in range(state_width)
            )
            expected_state = tuple(certificate.scale * value for value in weights)
            expected_input = tuple(certificate.scale * value for value in input_weights)
            expected_bias = certificate.scale * certificate.bias
            initial_coefficients = tuple(
                input_weights[column]
                + sum(weights[index] * program.initial_registers[index].coefficients[column]
                      for index in range(state_width))
                for column in range(input_width)
            )
            initial_bias = certificate.bias + sum(
                weights[index] * program.initial_registers[index].bias
                for index in range(state_width)
            )
        else:
            next_state = next_input = expected_state = expected_input = ()
            next_bias = initial_bias = expected_bias = 0
            initial_coefficients = ()
        initial_matches = certificate.initial_expression == AffineExpression(
            initial_coefficients, initial_bias
        )
        initially_zero = (
            not any(certificate.initial_expression.coefficients)
            and certificate.initial_expression.bias == 0
        )
        admissible_relation = abs(certificate.scale) > 1 or initially_zero
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "dimension_binding", "passed": dimensions_match},
            {"id": "nonzero_state_form", "passed": any(weights)},
            {
                "id": "admissible_eigen_relation",
                "passed": admissible_relation,
                "mode": "scaling_conservation" if abs(certificate.scale) > 1 else "inductive_zero_set",
            },
            {"id": "state_coefficient_identity", "passed": next_state == expected_state},
            {"id": "input_coefficient_identity", "passed": next_input == expected_input},
            {"id": "constant_identity", "passed": next_bias == expected_bias},
            {"id": "initial_form_binding", "passed": initial_matches},
            {"id": "counter_binding", "passed": certificate.counter_input == program.counter_input},
            {
                "id": "symbolic_conservation_step",
                "passed": dimensions_match and next_state == expected_state
                and next_input == expected_input and next_bias == expected_bias,
                "identity": (
                    "q'=scale*q => q'*scale^(c-1)=q*scale^c"
                    if abs(certificate.scale) > 1
                    else "q=0 and q'=scale*q => q'=0"
                ),
            },
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class AffineScalingInvariantMiner:
    """Enumerate small integer affine forms and retain exact eigen-identities."""

    def __init__(self, *, weight_radius: int = 2, scale_radius: int = 3) -> None:
        self.weight_radius = weight_radius
        self.scale_radius = scale_radius
        self.kernel = AffineScalingInvariantKernel()

    def mine(self, program: EvolvedProgram) -> tuple[AffineScalingInvariantCertificate, ...]:
        if program.kind != "counter_fold":
            return ()
        import itertools

        state_width = program.state_width
        input_width = program.input_width
        values = range(-self.weight_radius, self.weight_radius + 1)
        certificates = []
        seen_normal_forms: set[tuple[int, ...]] = set()
        for state_weights in itertools.product(values, repeat=state_width):
            if not any(state_weights):
                continue
            for input_weights in itertools.product(values, repeat=input_width):
                for bias in values:
                    primitive_values = tuple(state_weights) + tuple(input_weights) + (bias,)
                    common = math.gcd(*(abs(value) for value in primitive_values if value))
                    if common > 1:
                        continue
                    first = next(value for value in primitive_values if value)
                    if first < 0:
                        continue
                    for scale in range(-self.scale_radius, self.scale_radius + 1):
                        initial_coefficients = tuple(
                            input_weights[column]
                            + sum(state_weights[index] * program.initial_registers[index].coefficients[column]
                                  for index in range(state_width))
                            for column in range(input_width)
                        )
                        initial_bias = bias + sum(
                            state_weights[index] * program.initial_registers[index].bias
                            for index in range(state_width)
                        )
                        payload = {
                            "program": program.program_id, "state_weights": state_weights,
                            "input_weights": input_weights, "bias": bias, "scale": scale,
                            "counter": program.counter_input,
                        }
                        certificate = AffineScalingInvariantCertificate(
                            "AINV-" + hashlib.sha256(
                                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                            ).hexdigest()[:16],
                            program.program_id, tuple(state_weights), tuple(input_weights),
                            bias, scale, program.counter_input,
                            AffineExpression(initial_coefficients, initial_bias),
                        )
                        if not self.kernel.verify(program, certificate)["passed"]:
                            continue
                        normal = tuple(state_weights) + tuple(input_weights) + (bias, scale)
                        if normal in seen_normal_forms:
                            continue
                        seen_normal_forms.add(normal)
                        certificates.append(certificate)
        return tuple(certificates)


@dataclass(frozen=True, slots=True)
class CounterProductCertificate:
    certificate_id: str
    program_id: str
    register_index: int
    counter_input: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "program_id": self.program_id,
            "register_index": self.register_index,
            "counter_input": self.counter_input,
            "induction_shape": "r(0)=1; r(next)=r*remaining_counter",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CounterProductCertificate":
        return cls(
            str(value["certificate_id"]), str(value["program_id"]),
            int(value["register_index"]), int(value["counter_input"]),
        )


class CounterProductKernel:
    """Exact induction checker for a discovered state/counter product fold."""

    def verify(
        self, program: EvolvedProgram, certificate: CounterProductCertificate
    ) -> dict[str, Any]:
        register = certificate.register_index
        one_state = program.state_width == 1 and register == 0
        initial_one = (
            one_state
            and program.initial_registers[0] == AffineExpression((0,) * program.input_width, 1)
        )
        pure_interaction = (
            one_state
            and program.update_matrix == ((0,) * (1 + program.input_width),)
            and program.update_bias == (0,)
            and (not program.counter_coefficients or program.counter_coefficients == (0,))
            and program.counter_state_matrix == ((1,),)
            and not any(any(item) for item in program.state_input_coefficients)
        )
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "counter_fold", "passed": program.kind == "counter_fold"},
            {"id": "single_state_binding", "passed": one_state},
            {"id": "unit_initialization", "passed": initial_one},
            {"id": "pure_state_counter_interaction", "passed": pure_interaction},
            {"id": "counter_binding", "passed": certificate.counter_input == program.counter_input},
            {
                "id": "induction_base",
                "passed": initial_one,
                "identity": "empty accumulated product = 1",
            },
            {
                "id": "induction_step",
                "passed": pure_interaction,
                "identity": "r'=r*c and c'=c-1 extends the accumulated factor range by c",
            },
            {
                "id": "natural_counter_termination",
                "passed": program.counter_input >= 0,
                "ranking": "c' = c - 1 while c > 0",
            },
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class CounterProductMiner:
    def __init__(self) -> None:
        self.kernel = CounterProductKernel()

    def mine(self, program: EvolvedProgram) -> tuple[CounterProductCertificate, ...]:
        payload = {"program": program.program_id, "register": 0, "counter": program.counter_input}
        certificate = CounterProductCertificate(
            "CPINV-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16],
            program.program_id, 0, program.counter_input,
        )
        return (certificate,) if self.kernel.verify(program, certificate)["passed"] else ()


@dataclass(frozen=True, slots=True)
class ScaledCounterProductCertificate:
    certificate_id: str
    program_id: str
    counter_input: int
    initial_expression: AffineExpression

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "program_id": self.program_id,
            "counter_input": self.counter_input,
            "initial_expression": self.initial_expression.to_dict(),
            "induction_shape": "r(0)=affine(inputs); r(next)=r*remaining_counter",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScaledCounterProductCertificate":
        return cls(
            str(value["certificate_id"]), str(value["program_id"]),
            int(value["counter_input"]),
            AffineExpression.from_dict(value["initial_expression"]),
        )


class ScaledCounterProductKernel:
    def verify(
        self, program: EvolvedProgram,
        certificate: ScaledCounterProductCertificate,
    ) -> dict[str, Any]:
        pure = (
            program.kind == "counter_fold" and program.state_width == 1
            and program.update_matrix == ((0,) * (1 + program.input_width),)
            and program.update_bias == (0,)
            and (not program.counter_coefficients or program.counter_coefficients == (0,))
            and program.counter_state_matrix == ((1,),)
            and not any(any(item) for item in program.state_input_coefficients)
        )
        initial = program.initial_registers[0] if program.state_width == 1 else None
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "pure_state_counter_interaction", "passed": pure},
            {"id": "initial_expression_binding", "passed": initial == certificate.initial_expression},
            {"id": "counter_binding", "passed": certificate.counter_input == program.counter_input},
            {
                "id": "scaled_product_induction",
                "passed": pure and initial == certificate.initial_expression,
                "identity": "r_k = initial*product(n-k+1..n)",
            },
            {"id": "natural_counter_termination", "passed": program.counter_input >= 0},
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class ScaledCounterProductMiner:
    def __init__(self) -> None:
        self.kernel = ScaledCounterProductKernel()

    def mine(self, program: EvolvedProgram) -> tuple[ScaledCounterProductCertificate, ...]:
        if program.state_width != 1:
            return ()
        payload = {
            "program": program.program_id, "counter": program.counter_input,
            "initial": program.initial_registers[0].to_dict(),
        }
        certificate = ScaledCounterProductCertificate(
            "SCPINV-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16],
            program.program_id, program.counter_input, program.initial_registers[0],
        )
        return (certificate,) if self.kernel.verify(program, certificate)["passed"] else ()


@dataclass(frozen=True, slots=True)
class CFiniteRecurrenceCertificate:
    certificate_id: str
    program_id: str
    output_register: int
    trace: int
    determinant: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "program_id": self.program_id,
            "output_register": self.output_register,
            "trace": self.trace,
            "determinant": self.determinant,
            "recurrence": "x[t+2] = trace*x[t+1] - determinant*x[t]",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CFiniteRecurrenceCertificate":
        return cls(
            str(value["certificate_id"]), str(value["program_id"]),
            int(value["output_register"]), int(value["trace"]),
            int(value["determinant"]),
        )


class CFiniteRecurrenceKernel:
    """Use the exact 2x2 characteristic identity as a recurrence proof."""

    def verify(
        self, program: EvolvedProgram, certificate: CFiniteRecurrenceCertificate
    ) -> dict[str, Any]:
        matrix_shape = (
            program.kind == "counter_fold"
            and program.state_width == 2
            and len(program.update_matrix) == 2
            and all(len(row) == 2 + program.input_width for row in program.update_matrix)
        )
        if matrix_shape:
            a, b = program.update_matrix[0][:2]
            c, d = program.update_matrix[1][:2]
            trace = a + d
            determinant = a * d - b * c
            homogeneous = (
                all(not any(row[2:]) for row in program.update_matrix)
                and not any(program.update_bias)
                and not any(program.counter_coefficients)
            and not any(any(row) for row in program.counter_state_matrix)
            and not any(any(row) for row in program.state_input_coefficients)
            )
        else:
            trace = determinant = 0
            homogeneous = False
        output_valid = certificate.output_register in program.output_registers
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "two_state_matrix", "passed": matrix_shape},
            {"id": "homogeneous_transition", "passed": homogeneous},
            {"id": "trace_binding", "passed": certificate.trace == trace},
            {"id": "determinant_binding", "passed": certificate.determinant == determinant},
            {"id": "output_binding", "passed": output_valid},
            {
                "id": "cayley_hamilton_identity",
                "passed": matrix_shape,
                "identity": "A^2 - trace(A)A + determinant(A)I = 0",
            },
            {
                "id": "component_recurrence",
                "passed": matrix_shape and homogeneous and output_valid,
                "identity": "each selected state component obeys the characteristic recurrence",
            },
            {"id": "natural_counter_termination", "passed": program.counter_input >= 0},
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class CFiniteRecurrenceMiner:
    def __init__(self) -> None:
        self.kernel = CFiniteRecurrenceKernel()

    def mine(self, program: EvolvedProgram) -> tuple[CFiniteRecurrenceCertificate, ...]:
        if program.state_width != 2 or not program.output_registers:
            return ()
        a, b = program.update_matrix[0][:2]
        c, d = program.update_matrix[1][:2]
        trace = a + d
        determinant = a * d - b * c
        payload = {
            "program": program.program_id, "output": program.output_registers[0],
            "trace": trace, "determinant": determinant,
        }
        certificate = CFiniteRecurrenceCertificate(
            "CFINV-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16],
            program.program_id, program.output_registers[0], trace, determinant,
        )
        return (certificate,) if self.kernel.verify(program, certificate)["passed"] else ()


def _determinant(matrix: Sequence[Sequence[int]]) -> int:
    if len(matrix) == 1:
        return int(matrix[0][0])
    return sum(
        (-1 if column % 2 else 1) * matrix[0][column]
        * _determinant(tuple(
            tuple(row[index] for index in range(len(matrix)) if index != column)
            for row in matrix[1:]
        ))
        for column in range(len(matrix))
    )


def _characteristic_coefficients(matrix: Sequence[Sequence[int]]) -> tuple[int, ...]:
    """Coefficients after the leading one for matrices up to dimension three."""

    width = len(matrix)
    if width == 1:
        return (-int(matrix[0][0]),)
    trace = sum(matrix[index][index] for index in range(width))
    if width == 2:
        return (-trace, _determinant(matrix))
    if width == 3:
        principal_pairs = (
            matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
            + matrix[0][0] * matrix[2][2] - matrix[0][2] * matrix[2][0]
            + matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1]
        )
        return (-trace, principal_pairs, -_determinant(matrix))
    raise ValueError("characteristic kernel supports dimensions one through three")


@dataclass(frozen=True, slots=True)
class AffineCFiniteCertificate:
    certificate_id: str
    program_id: str
    output_register: int
    augmented_dimension: int
    characteristic_coefficients: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "program_id": self.program_id,
            "output_register": self.output_register,
            "augmented_dimension": self.augmented_dimension,
            "characteristic_coefficients": list(self.characteristic_coefficients),
            "recurrence": "Cayley-Hamilton recurrence of the constant-augmented transition",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AffineCFiniteCertificate":
        return cls(
            str(value["certificate_id"]), str(value["program_id"]),
            int(value["output_register"]), int(value["augmented_dimension"]),
            tuple(map(int, value["characteristic_coefficients"])),
        )


def _augmented_transition(program: EvolvedProgram) -> tuple[tuple[int, ...], ...] | None:
    if (
        program.kind != "counter_fold"
        or not 1 <= program.state_width <= 2
        or any(any(row[program.state_width:]) for row in program.update_matrix)
        or any(program.counter_coefficients)
        or any(any(row) for row in program.counter_state_matrix)
        or any(any(row) for row in program.state_input_coefficients)
    ):
        return None
    width = program.state_width
    rows = [
        tuple(program.update_matrix[index][:width]) + (program.update_bias[index],)
        for index in range(width)
    ]
    rows.append((0,) * width + (1,))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class InputScaleCertificate:
    certificate_id: str
    program_id: str
    counter_input: int
    scale_input: int
    interaction_coefficient: int
    initial_expression: AffineExpression

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "program_id": self.program_id,
            "counter_input": self.counter_input,
            "scale_input": self.scale_input,
            "interaction_coefficient": self.interaction_coefficient,
            "initial_expression": self.initial_expression.to_dict(),
            "induction_shape": "r_n=initial*(coefficient*input)^n",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InputScaleCertificate":
        return cls(
            str(value["certificate_id"]), str(value["program_id"]),
            int(value["counter_input"]), int(value["scale_input"]),
            int(value["interaction_coefficient"]),
            AffineExpression.from_dict(value["initial_expression"]),
        )


class InputScaleKernel:
    def verify(self, program: EvolvedProgram, certificate: InputScaleCertificate) -> dict[str, Any]:
        interaction = (
            program.state_input_coefficients[0]
            if program.state_width == 1 and program.state_input_coefficients else ()
        )
        active = [index for index, value in enumerate(interaction) if value]
        pure = (
            program.kind == "counter_fold" and program.state_width == 1
            and program.update_matrix == ((0,) * (1 + program.input_width),)
            and program.update_bias == (0,)
            and not any(program.counter_coefficients)
            and not any(any(row) for row in program.counter_state_matrix)
            and len(active) == 1
        )
        scale_input = active[0] if len(active) == 1 else -1
        coefficient = interaction[scale_input] if scale_input >= 0 else 0
        initial = program.initial_registers[0] if program.state_width == 1 else None
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "pure_state_input_interaction", "passed": pure},
            {"id": "counter_binding", "passed": certificate.counter_input == program.counter_input},
            {"id": "scale_input_binding", "passed": certificate.scale_input == scale_input},
            {"id": "coefficient_binding", "passed": certificate.interaction_coefficient == coefficient},
            {"id": "initial_binding", "passed": certificate.initial_expression == initial},
            {
                "id": "power_induction",
                "passed": pure and certificate.initial_expression == initial,
                "identity": "r'=r*(coefficient*input) extends the exponent by one",
            },
            {"id": "natural_counter_termination", "passed": program.counter_input >= 0},
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class InputScaleMiner:
    def __init__(self) -> None:
        self.kernel = InputScaleKernel()

    def mine(self, program: EvolvedProgram) -> tuple[InputScaleCertificate, ...]:
        if program.state_width != 1 or not program.state_input_coefficients:
            return ()
        active = [index for index, value in enumerate(program.state_input_coefficients[0]) if value]
        if len(active) != 1:
            return ()
        scale_input = active[0]
        payload = {
            "program": program.program_id, "counter": program.counter_input,
            "scale_input": scale_input,
            "coefficient": program.state_input_coefficients[0][scale_input],
            "initial": program.initial_registers[0].to_dict(),
        }
        certificate = InputScaleCertificate(
            "ISINV-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16],
            program.program_id, program.counter_input, scale_input,
            program.state_input_coefficients[0][scale_input],
            program.initial_registers[0],
        )
        return (certificate,) if self.kernel.verify(program, certificate)["passed"] else ()


class AffineCFiniteKernel:
    def verify(self, program: EvolvedProgram, certificate: AffineCFiniteCertificate) -> dict[str, Any]:
        matrix = _augmented_transition(program)
        coefficients = _characteristic_coefficients(matrix) if matrix else ()
        output_valid = certificate.output_register in program.output_registers
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "constant_augmentation_admissible", "passed": matrix is not None},
            {"id": "dimension_binding", "passed": bool(matrix) and certificate.augmented_dimension == len(matrix)},
            {"id": "characteristic_coefficients", "passed": certificate.characteristic_coefficients == coefficients},
            {"id": "output_binding", "passed": output_valid},
            {
                "id": "cayley_hamilton_identity",
                "passed": bool(matrix) and len(coefficients) == len(matrix),
                "identity": "the augmented transition annihilates its characteristic polynomial",
            },
            {
                "id": "selected_component_recurrence",
                "passed": bool(matrix) and output_valid,
                "order": len(matrix) if matrix else 0,
            },
            {"id": "natural_counter_termination", "passed": program.counter_input >= 0},
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class AffineCFiniteMiner:
    def __init__(self) -> None:
        self.kernel = AffineCFiniteKernel()

    def mine(self, program: EvolvedProgram) -> tuple[AffineCFiniteCertificate, ...]:
        matrix = _augmented_transition(program)
        if matrix is None or not program.output_registers:
            return ()
        coefficients = _characteristic_coefficients(matrix)
        payload = {
            "program": program.program_id, "output": program.output_registers[0],
            "dimension": len(matrix), "coefficients": coefficients,
        }
        certificate = AffineCFiniteCertificate(
            "ACFINV-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16],
            program.program_id, program.output_registers[0], len(matrix), coefficients,
        )
        return (certificate,) if self.kernel.verify(program, certificate)["passed"] else ()


@dataclass(frozen=True, slots=True)
class PortfolioProof:
    proof_domain: str
    program_id: str
    certificate: InvariantCertificate | ScalingInvariantCertificate
    verification: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_domain": self.proof_domain,
            "program_id": self.program_id,
            "certificate": self.certificate.to_dict(),
            "verification": dict(self.verification),
        }


class AutonomousProofPortfolio:
    """Try proof domains by measured applicability, without a theorem label."""

    def __init__(self, *, polynomial_degree: int = 2) -> None:
        self.polynomial = PolynomialInvariantMiner(maximum_degree=polynomial_degree)
        self.scaling = ScalingInvariantMiner()
        self.affine_scaling = AffineScalingInvariantMiner()
        self.counter_product = CounterProductMiner()
        self.scaled_counter_product = ScaledCounterProductMiner()
        self.cfinite = CFiniteRecurrenceMiner()
        self.affine_cfinite = AffineCFiniteMiner()
        self.input_scale = InputScaleMiner()

    def prove(self, program: EvolvedProgram) -> tuple[PortfolioProof, ...]:
        results: list[PortfolioProof] = []
        for certificate in self.polynomial.mine(program):
            verification = self.polynomial.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("polynomial_equality", program.program_id, certificate, verification))
        for certificate in self.scaling.mine(program):
            verification = self.scaling.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("scaling_conservation", program.program_id, certificate, verification))
        for certificate in self.affine_scaling.mine(program):
            verification = self.affine_scaling.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("affine_scaling_conservation", program.program_id, certificate, verification))
        for certificate in self.counter_product.mine(program):
            verification = self.counter_product.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("counter_product_induction", program.program_id, certificate, verification))
        for certificate in self.scaled_counter_product.mine(program):
            verification = self.scaled_counter_product.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("scaled_counter_product_induction", program.program_id, certificate, verification))
        for certificate in self.cfinite.mine(program):
            verification = self.cfinite.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("cfinite_characteristic_recurrence", program.program_id, certificate, verification))
        for certificate in self.affine_cfinite.mine(program):
            verification = self.affine_cfinite.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("affine_cfinite_recurrence", program.program_id, certificate, verification))
        for certificate in self.input_scale.mine(program):
            verification = self.input_scale.kernel.verify(program, certificate)
            if verification["passed"]:
                results.append(PortfolioProof("input_scaled_power_induction", program.program_id, certificate, verification))
        return tuple(results)


@dataclass(frozen=True, slots=True)
class LearnedTransitionMacro:
    macro_id: str
    state_width: int
    input_width: int
    normalized_row: tuple[int, ...]
    support: int
    primitive_token_cost: int
    macro_token_cost: int = 1

    @property
    def token_savings_per_use(self) -> int:
        return max(0, self.primitive_token_cost - self.macro_token_cost)

    def to_dict(self) -> dict[str, Any]:
        return {
            "macro_id": self.macro_id,
            "state_width": self.state_width,
            "input_width": self.input_width,
            "normalized_row": list(self.normalized_row),
            "support": self.support,
            "primitive_token_cost": self.primitive_token_cost,
            "macro_token_cost": self.macro_token_cost,
            "token_savings_per_use": self.token_savings_per_use,
        }


class TransitionLibraryMiner:
    """Compress recurring executable transition rows into anonymous macros."""

    def mine(
        self, programs: Sequence[EvolvedProgram], *, minimum_support: int = 2
    ) -> tuple[LearnedTransitionMacro, ...]:
        rows = Counter(
            (program.state_width, program.input_width, tuple(row) + (bias,))
            for program in programs if program.kind == "counter_fold"
            for row, bias in zip(program.update_matrix, program.update_bias, strict=True)
        )
        macros = []
        for (state_width, input_width, row), support in sorted(rows.items()):
            if support < minimum_support:
                continue
            primitive_cost = 1 + sum(value != 0 for value in row)
            payload = {
                "state_width": state_width, "input_width": input_width,
                "row": row, "support": support,
            }
            macros.append(LearnedTransitionMacro(
                "TMAC-" + hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()[:16],
                state_width, input_width, row, support, primitive_cost,
            ))
        return tuple(macros)


@dataclass(frozen=True, slots=True)
class MacroTransferReport:
    world_id: str
    macros_available: int
    candidates_executed: int
    selected: SynthesisCandidate

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "macros_available": self.macros_available,
            "candidates_executed": self.candidates_executed,
            "selected_program": self.selected.program.to_dict(),
            "passed_rows": self.selected.passed_rows,
            "row_count": self.selected.row_count,
            "exact": self.selected.exact,
        }


class MacroGuidedSynthesizer:
    """Recombine learned transition rows before reopening primitive search."""

    def search(
        self, world: AnonymousWorld,
        macros: Sequence[LearnedTransitionMacro],
    ) -> MacroTransferReport:
        import itertools

        compatible = tuple(
            macro for macro in macros
            if macro.input_width == world.input_width and 1 <= macro.state_width <= 2
        )
        best: SynthesisCandidate | None = None
        executed = 0
        for state_width in sorted({macro.state_width for macro in compatible}):
            choices = tuple(macro for macro in compatible if macro.state_width == state_width)
            if not choices:
                continue
            initial_options = (
                AffineExpression((0,) * world.input_width, 0),
                AffineExpression((0,) * world.input_width, 1),
            ) + tuple(
                AffineExpression(
                    tuple(int(index == source) for index in range(world.input_width)), 0
                )
                for source in range(world.input_width)
            )
            for counter_input in range(world.input_width):
                for initial in itertools.product(initial_options, repeat=state_width):
                    for selected_rows in itertools.product(choices, repeat=state_width):
                        program = compile_fold_program(
                            input_width=world.input_width,
                            counter_input=counter_input,
                            initial_registers=initial,
                            update_matrix=tuple(item.normalized_row[:-1] for item in selected_rows),
                            update_bias=tuple(item.normalized_row[-1] for item in selected_rows),
                            output_registers=(0,),
                        )
                        passed = sum(
                            program.execute(row) == expected
                            for row, expected in zip(world.input_rows, world.output_rows, strict=True)
                        )
                        executed += 1
                        candidate = SynthesisCandidate(program, passed, len(world.input_rows))
                        if best is None or (-passed, program.complexity, program.program_id) < (
                            -best.passed_rows, best.program.complexity, best.program.program_id
                        ):
                            best = candidate
                        if candidate.exact:
                            return MacroTransferReport(world.world_id, len(compatible), executed, candidate)
        if best is None:
            raise ValueError("no compatible learned transition macros")
        return MacroTransferReport(world.world_id, len(compatible), executed, best)


def replay_portfolio_proof(program: EvolvedProgram, proof: Mapping[str, Any]) -> dict[str, Any]:
    domain = proof.get("proof_domain")
    if proof.get("program_id") != program.program_id:
        return {"passed": False, "obligations": [{"id": "program_binding", "passed": False}]}
    if domain == "polynomial_equality":
        value = proof["certificate"]
        certificate = InvariantCertificate(
            str(value["certificate_id"]), str(value["program_id"]),
            int(value["variable_count"]), int(value["degree"]),
            tuple(map(int, value["coefficients"])),
            tuple(tuple(map(int, monomial)) for monomial in value["monomials"]),
            int(value["ranking_variable"]),
        )
        return PolynomialInvariantKernel().verify(program, certificate)
    if domain == "scaling_conservation":
        return ScalingInvariantKernel().verify(
            program, ScalingInvariantCertificate.from_dict(proof["certificate"])
        )
    if domain == "affine_scaling_conservation":
        return AffineScalingInvariantKernel().verify(
            program, AffineScalingInvariantCertificate.from_dict(proof["certificate"])
        )
    if domain == "counter_product_induction":
        return CounterProductKernel().verify(
            program, CounterProductCertificate.from_dict(proof["certificate"])
        )
    if domain == "scaled_counter_product_induction":
        return ScaledCounterProductKernel().verify(
            program, ScaledCounterProductCertificate.from_dict(proof["certificate"])
        )
    if domain == "cfinite_characteristic_recurrence":
        return CFiniteRecurrenceKernel().verify(
            program, CFiniteRecurrenceCertificate.from_dict(proof["certificate"])
        )
    if domain == "affine_cfinite_recurrence":
        return AffineCFiniteKernel().verify(
            program, AffineCFiniteCertificate.from_dict(proof["certificate"])
        )
    if domain == "input_scaled_power_induction":
        return InputScaleKernel().verify(
            program, InputScaleCertificate.from_dict(proof["certificate"])
        )
    return {"passed": False, "obligations": [{"id": "known_proof_domain", "passed": False}]}
