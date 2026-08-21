from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.evaluator import FormulaSuccessRoom
from akgm_n0.learner import (
    CompositionExecutor,
    CompositionGraphProgram,
    CompositionNode,
    NumericTableObservation,
    ProofCarryingReasoner,
    ReasoningTraceVerifier,
    ReflectiveProgram,
    composition_key,
)


ROOT = Path(__file__).resolve().parents[1]


class ReasoningEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        proof_report = json.loads(
            (ROOT / "reports/data/universal_formula_proof_latest.json").read_text(
                encoding="utf-8"
            )
        )
        success = FormulaSuccessRoom(
            ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
        )
        definitions = {record.operation_id: record.definition for record in success.records}
        wanted = {
            "2^n",
            "3^n",
            "bit_length(n)",
            "abs(a-b)",
            "n^2",
            "n mod 4",
            "floor(sqrt(n))",
            "min(a,b)",
        }
        formulas = [
            item for item in proof_report["formulas"] if item["display_formula"] in wanted
        ]
        cls.by_name = {item["display_formula"]: item for item in formulas}
        cls.library = {
            item["source_operation_id"]: ReflectiveProgram.from_dict(
                dict(definitions[item["source_operation_id"]])
            )
            for item in formulas
        }
        cls.arities = {
            item["source_operation_id"]: int(item["domain"]["arity"])
            for item in formulas
        }
        cls.proofs = {
            item["source_operation_id"]: item["universal_room_record_id"]
            for item in formulas
        }
        ids = {name: item["source_operation_id"] for name, item in cls.by_name.items()}
        cls.target = CompositionGraphProgram(
            (
                CompositionNode(ids["3^n"], ("input:0",)),
                CompositionNode(ids["2^n"], ("input:0",)),
                CompositionNode(ids["abs(a-b)"], ("node:0", "node:1")),
                CompositionNode(ids["bit_length(n)"], ("node:2",)),
            )
        )

    def test_variable_depth_reasoner_discovers_four_node_graph_without_template(self) -> None:
        executor = CompositionExecutor(self.library)
        rows = tuple((float(value),) for value in range(7))
        outputs = tuple(executor.execute(self.target, row).output_value for row in rows)
        observation = NumericTableObservation.create(
            opaque_session_id="reasoning-four-node-unit",
            input_rows=rows,
            output_values=outputs,
            validity_mask=(True,) * len(rows),
            action_receipt="anonymous_reasoning_evidence",
        )
        report = ProofCarryingReasoner(
            self.library,
            self.arities,
            self.proofs,
            maximum_depth=3,
            maximum_nodes=5,
            maximum_argument_states=100,
            beam_per_depth=2500,
            top_k=5000,
        ).search(observation)
        target = next(candidate for candidate in report.top_candidates if candidate.exact)
        self.assertTrue(target.exact)
        self.assertEqual(target.reasoning_depth, 3)
        self.assertEqual(len(target.reasoning_steps), 4)
        self.assertNotEqual(composition_key(target.program), "")
        self.assertTrue(
            ReasoningTraceVerifier(self.library, self.proofs).verify(
                target, tuple(zip(rows, outputs, strict=True))
            )["passed"]
        )

    def test_latest_reasoning_report_is_replayable(self) -> None:
        report = json.loads(
            (ROOT / "reports/data/reasoning_optimization_latest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(all(gate["passed"] for gate in report["gates"]))
        self.assertGreaterEqual(report["result"]["reasoning_depth"], 3)
        self.assertGreaterEqual(report["result"]["reasoning_step_count"], 4)
        self.assertTrue(report["verification"]["passed"])
        self.assertGreater(
            report["sealed_transfer"]["passed"],
            report["fixed_depth_baseline"]["sealed_passed"],
        )


if __name__ == "__main__":
    unittest.main()
