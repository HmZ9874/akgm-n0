"""Let verified micro-semantics compete for meaningless keyboard glyph slots."""

from __future__ import annotations

import hashlib
import json
import shutil
import string
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    HiddenIntegerGridEnvironment,
    KnowledgeLedger,
    MicroMistakeLibrary,
)
from akgm_n0.learner import (
    KeyboardSymbolArena,
    MicroProgramReductionScorer,
    MicroProgramSearch,
    UnboundSemanticError,
)


SECRET = b"keyboard-symbol-arena-v0.1"


def main() -> int:
    development_rows = (
        (2, 2),
        (2, 3),
        (3, 2),
        (4, 3),
        (-2, 3),
        (5, 2),
        (3, 4),
        (6, 5),
    )
    blind_rows = (
        (7, 5),
        (-4, 6),
        (11, 0),
        (2, 9),
        (9, 2),
        (-3, 8),
    )
    adversarial_rows = (
        (0, 7),
        (8, 0),
        (-5, 7),
        (12, 8),
        (1, 64),
    )
    development = HiddenIntegerGridEnvironment(
        development_rows, seed=501, secret=SECRET
    ).observe()
    blind = HiddenIntegerGridEnvironment(
        blind_rows, seed=502, secret=SECRET
    ).observe()
    adversarial = HiddenIntegerGridEnvironment(
        adversarial_rows, seed=503, secret=SECRET
    ).observe()

    initial_arena = KeyboardSymbolArena()
    conventional_glyphs_unbound = True
    for glyph in ("+", "-", "*", "/", "="):
        try:
            initial_arena.execute(glyph, (2, 3))
        except UnboundSemanticError:
            continue
        conventional_glyphs_unbound = False

    condition_key = "semantic-grid-" + hashlib.sha256(
        json.dumps(development_rows, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    failed_scope = "sealed_blind_semantic_validation"
    mistakes = MicroMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "micro_mistakes.jsonl"
    )
    search_report = MicroProgramSearch(
        top_k=200,
        candidate_gate=mistakes.candidate_gate(
            failed_scope=failed_scope, condition_key=condition_key
        ),
    ).search(development)

    all_cases = tuple(
        (row, output)
        for observation in (development, blind, adversarial)
        for row, output in zip(
            observation.input_rows, observation.output_values, strict=True
        )
    )
    scorer = MicroProgramReductionScorer()
    scored_candidates = [
        {
            "candidate_id": candidate.candidate_id,
            "development_fit_error": candidate.fit_error,
            "program": candidate.program.to_dict(),
            "score": scorer.score(candidate.program, all_cases),
        }
        for candidate in search_report.top_candidates
    ]
    scored_candidates.sort(
        key=lambda item: (
            -item["score"].reward,
            item["score"].description_cost,
            item["candidate_id"],
        )
    )
    verified = [item for item in scored_candidates if item["score"].verified]
    if not verified:
        raise RuntimeError("no candidate passed the registered reward eligibility gate")
    winner = verified[0]
    winner_score = winner["score"]

    arena = KeyboardSymbolArena()
    chosen_glyph, binding = arena.bind_reward_winner(
        winner_score.reduced_program, verification_status="bounded"
    )
    probe_output = arena.execute(chosen_glyph, (7, 5)).output_value
    reversed_arena = KeyboardSymbolArena(glyphs=tuple(reversed(string.punctuation)))
    reversed_glyph, reversed_binding = reversed_arena.bind_reward_winner(
        winner_score.reduced_program, verification_status="bounded"
    )
    glyph_order_invariant = (
        binding.operation_id == reversed_binding.operation_id
        and reversed_arena.execute(reversed_glyph, (7, 5)).output_value
        == probe_output
    )

    incorrect = [item for item in scored_candidates if not item["score"].verified]
    shortest_incorrect = min(
        incorrect,
        key=lambda item: (
            item["score"].description_cost,
            item["candidate_id"],
        ),
        default=None,
    )
    correctness_dominates = (
        shortest_incorrect is None
        or winner_score.reward > shortest_incorrect["score"].reward
    )
    reward_monotonic = all(
        left["score"].reward >= right["score"].reward
        for left, right in zip(verified, verified[1:])
    )

    gates = [
        {
            "gate_id": "all_keyboard_punctuation_slots_open",
            "passed": len(initial_arena.glyphs) == 32
            and len(initial_arena.unbound_glyphs) == 32,
            "actual": len(initial_arena.unbound_glyphs),
            "threshold": 32,
        },
        {
            "gate_id": "conventional_math_glyphs_have_no_intrinsic_semantics",
            "passed": conventional_glyphs_unbound,
            "actual": conventional_glyphs_unbound,
            "threshold": True,
        },
        {
            "gate_id": "mistake_memory_filters_prior_blind_failures",
            "passed": search_report.programs_filtered >= 4,
            "actual": search_report.programs_filtered,
            "threshold": 4,
        },
        {
            "gate_id": "verified_candidate_available",
            "passed": bool(verified),
            "actual": len(verified),
            "threshold": 1,
        },
        {
            "gate_id": "correctness_dominates_short_incorrect_programs",
            "passed": correctness_dominates,
            "actual": correctness_dominates,
            "threshold": True,
        },
        {
            "gate_id": "reduction_reward_is_monotonic",
            "passed": reward_monotonic,
            "actual": reward_monotonic,
            "threshold": True,
        },
        {
            "gate_id": "glyph_order_does_not_change_semantics",
            "passed": glyph_order_invariant,
            "actual": glyph_order_invariant,
            "threshold": True,
        },
        {
            "gate_id": "winner_executes_after_binding",
            "passed": probe_output == 35.0,
            "actual": probe_output,
            "threshold": 35.0,
        },
        {
            "gate_id": "multi_operation_library_growth",
            "passed": None,
            "actual": len(arena.bindings),
            "threshold": 5,
        },
    ]
    verdict = (
        "conditionally_passed"
        if all(gate["passed"] for gate in gates if gate["passed"] is not None)
        else "failed"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-keyboard-arena-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        winner_score.reduced_program,
        parent_ids=(
            "keyboard_punctuation_slots",
            "verification_gate",
            "micro_reducer",
            "mdl_reward",
        ),
        provenance={
            "run_id": run_id,
            "candidate_id": winner["candidate_id"],
            "chosen_glyph": chosen_glyph,
        },
        evidence={"reward": winner_score.to_dict()},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed",
        reason="reward_winner_passed_all_registered_numeric_cases",
        evidence={"case_count": len(all_cases)},
    )
    if verdict == "conditionally_passed":
        ledger.transition(
            knowledge_id,
            "verified",
            reason="reward_and_glyph_ablation_gates_passed",
            evidence={"gates": gates},
        )
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="only_one_semantic_operation_has_competed_so_far",
            evidence={"pending_gate": "multi_operation_library_growth"},
        )
    else:
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="keyboard_arena_gate_failed",
            evidence={"gates": gates},
        )

    score_table = [
        {
            "rank": index,
            "candidate_id": item["candidate_id"],
            "development_fit_error": item["development_fit_error"],
            **item["score"].to_dict(),
        }
        for index, item in enumerate(scored_candidates[:10], start=1)
    ]
    report = {
        "report_version": "keyboard-symbol-arena-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "全键盘标点符号语义竞技场",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "unbound_glyph_arena_plus_verified_mdl_reward",
        "symbol_arena": {
            "glyph_count": len(initial_arena.glyphs),
            "glyphs": list(initial_arena.glyphs),
            "all_initially_unbound": len(initial_arena.unbound_glyphs) == 32,
            "conventional_glyphs_unbound": conventional_glyphs_unbound,
            "chosen_glyph": chosen_glyph,
            "remaining_unbound_count": len(arena.unbound_glyphs),
            "binding": binding.to_dict(),
        },
        "learner_received": {
            "glyph_meanings": False,
            "natural_language": False,
            "target_formula": False,
            "reward_rule": {
                "eligibility": "all_registered_cases_exact",
                "description_cost": "reduced_nodes + 0.5*unique_nodes + 0.75*constant_leaves + 0.02*mean_steps + 0.1*original_nodes",
                "verified_reward_floor": scorer.VERIFIED_REWARD_FLOOR,
                "selection": "highest_reward_among_verified_candidates",
            },
        },
        "search": {
            "programs_generated": search_report.programs_generated,
            "programs_filtered_by_mistake_memory": search_report.programs_filtered,
            "verified_candidate_count": len(verified),
            "scored_candidate_count": len(scored_candidates),
        },
        "reward_ranking": score_table,
        "winner": {
            "source_candidate_id": winner["candidate_id"],
            "score": winner_score.to_dict(),
            "chosen_glyph": chosen_glyph,
            "operation_id": binding.operation_id,
            "probe": {"input": [7, 5], "output": probe_output},
        },
        "glyph_order_ablation": {
            "normal_order_glyph": chosen_glyph,
            "reversed_order_glyph": reversed_glyph,
            "same_operation_id": binding.operation_id
            == reversed_binding.operation_id,
            "same_output": glyph_order_invariant,
        },
        "gates": gates,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "All 32 printable ASCII punctuation glyphs are open, not every Unicode or physical keyboard-layout key.",
            "Glyphs are identifiers only; the micro-program and evidence define semantics.",
            "Correctness is a hard eligibility gate, so compression cannot reward a short false program into the library.",
            "Only one verified semantic family is currently bound; library-wide competition across multiple operations remains pending.",
            "The host still supplies the registered microstate substrate and bounded scheduler.",
        ],
    }
    artifact_path = run_directory / "keyboard_symbol_arena_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "keyboard_arena_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "keyboard_arena_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "glyph_count": len(initial_arena.glyphs),
                "all_initially_unbound": len(initial_arena.unbound_glyphs) == 32,
                "programs_generated": search_report.programs_generated,
                "programs_filtered_by_mistake_memory": search_report.programs_filtered,
                "verified_candidate_count": len(verified),
                "winner_candidate_id": winner["candidate_id"],
                "winner_reward": winner_score.reward,
                "winner_description_cost": winner_score.description_cost,
                "chosen_glyph": chosen_glyph,
                "operation_id": binding.operation_id,
                "remaining_unbound_glyphs": len(arena.unbound_glyphs),
                "glyph_order_invariant": glyph_order_invariant,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
