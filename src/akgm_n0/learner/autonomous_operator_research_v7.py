"""Target-free closure research for distinct exact integer operators.

Starting only from two opaque input leaves and composition by addition and
multiplication, the researcher grows polynomial computation graphs.  It keeps
one coefficient-free support pattern per operator, preventing constant or
coefficient changes from padding the discovery count.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from math import prod
from typing import Any, Mapping, Sequence


Monomial = tuple[int, int]
NormalForm = tuple[tuple[int, int, int], ...]


@dataclass(frozen=True, slots=True)
class OperatorExpression:
    op: str
    input_index: int = -1
    args: tuple["OperatorExpression", ...] = ()

    @classmethod
    def input(cls, index: int) -> "OperatorExpression":
        if index not in (0, 1):
            raise ValueError("operator research has two opaque input leaves")
        return cls("input", index, ())

    @classmethod
    def combine(cls, op: str, left: "OperatorExpression", right: "OperatorExpression") -> "OperatorExpression":
        if op not in ("add", "multiply"):
            raise ValueError("unsupported closure operation")
        return cls(op, -1, (left, right))

    @property
    def node_count(self) -> int:
        return 0 if self.op == "input" else 1 + sum(item.node_count for item in self.args)

    @property
    def depth(self) -> int:
        return 0 if self.op == "input" else 1 + max(item.depth for item in self.args)

    def execute(self, row: Sequence[int]) -> int:
        if len(row) < 2:
            raise ValueError("operator input is too narrow")
        if self.op == "input":
            return int(row[self.input_index])
        values = tuple(item.execute(row) for item in self.args)
        return values[0] + values[1] if self.op == "add" else values[0] * values[1]

    def to_dict(self) -> dict[str, Any]:
        if self.op == "input":
            return {"op": "input", "input_index": self.input_index}
        return {"op": self.op, "args": [item.to_dict() for item in self.args]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OperatorExpression":
        op = str(value["op"])
        if op == "input":
            return cls.input(int(value["input_index"]))
        args = tuple(cls.from_dict(item) for item in value["args"])
        if len(args) != 2:
            raise ValueError("binary closure node requires two arguments")
        return cls.combine(op, args[0], args[1])


def symbolic_normal_form(expression: OperatorExpression) -> NormalForm:
    def visit(node: OperatorExpression) -> dict[Monomial, int]:
        if node.op == "input":
            return {(1, 0) if node.input_index == 0 else (0, 1): 1}
        left, right = (visit(item) for item in node.args)
        if node.op == "add":
            result = dict(left)
            for monomial, coefficient in right.items():
                result[monomial] = result.get(monomial, 0) + coefficient
            return {key: value for key, value in result.items() if value}
        result: dict[Monomial, int] = {}
        for (lx, ly), left_coefficient in left.items():
            for (rx, ry), right_coefficient in right.items():
                key = (lx + rx, ly + ry)
                result[key] = result.get(key, 0) + left_coefficient * right_coefficient
        return {key: value for key, value in result.items() if value}

    polynomial = visit(expression)
    return tuple(sorted((x_degree, y_degree, coefficient) for (x_degree, y_degree), coefficient in polynomial.items()))


def execute_normal_form(normal_form: NormalForm, row: Sequence[int]) -> int:
    x, y = map(int, row[:2])
    return sum(coefficient * (x ** x_degree) * (y ** y_degree) for x_degree, y_degree, coefficient in normal_form)


def expression_digest(expression: OperatorExpression) -> str:
    payload = json.dumps(expression.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _power(index: int, exponent: int) -> OperatorExpression:
    if exponent < 1:
        raise ValueError("constant monomials are intentionally unavailable")
    leaf = OperatorExpression.input(index)
    result = leaf
    for _ in range(1, exponent):
        result = OperatorExpression.combine("multiply", result, leaf)
    return result


def expression_for_support(support: Sequence[Monomial], *, reverse: bool = False) -> OperatorExpression:
    ordered = list(reversed(tuple(support))) if reverse else list(support)
    terms: list[OperatorExpression] = []
    for x_degree, y_degree in ordered:
        if x_degree < 0 or y_degree < 0 or x_degree + y_degree < 1:
            raise ValueError("invalid nonconstant monomial")
        if x_degree and y_degree:
            term = OperatorExpression.combine("multiply", _power(0, x_degree), _power(1, y_degree))
        elif x_degree:
            term = _power(0, x_degree)
        else:
            term = _power(1, y_degree)
        terms.append(term)
    result = terms[0]
    for term in terms[1:]:
        result = OperatorExpression.combine("add", result, term)
    return result


@dataclass(frozen=True, slots=True)
class DiscoveredOperator:
    operator_id: str
    expression: OperatorExpression
    normal_form: NormalForm
    support_signature: str
    behavior_signature: str
    token_cost: int
    discovery_rank: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "expression": self.expression.to_dict(),
            "normal_form": [list(item) for item in self.normal_form],
            "support_signature": self.support_signature,
            "behavior_signature": self.behavior_signature,
            "token_cost": self.token_cost,
            "discovery_rank": self.discovery_rank,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DiscoveredOperator":
        expression = OperatorExpression.from_dict(value["expression"])
        return cls(
            str(value["operator_id"]), expression,
            tuple(tuple(map(int, item)) for item in value["normal_form"]),
            str(value["support_signature"]), str(value["behavior_signature"]),
            int(value["token_cost"]), int(value["discovery_rank"]),
        )


@dataclass(frozen=True, slots=True)
class OperatorResearchReport:
    target_count: int
    monomial_count: int
    supports_considered: int
    excluded_existing_count: int
    discoveries: tuple[DiscoveredOperator, ...]


class AutonomousOperatorResearch:
    PROBE_ROWS = tuple((x, y) for x in range(-3, 4) for y in range(-3, 4))

    def __init__(self, *, maximum_total_degree: int = 6, target_count: int = 500) -> None:
        if maximum_total_degree != 6:
            raise ValueError("the fixed proof grid currently certifies total degree at most six")
        if target_count < 1:
            raise ValueError("target count must be positive")
        self.maximum_total_degree = maximum_total_degree
        self.target_count = target_count

    def research(self) -> OperatorResearchReport:
        monomials = tuple(
            (x_degree, total - x_degree)
            for total in range(1, self.maximum_total_degree + 1)
            for x_degree in range(total + 1)
        )
        known_supports = {frozenset({(1, 0), (0, 1)})}
        proposals = []
        considered = excluded = 0
        for support_size in range(2, 5):
            for support_tuple in itertools.combinations(monomials, support_size):
                considered += 1
                support = frozenset(support_tuple)
                depends_x = any(x_degree for x_degree, _ in support)
                depends_y = any(y_degree for _, y_degree in support)
                if not (depends_x and depends_y):
                    continue
                if support in known_supports:
                    excluded += 1
                    continue
                expression = expression_for_support(tuple(sorted(support)))
                normal_form = symbolic_normal_form(expression)
                if any(coefficient != 1 for _, _, coefficient in normal_form):
                    continue
                support_payload = tuple((x_degree, y_degree) for x_degree, y_degree, _ in normal_form)
                support_signature = hashlib.sha256(repr(support_payload).encode()).hexdigest()
                behavior = tuple(expression.execute(row) for row in self.PROBE_ROWS)
                behavior_signature = hashlib.sha256(repr(behavior).encode()).hexdigest()
                program_digest = expression_digest(expression)
                proposals.append((
                    expression.node_count,
                    max(x + y for x, y in support),
                    support_size,
                    support_signature,
                    DiscoveredOperator(
                        "AOP7-" + program_digest[:16], expression, normal_form,
                        support_signature, behavior_signature, expression.node_count, 0,
                    ),
                ))
        proposals.sort(key=lambda item: item[:4])
        selected = []
        seen_supports: set[str] = set()
        seen_behaviors: set[str] = set()
        for proposal in proposals:
            item = proposal[-1]
            if item.support_signature in seen_supports or item.behavior_signature in seen_behaviors:
                continue
            rank = len(selected) + 1
            selected.append(DiscoveredOperator(
                item.operator_id, item.expression, item.normal_form, item.support_signature,
                item.behavior_signature, item.token_cost, rank,
            ))
            seen_supports.add(item.support_signature)
            seen_behaviors.add(item.behavior_signature)
            if len(selected) == self.target_count:
                break
        if len(selected) != self.target_count:
            raise ValueError(f"closure research found only {len(selected)} distinct operators")
        return OperatorResearchReport(
            self.target_count, len(monomials), considered, excluded, tuple(selected)
        )
