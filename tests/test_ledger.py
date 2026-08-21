from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator.ledger import KnowledgeLedger, LedgerError
from akgm_n0.learner import add, parameter, read_offset


FIXED_TIME = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


class LedgerTests(unittest.TestCase):
    def test_status_history_is_append_only_and_reloadable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "knowledge_ledger.jsonl"
            ledger = KnowledgeLedger(path, clock=lambda: FIXED_TIME)
            knowledge_id = ledger.propose(
                add(read_offset(0), parameter(0)),
                parent_ids=("p_read_offset", "p_add", "p_scalar_parameter"),
                provenance={"run_id": "RUN-test-001"},
            )
            ledger.transition(
                knowledge_id,
                "fit_passed",
                reason="development_fit_passed",
                evidence={"mse": 0.0},
            )
            ledger.transition(
                knowledge_id,
                "verified",
                reason="required_cases_passed",
                evidence={"required_failures": 0},
            )
            ledger.transition(
                knowledge_id,
                "bounded",
                reason="challenge_counterexample_found",
                evidence={"counterexample_count": 3},
            )

            self.assertEqual(knowledge_id, "K-000001")
            self.assertEqual(ledger.get(knowledge_id).status, "bounded")
            self.assertEqual(len(ledger.events), 4)
            reloaded = KnowledgeLedger(path, clock=lambda: FIXED_TIME)
            self.assertEqual(reloaded.get(knowledge_id).status, "bounded")
            self.assertEqual(reloaded.events, ledger.events)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 4)

    def test_invalid_transition_is_rejected_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "knowledge_ledger.jsonl"
            ledger = KnowledgeLedger(path, clock=lambda: FIXED_TIME)
            knowledge_id = ledger.propose(
                read_offset(0), parent_ids=("p_read_offset",), provenance={}
            )
            with self.assertRaises(LedgerError):
                ledger.transition(knowledge_id, "bounded", reason="invalid_skip")
            self.assertEqual(len(ledger.events), 1)

    def test_hash_chain_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "knowledge_ledger.jsonl"
            ledger = KnowledgeLedger(path, clock=lambda: FIXED_TIME)
            ledger.propose(read_offset(0), parent_ids=("p_read_offset",), provenance={})
            event = json.loads(path.read_text(encoding="utf-8"))
            event["reason"] = "tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaises(LedgerError):
                KnowledgeLedger(path, clock=lambda: FIXED_TIME)


if __name__ == "__main__":
    unittest.main()

