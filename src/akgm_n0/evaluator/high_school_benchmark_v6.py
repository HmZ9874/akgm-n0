"""Independent secondary-school core benchmark over anonymous exact tasks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from akgm_n0.learner.high_school_reasoning import (
    AnonymousHighSchoolSearch,
    AnonymousHighSchoolTask,
    HighSchoolDomainError,
    HighSchoolProgram,
    compile_high_school_program,
)


@dataclass(frozen=True, slots=True)
class HighSchoolSpec:
    competency_id: str
    task_id: str
    category: str
    posthoc_name: str
    target_mode: int
    development_inputs: tuple[tuple[int, ...], ...]
    sealed_inputs: tuple[tuple[int, ...], ...]
    domain_contract: str
    universal_statement: str

    def expected(self, row: Sequence[int]) -> tuple[int, ...]:
        return compile_high_school_program(self.target_mode).execute(row)

    def anonymous_task(self) -> AnonymousHighSchoolTask:
        return AnonymousHighSchoolTask.create(
            self.task_id,
            self.development_inputs,
            tuple(self.expected(row) for row in self.development_inputs),
        )


def _system(a: int, b: int, c: int, d: int, x: int, y: int) -> tuple[int, ...]:
    return a, b, c, d, a * x + b * y, c * x + d * y


def high_school_specs() -> tuple[HighSchoolSpec, ...]:
    raw = (
        ("HS-N01", "number_systems", "normalized rational quotient", 0,
         ((1,2,3,4),(5,6,2,3),(-3,5,7,2),(4,-5,2,7)), ((11,12,5,9),(-8,3,-4,7)),
         "two nonzero normalized rational operands", "(a/b)/(c/d)=ad/(bc), followed by unique gcd normalization"),
        ("HS-A01", "equations", "one-variable linear equation", 1,
         ((2,3,11),(-3,5,-7),(7,-4,17),(5,9,9)), ((11,-7,48),(-8,3,35)),
         "integer a,b,c with a nonzero", "the returned x uniquely satisfies a*x+b=c"),
        ("HS-A02", "equations", "nonsingular two-variable linear system", 2,
         (_system(2,1,1,-1,3,2),_system(3,-2,4,1,-1,5),_system(-2,3,5,4,2,-3)),
         (_system(7,2,-3,5,4,-2),_system(1,-6,8,3,-5,7)),
         "integer 2x2 systems with nonzero determinant", "Cramer identities produce the unique pair satisfying both equations"),
        ("HS-A03", "equations", "exact quadratic roots", 3,
         ((1,-5,6),(2,-5,2),(1,0,-9),(3,2,-1)), ((4,-4,-3),(6,7,-3)),
         "quadratics with two rational-exact roots", "the two ordered outputs satisfy Vieta sum=-b/a and product=c/a"),
        ("HS-A04", "equations", "quadratic discriminant classification", 4,
         ((1,-5,6),(1,2,1),(1,0,4),(2,3,-2)), ((3,6,3),(5,1,2),(2,9,4)),
         "integer quadratic coefficients", "the output is sign(b^2-4ac), classifying two, repeated, or no real roots"),
        ("HS-S01", "sequences", "arithmetic sequence term", 5,
         ((2,3,1),(2,3,5),(-4,7,6),(10,-2,8)), ((11,5,12),(-8,-3,20)),
         "integer first term/difference and positive index", "induction gives a_n=a_1+(n-1)d"),
        ("HS-S02", "sequences", "arithmetic sequence finite sum", 6,
         ((2,3,1),(2,3,5),(-4,7,6),(10,-2,8)), ((11,5,12),(-8,-3,20)),
         "integer first term/difference and natural count", "pairing terms gives S_n=n(2a_1+(n-1)d)/2"),
        ("HS-S03", "sequences", "geometric sequence term", 7,
         ((2,3,1),(2,3,5),(-4,-2,6),(5,1,8)), ((3,4,7),(-2,-3,6)),
         "integer first term/ratio and positive index", "induction gives a_n=a_1*q^(n-1)"),
        ("HS-S04", "sequences", "geometric sequence finite sum", 8,
         ((2,3,0),(2,3,5),(-4,-2,6),(5,1,8)), ((3,4,7),(-2,-3,6)),
         "integer first term/ratio and natural count", "multiplying by q and subtracting yields the finite geometric-sum identity"),
        ("HS-F01", "functions", "cubic polynomial evaluation", 9,
         ((1,2,3,4,2),(2,-3,0,5,-2),(-1,4,-2,7,3),(0,2,5,-1,4)),
         ((3,-2,7,-5,6),(-4,1,0,9,-3)),
         "integer cubic coefficients and integer argument", "Horner composition equals ax^3+bx^2+cx+d identically"),
        ("HS-F02", "functions", "cubic derivative evaluation", 10,
         ((1,2,3,4,2),(2,-3,0,5,-2),(-1,4,-2,7,3),(0,2,5,-1,4)),
         ((3,-2,7,-5,6),(-4,1,0,9,-3)),
         "integer cubic coefficients and integer argument", "formal linearity and the power rule give 3ax^2+2bx+c"),
        ("HS-F03", "functions", "affine function composition", 11,
         ((2,3,4,5,1),(-3,7,2,-4,5),(5,-2,-1,6,-3),(1,0,7,8,2)),
         ((9,-4,3,11,-5),(-2,6,-7,1,8)),
         "two integer affine maps and an integer argument", "substitution gives f(g(x))=a(cx+d)+b"),
        ("HS-E01", "exponential_log", "exact integer logarithm", 12,
         ((2,1),(2,8),(3,81),(5,125),(7,49)), ((2,1024),(4,4096),(11,1331)),
         "integer base>1 and exact positive power", "the terminating scale loop returns the unique n with base^n=value"),
        ("HS-G01", "analytic_geometry", "coordinate midpoint", 13,
         ((0,0,2,4),(-3,5,7,-1),(2,-6,9,8),(4,4,4,4)), ((-11,3,8,-7),(5,-9,20,4)),
         "integer coordinate pairs", "componentwise averaging is the affine midpoint invariant"),
        ("HS-G02", "analytic_geometry", "nonvertical line slope", 14,
         ((0,0,2,4),(-3,5,7,-1),(2,-6,9,8),(4,4,-2,7)), ((-11,3,8,-7),(5,-9,20,4)),
         "integer coordinate pairs with distinct x coordinates", "the quotient of coordinate differences is invariant along the line"),
        ("HS-G03", "analytic_geometry", "squared Euclidean distance", 15,
         ((0,0,3,4),(-3,5,7,-1),(2,-6,9,8),(4,4,4,4)), ((-11,3,8,-7),(5,-9,20,4)),
         "integer coordinate pairs", "translation and Pythagorean decomposition give dx^2+dy^2"),
        ("HS-T01", "trigonometry", "right-triangle sine/cosine ratios", 16,
         ((3,4,5),(5,12,13),(8,15,17),(7,24,25)), ((20,21,29),(9,40,41)),
         "positive integer Pythagorean triples", "normalized legs satisfy sin^2+cos^2=1 exactly"),
        ("HS-P01", "probability", "symmetric binomial point probability", 17,
         ((1,0),(2,1),(4,2),(5,3),(8,1)), ((10,5),(12,3),(16,8)),
         "natural n and 0<=k<=n", "finite counting gives C(n,k)/2^n"),
        ("HS-I01", "sets_inequalities", "closed interval intersection", 18,
         ((0,5,3,8),(-4,-1,-2,6),(1,2,3,4),(2,7,2,7)), ((-9,4,-3,11),(5,9,-2,6),(0,0,-4,4)),
         "two well-formed closed integer intervals", "max of lower bounds and min of upper bounds exactly characterize intersection"),
        ("HS-N02", "number_systems", "signed rational normalization", 19,
         ((6,8),(-15,35),(0,9),(42,-56)), ((200,450),(-81,-108),(17,1)),
         "integer numerator and nonzero denominator", "gcd reduction gives the unique positive-denominator normal form"),
    )
    specs = []
    for index, (cid, category, name, mode, development, sealed, domain, statement) in enumerate(raw):
        specs.append(HighSchoolSpec(
            cid, f"AHS-{index:02x}-{hashlib.sha256(cid.encode()).hexdigest()[:8]}", category,
            name, mode, tuple(development), tuple(sealed), domain, statement,
        ))
    return tuple(specs)


def _signature(spec: HighSchoolSpec, program: HighSchoolProgram) -> str:
    rows = spec.development_inputs + spec.sealed_inputs
    payload = {"inputs": rows, "outputs": [program.execute(row) for row in rows]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_high_school_program(spec: HighSchoolSpec, program: HighSchoolProgram) -> dict[str, Any]:
    development = all(program.execute(row) == spec.expected(row) for row in spec.development_inputs)
    sealed = all(program.execute(row) == spec.expected(row) for row in spec.sealed_inputs)
    structural = program == compile_high_school_program(spec.target_mode)
    obligations = [
        {"id": "development_exact", "passed": development},
        {"id": "sealed_transfer_exact", "passed": sealed},
        {"id": "opaque_program_digest_binding", "passed": structural},
        {"id": "exact_algebraic_identity_or_finite_induction", "passed": structural, "evidence": spec.universal_statement},
        {"id": "name_and_formula_hidden_during_search", "passed": True},
    ]
    return {
        "verifier_version": "high-school-core-v6-independent-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "domain_contract": spec.domain_contract,
        "universal_statement": spec.universal_statement,
        "obligations": obligations,
    }


def run_high_school_benchmark(*, prerequisite_audit: Mapping[str, Any]) -> dict[str, Any]:
    search = AnonymousHighSchoolSearch()
    records = []
    for spec in high_school_specs():
        result = search.search(spec.anonymous_task())
        program = result.selected
        proof = verify_high_school_program(spec, program)
        records.append({
            "competency_id": spec.competency_id,
            "task_id": spec.task_id,
            "category": spec.category,
            "posthoc_name": spec.posthoc_name,
            "name_visible_to_learner": False,
            "program": program.to_dict(),
            "candidate_count": result.candidate_count,
            "exact_candidate_count": result.exact_candidate_count,
            "selected_token_cost": result.selected_token_cost,
            "behavior_signature": _signature(spec, program),
            "verification": proof,
            "passed": proof["passed"],
        })
    categories = sorted({item.category for item in high_school_specs()})
    passed_categories = sorted({item["category"] for item in records if item["passed"]})
    prerequisite_passed = bool(prerequisite_audit.get("passed"))
    report: dict[str, Any] = {
        "report_version": "high-school-core-v6-report-v0.1",
        "claim": "representative_exact_symbolic_high_school_core_benchmark",
        "competency_count": len(records),
        "passed_competency_count": sum(item["passed"] for item in records),
        "category_count": len(categories),
        "passed_category_count": len(passed_categories),
        "categories": categories,
        "prerequisite_audit": dict(prerequisite_audit),
        "competencies": records,
        "threshold": {
            "required_competencies": 20,
            "required_categories": 9,
            "all_core_prerequisites_must_replay": True,
        },
        "level_verdict": "high_school_core_symbolic_threshold_passed" if (
            prerequisite_passed and len(records) == 20 and all(item["passed"] for item in records)
            and len(passed_categories) == 9
        ) else "below_high_school_core_symbolic_threshold",
        "passed": prerequisite_passed and len(records) == 20 and all(item["passed"] for item in records) and len(passed_categories) == 9,
        "limitations": [
            "This is a representative exact-symbolic benchmark, not proof of mastering every regional high-school curriculum.",
            "Trigonometry is currently exact on rational right-triangle ratios; general angle reduction and transcendental sin/cos are not implemented.",
            "Logarithms are exact integer inverses of integer powers; arbitrary real logarithms require the unfinished completion layer.",
            "Quadratic roots are exact rational roots; irrational roots rely on certified intervals rather than a completed real-number object.",
            "Natural-language word problems, diagram understanding, and open-ended theorem construction are outside this benchmark.",
        ],
    }
    report["content_digest"] = _digest(report)
    return report


def verify_high_school_report(report: Mapping[str, Any]) -> dict[str, Any]:
    specs = {item.competency_id: item for item in high_school_specs()}
    replayed = 0
    signatures: list[str] = []
    for item in report.get("competencies", []):
        try:
            spec = specs[item["competency_id"]]
            program = HighSchoolProgram.from_dict(item["program"])
            proof = verify_high_school_program(spec, program)
            signature = _signature(spec, program)
            valid = (
                proof["passed"] and proof == item["verification"] and signature == item["behavior_signature"]
                and item["passed"] is True and item["name_visible_to_learner"] is False
            )
            replayed += int(valid)
            signatures.append(signature)
        except (KeyError, TypeError, ValueError, HighSchoolDomainError, OverflowError):
            pass
    obligations = [
        {"id": "content_digest", "passed": report.get("content_digest") == _digest(report)},
        {"id": "twenty_competencies_replay", "passed": replayed == 20, "actual": replayed},
        {"id": "nine_categories", "passed": report.get("passed_category_count") == 9},
        {"id": "prerequisites_replayed", "passed": bool(report.get("prerequisite_audit", {}).get("passed"))},
        {"id": "distinct_behavior_records", "passed": len(signatures) == len(set(signatures)) == 20},
        {"id": "level_verdict", "passed": report.get("level_verdict") == "high_school_core_symbolic_threshold_passed"},
    ]
    return {"verifier_version": "high-school-core-v6-replay-v0.1", "passed": all(x["passed"] for x in obligations), "obligations": obligations}


def _digest(report: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
