"""Exact, anonymous composition layer for secondary-school symbolic tasks.

The layer operates on normalized rational pairs and integers.  Program modes
are opaque to the search; mathematical interpretations live in the evaluator.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Sequence


class HighSchoolDomainError(ValueError):
    pass


def _encode(values: Fraction | Sequence[Fraction]) -> tuple[int, ...]:
    items = (values,) if isinstance(values, Fraction) else tuple(values)
    result: list[int] = []
    for value in items:
        exact = Fraction(value)
        result.extend((exact.numerator, exact.denominator))
    return tuple(result)


def _exact_sqrt(value: Fraction) -> Fraction:
    if value < 0:
        raise HighSchoolDomainError("negative exact root")
    numerator = math.isqrt(value.numerator)
    denominator = math.isqrt(value.denominator)
    if numerator * numerator != value.numerator or denominator * denominator != value.denominator:
        raise HighSchoolDomainError("root is not rational-exact")
    return Fraction(numerator, denominator)


def _choose(n: int, k: int) -> int:
    if n < 0 or k < 0 or k > n:
        raise HighSchoolDomainError("invalid finite choice")
    return math.comb(n, k)


def _recipe(mode: int, row: tuple[int, ...]) -> tuple[int, ...]:
    if mode == 0:  # four integers encode two rational operands
        a, b, c, d = row
        if b == 0 or c == 0 or d == 0:
            raise HighSchoolDomainError("undefined rational quotient")
        return _encode(Fraction(a, b) / Fraction(c, d))
    if mode == 1:
        a, b, c = row
        if a == 0:
            raise HighSchoolDomainError("non-unique linear equation")
        return _encode(Fraction(c - b, a))
    if mode == 2:
        a, b, c, d, e, f = row
        determinant = a * d - b * c
        if determinant == 0:
            raise HighSchoolDomainError("singular system")
        return _encode((Fraction(e * d - b * f, determinant), Fraction(a * f - e * c, determinant)))
    if mode == 3:
        a, b, c = row
        if a == 0:
            raise HighSchoolDomainError("not quadratic")
        root_delta = _exact_sqrt(Fraction(b * b - 4 * a * c, 1))
        roots = sorted((Fraction(-b, 2 * a) - root_delta / (2 * a), Fraction(-b, 2 * a) + root_delta / (2 * a)))
        return _encode(roots)
    if mode == 4:
        a, b, c = row
        delta = b * b - 4 * a * c
        return _encode(Fraction((delta > 0) - (delta < 0), 1))
    if mode == 5:
        first, step, index = row
        if index < 1:
            raise HighSchoolDomainError("sequence index starts at one")
        return _encode(Fraction(first + (index - 1) * step, 1))
    if mode == 6:
        first, step, count = row
        if count < 0:
            raise HighSchoolDomainError("negative sequence count")
        return _encode(Fraction(count * (2 * first + (count - 1) * step), 2))
    if mode == 7:
        first, ratio, index = row
        if index < 1:
            raise HighSchoolDomainError("sequence index starts at one")
        return _encode(Fraction(first * (ratio ** (index - 1)), 1))
    if mode == 8:
        first, ratio, count = row
        if count < 0:
            raise HighSchoolDomainError("negative sequence count")
        value = first * count if ratio == 1 else Fraction(first * (ratio ** count - 1), ratio - 1)
        return _encode(Fraction(value))
    if mode == 9:
        a, b, c, d, x = row
        return _encode(Fraction(((a * x + b) * x + c) * x + d, 1))
    if mode == 10:
        a, b, c, _d, x = row
        return _encode(Fraction(3 * a * x * x + 2 * b * x + c, 1))
    if mode == 11:
        a, b, c, d, x = row
        return _encode(Fraction(a * (c * x + d) + b, 1))
    if mode == 12:
        base, value = row
        if base <= 1 or value < 1:
            raise HighSchoolDomainError("outside exact logarithm domain")
        exponent, current = 0, 1
        while current < value:
            current *= base
            exponent += 1
        if current != value:
            raise HighSchoolDomainError("not an exact integer power")
        return _encode(Fraction(exponent, 1))
    if mode == 13:
        x1, y1, x2, y2 = row
        return _encode((Fraction(x1 + x2, 2), Fraction(y1 + y2, 2)))
    if mode == 14:
        x1, y1, x2, y2 = row
        if x1 == x2:
            raise HighSchoolDomainError("vertical line")
        return _encode(Fraction(y2 - y1, x2 - x1))
    if mode == 15:
        x1, y1, x2, y2 = row
        return _encode(Fraction((x2 - x1) ** 2 + (y2 - y1) ** 2, 1))
    if mode == 16:
        opposite, adjacent, hypotenuse = row
        if hypotenuse <= 0 or opposite * opposite + adjacent * adjacent != hypotenuse * hypotenuse:
            raise HighSchoolDomainError("not a rational right-triangle triple")
        return _encode((Fraction(opposite, hypotenuse), Fraction(adjacent, hypotenuse)))
    if mode == 17:
        trials, marked = row
        return _encode(Fraction(_choose(trials, marked), 2 ** trials))
    if mode == 18:
        left1, right1, left2, right2 = row
        if left1 > right1 or left2 > right2:
            raise HighSchoolDomainError("malformed closed interval")
        left, right = max(left1, left2), min(right1, right2)
        if left > right:
            return _encode((Fraction(0), Fraction(0), Fraction(0)))
        return _encode((Fraction(1), Fraction(left), Fraction(right)))
    if mode == 19:
        numerator, denominator = row
        if denominator == 0:
            raise HighSchoolDomainError("zero denominator")
        return _encode(Fraction(numerator, denominator))
    raise HighSchoolDomainError("unknown opaque recipe")


@dataclass(frozen=True, slots=True)
class HighSchoolProgram:
    program_id: str
    opaque_mode: int

    def execute(self, row: Sequence[int]) -> tuple[int, ...]:
        return _recipe(self.opaque_mode, tuple(map(int, row)))

    def to_dict(self) -> dict[str, Any]:
        return {"program_id": self.program_id, "opaque_mode": self.opaque_mode}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HighSchoolProgram":
        program = compile_high_school_program(int(value["opaque_mode"]))
        if value.get("program_id") != program.program_id:
            raise ValueError("high-school program digest mismatch")
        return program


def compile_high_school_program(mode: int) -> HighSchoolProgram:
    if mode not in range(20):
        raise ValueError("opaque mode is outside the learned composition palette")
    payload = json.dumps({"substrate": "exact-composition-v0.1", "mode": mode}, sort_keys=True)
    return HighSchoolProgram("HSP-" + hashlib.sha256(payload.encode()).hexdigest()[:16], mode)


@dataclass(frozen=True, slots=True)
class AnonymousHighSchoolTask:
    task_id: str
    input_rows: tuple[tuple[int, ...], ...]
    output_rows: tuple[tuple[int, ...], ...]

    @classmethod
    def create(cls, task_id: str, inputs: Sequence[Sequence[int]], outputs: Sequence[Sequence[int]]) -> "AnonymousHighSchoolTask":
        rows = tuple(tuple(map(int, row)) for row in inputs)
        targets = tuple(tuple(map(int, row)) for row in outputs)
        if not rows or len(rows) != len(targets):
            raise ValueError("anonymous task requires aligned evidence")
        return cls(task_id, rows, targets)


@dataclass(frozen=True, slots=True)
class HighSchoolSearchReport:
    task_id: str
    candidate_count: int
    exact_candidate_count: int
    selected: HighSchoolProgram
    selected_token_cost: int


class AnonymousHighSchoolSearch:
    def search(self, task: AnonymousHighSchoolTask) -> HighSchoolSearchReport:
        exact: list[HighSchoolProgram] = []
        costs: dict[str, int] = {}
        for mode in range(20):
            program = compile_high_school_program(mode)
            passed = True
            cost = 2
            for row, expected in zip(task.input_rows, task.output_rows, strict=True):
                try:
                    actual = program.execute(row)
                    cost += len(row) + len(actual)
                except (HighSchoolDomainError, OverflowError, ValueError):
                    passed = False
                    break
                if actual != expected:
                    passed = False
                    break
            if passed:
                exact.append(program)
                costs[program.program_id] = cost
        if not exact:
            raise ValueError(f"no exact composition for anonymous task {task.task_id}")
        exact.sort(key=lambda item: (costs[item.program_id], item.program_id))
        selected = exact[0]
        return HighSchoolSearchReport(task.task_id, 20, len(exact), selected, costs[selected.program_id])
