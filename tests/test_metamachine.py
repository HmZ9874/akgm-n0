from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenSymbolTraceEnvironment
from akgm_n0.learner import (
    InvalidStateGraph,
    StateGraphExecutor,
    StateGraphLibrary,
    StateGraphProgram,
    StateGraphSearch,
)


SECRET = b"metamachine-tests"
PERMUTATION = (1, 0)


def development_observation():
    traces = ((), (0,), (1,), (0, 0), (0, 1), (1, 0), (1, 1))
    return HiddenSymbolTraceEnvironment(
        traces,
        seed=101,
        secret=SECRET,
        symbol_permutation=PERMUTATION,
    ).observe()


class MetaMachineTests(unittest.TestCase):
    def test_public_surface_and_manifest_have_no_declared_high_level_operations(self) -> None:
        observation = development_observation()
        self.assertEqual(
            set(observation.to_public_dict()),
            {
                "opaque_session_id",
                "symbol_traces",
                "output_values",
                "validity_mask",
                "action_receipt",
            },
        )
        manifest_path = (
            PROJECT_ROOT / "configs" / "metamachine" / "substrate_manifest.yaml"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["declared_arithmetic_operations"], [])
        self.assertEqual(manifest["declared_structured_storage_operations"], [])
        self.assertEqual(manifest["declared_repetition_operations"], [])
        serialized = json.dumps(manifest).casefold()
        for forbidden in ("p_add", "p_subtract", "p_iterate", "p_multiply", "p_divide"):
            self.assertNotIn(forbidden, serialized)

    def test_search_creates_exact_two_state_graph_deterministically(self) -> None:
        search = StateGraphSearch(maximum_state_count=3, top_k=10)
        first = search.search(development_observation())
        second = search.search(development_observation())
        self.assertEqual(
            [item.candidate_id for item in first.top_candidates],
            [item.candidate_id for item in second.top_candidates],
        )
        exact = next(item for item in first.top_candidates if item.fit_error == 0.0)
        self.assertEqual(exact.reachable_state_count, 2)
        self.assertEqual(exact.program.state_count, 2)
        self.assertTrue(
            exact.program.transition_table[0][0] == 1
            or exact.program.transition_table[0][1] == 1
        )
        self.assertTrue(
            exact.program.transition_table[1][0] == 0
            or exact.program.transition_table[1][1] == 0
        )

    def test_discovered_graph_passes_longer_unseen_traces(self) -> None:
        report = StateGraphSearch(maximum_state_count=3, top_k=10).search(
            development_observation()
        )
        candidate = next(item for item in report.top_candidates if item.fit_error == 0.0)
        blind_private_traces = (
            (0, 1, 0),
            (1, 1, 1),
            (0, 0, 1, 1),
            (1, 0, 1, 0, 1),
            tuple((index * 7 + 1) % 2 for index in range(31)),
            tuple((index * 5 + 3) % 2 for index in range(64)),
        )
        blind = HiddenSymbolTraceEnvironment(
            blind_private_traces,
            seed=202,
            secret=SECRET,
            symbol_permutation=PERMUTATION,
        ).observe()
        executor = StateGraphExecutor()
        predictions = tuple(
            executor.execute(candidate.program, trace).output_value
            for trace in blind.symbol_traces
        )
        self.assertEqual(predictions, blind.output_values)

    def test_executor_enforces_state_and_step_bounds(self) -> None:
        executor = StateGraphExecutor(maximum_state_count=2, maximum_trace_steps=2)
        invalid = StateGraphProgram(
            state_count=2,
            initial_state_id=0,
            transition_table=((0, 2), (0, 1)),
            output_table=(0, 1),
        )
        with self.assertRaises(InvalidStateGraph):
            executor.execute(invalid, (0,))
        valid = StateGraphProgram(1, 0, ((0, 0),), (0,))
        with self.assertRaises(InvalidStateGraph):
            executor.execute(valid, (0, 0, 0))

    def test_verified_graph_can_be_promoted_and_called_by_opaque_id(self) -> None:
        report = StateGraphSearch(maximum_state_count=3, top_k=10).search(
            development_observation()
        )
        candidate = next(item for item in report.top_candidates if item.fit_error == 0.0)
        library = StateGraphLibrary()
        semantic = library.promote(candidate.program)
        self.assertTrue(semantic.operation_id.startswith("OP-"))
        self.assertIsNone(semantic.to_dict()["human_interpretation"])
        first = library.execute(semantic.operation_id, (0, 1, 0)).output_value
        second = library.execute(semantic.operation_id, (0, 1, 0)).output_value
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
