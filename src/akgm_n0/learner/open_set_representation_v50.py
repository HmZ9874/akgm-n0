"""V50 open set-representation synthesis over anonymous event values.

The learner receives only ordered numeric values and four substrate operations.
It invents ASTs over adjacent empirical survival levels, rejects identities and
tautologies, and selects a relation by cross-group stability and predictive
reconstruction.  Domain names and human laws are unavailable during search.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np


def canonical_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ast_key(ast):
    return json.dumps(ast, sort_keys=True, separators=(",", ":"))


def ast_nodes(ast):
    if "var" in ast:
        return 1
    return 1 + sum(ast_nodes(arg) for arg in ast["args"])


def ast_dependencies(ast):
    if "var" in ast:
        return {ast["var"]}
    result = set()
    for arg in ast["args"]:
        result.update(ast_dependencies(arg))
    return result


def evaluate_ast(ast, a, b):
    if "var" in ast:
        return a if ast["var"] == "A" else b
    left = evaluate_ast(ast["args"][0], a, b)
    right = evaluate_ast(ast["args"][1], a, b)
    op = ast["op"]
    if op == "ADD":
        return left + right
    if op == "SUB":
        return left - right
    if op == "MUL":
        return left * right
    if op == "SAFE_DIV":
        return left / right if abs(right) > 1e-12 else math.nan
    raise ValueError(op)


class RepresentationLanguageV50:
    OPERATIONS = ("ADD", "SUB", "MUL", "SAFE_DIV")

    @staticmethod
    def _nontrivial(ast):
        if ast_dependencies(ast) != {"A", "B"}:
            return False
        probes = ((0.17, 0.41), (0.29, 0.73), (0.61, 0.22), (0.83, 0.57))
        values = [evaluate_ast(ast, a, b) for a, b in probes]
        if not all(math.isfinite(value) for value in values):
            return False
        if max(values) - min(values) < 1e-8:
            return False
        base = evaluate_ast(ast, 0.37, 0.59)
        sensitive_a = abs(evaluate_ast(ast, 0.41, 0.59) - base) > 1e-8
        sensitive_b = abs(evaluate_ast(ast, 0.37, 0.63) - base) > 1e-8
        return sensitive_a and sensitive_b

    def grow(self, max_nodes=5):
        leaves = ({"var": "A"}, {"var": "B"})
        expressions = {ast_key(item): item for item in leaves}
        frontier = list(leaves)
        while frontier:
            current = frontier.pop(0)
            existing = list(expressions.values())
            for other in existing:
                for left, right in ((current, other), (other, current)):
                    for op in self.OPERATIONS:
                        candidate = {"op": op, "args": [left, right]}
                        if ast_nodes(candidate) > max_nodes:
                            continue
                        key = ast_key(candidate)
                        if key not in expressions:
                            expressions[key] = candidate
                            frontier.append(candidate)
            if len(expressions) > 1200:
                break
        candidates = [item for item in expressions.values() if self._nontrivial(item)]
        return tuple(sorted(candidates, key=lambda item: (ast_nodes(item), ast_key(item))))


@dataclass(frozen=True, slots=True)
class SurvivalProfileV50:
    group_id: str
    thresholds: tuple[float, ...]
    survival: tuple[float, ...]


class AnonymousSetWorldV50:
    @staticmethod
    def infer_grid(training_traces):
        values = sorted({float(value) for trace in training_traces for value in trace["outputs"]})
        differences = [right - left for left, right in zip(values, values[1:], strict=False) if right - left > 1e-9]
        if not differences:
            raise ValueError("event values have no ordered resolution")
        step = float(np.median(differences))
        lower = values[0]
        pooled = np.asarray([float(value) for trace in training_traces for value in trace["outputs"]])
        thresholds = []
        current = lower
        while current <= values[-1] + 1e-9:
            survival = float(np.mean(pooled >= current - 1e-9))
            if survival >= 0.04:
                thresholds.append(round(current, 10))
            current += step
        if len(thresholds) < 6:
            raise ValueError("insufficient empirical threshold levels")
        return {
            "origin": lower,
            "step": step,
            "thresholds": tuple(thresholds),
            "derived_from": "training_values_only",
        }

    @staticmethod
    def profiles(traces, thresholds, group_prefix, group_count=4):
        groups = [[] for _ in range(group_count)]
        for index, trace in enumerate(traces):
            groups[index % group_count].extend(map(float, trace["outputs"]))
        profiles = []
        for index, values in enumerate(groups):
            array = np.asarray(values, dtype=float)
            survival = tuple(float(np.mean(array >= threshold - 1e-9)) for threshold in thresholds)
            profiles.append(SurvivalProfileV50(
                f"{group_prefix}-{index}", tuple(thresholds), survival,
            ))
        return tuple(profiles)


def adjacent_pairs(profiles):
    pairs = []
    for profile in profiles:
        for index, (a, b) in enumerate(zip(profile.survival, profile.survival[1:], strict=False)):
            if a > 1e-12 and b > 1e-12:
                pairs.append((profile.group_id, index, a, b))
    return pairs


def solve_b(ast, a, target):
    grid = np.linspace(1e-6, 1.0, 2001)
    values = np.asarray([evaluate_ast(ast, a, float(b)) for b in grid], dtype=float)
    finite = np.isfinite(values)
    if not finite.any():
        return math.nan
    errors = np.abs(values[finite] - target)
    return float(grid[finite][int(np.argmin(errors))])


def relation_metrics(ast, constant, profiles):
    pairs = adjacent_pairs(profiles)
    relation_values = np.asarray([evaluate_ast(ast, a, b) for _, _, a, b in pairs], dtype=float)
    finite = np.isfinite(relation_values)
    if not finite.all() or len(relation_values) == 0:
        return None
    predictions = np.asarray([solve_b(ast, a, constant) for _, _, a, _ in pairs])
    observed = np.asarray([b for _, _, _, b in pairs])
    current = np.asarray([a for _, _, a, _ in pairs])
    if not np.isfinite(predictions).all():
        return None
    errors = predictions - observed
    baseline_errors = current - observed
    rmse = float(np.sqrt(np.mean(errors * errors)))
    baseline_rmse = float(np.sqrt(np.mean(baseline_errors * baseline_errors)))
    mean = float(relation_values.mean())
    dispersion = float(np.sqrt(np.mean((relation_values - constant) ** 2)))
    group_constants = {}
    for group_id in sorted({item[0] for item in pairs}):
        group_values = [evaluate_ast(ast, a, b) for gid, _, a, b in pairs if gid == group_id]
        group_constants[group_id] = float(np.mean(group_values))
    order = np.argsort(np.abs(errors))[::-1][:8]
    return {
        "pair_count": len(pairs),
        "relation_mean": mean,
        "relation_rmse_to_training_constant": dispersion,
        "relative_relation_dispersion": dispersion / max(abs(constant), 1e-12),
        "next_level_rmse": rmse,
        "identity_baseline_rmse": baseline_rmse,
        "prediction_rmse_ratio": rmse / max(baseline_rmse, 1e-15),
        "group_constants": group_constants,
        "maximum_group_constant_deviation": max(abs(value - constant) for value in group_constants.values()),
        "counterexamples": [
            {
                "group_id": pairs[index][0],
                "threshold_index": pairs[index][1],
                "current_survival": pairs[index][2],
                "next_survival": pairs[index][3],
                "predicted_next_survival": float(predictions[index]),
                "absolute_error": float(abs(errors[index])),
            }
            for index in order
        ],
    }


class OpenRepresentationForgeV50:
    def search(self, training_profiles, validation_profiles):
        candidates = RepresentationLanguageV50().grow(max_nodes=3)
        trials = []
        training_pairs = adjacent_pairs(training_profiles)
        for ast in candidates:
            values = np.asarray([evaluate_ast(ast, a, b) for _, _, a, b in training_pairs])
            if not np.isfinite(values).all():
                continue
            constant = float(np.median(values))
            training = relation_metrics(ast, constant, training_profiles)
            validation = relation_metrics(ast, constant, validation_profiles)
            if training is None or validation is None:
                continue
            score = (
                validation["prediction_rmse_ratio"]
                + 0.45 * validation["relative_relation_dispersion"]
                + 0.03 * validation["maximum_group_constant_deviation"] / max(abs(constant), 1e-12)
                + 0.002 * ast_nodes(ast)
            )
            trials.append({
                "ast": ast,
                "nodes": ast_nodes(ast),
                "constant": constant,
                "training": training,
                "validation": validation,
                "score": score,
            })
        trials.sort(key=lambda item: (item["score"], item["nodes"], ast_key(item["ast"])))
        selected = trials[0]
        payload = {"ast": selected["ast"], "constant": selected["constant"]}
        return {
            "semantic_id": "SETSEM-" + canonical_digest(payload)[:16],
            "kind": "synthesized_adjacent_set_relation",
            "selected": selected,
            "candidate_ast_count": len(candidates),
            "evaluated_candidate_count": len(trials),
            "top_trials": trials[:20],
            "host_selected": False,
            "human_law_name_received": False,
            "anti_triviality": {
                "depends_on_both_levels": ast_dependencies(selected["ast"]) == {"A", "B"},
                "counterfactual_sensitivity_checked": True,
                "tautologies_rejected": True,
            },
        }
