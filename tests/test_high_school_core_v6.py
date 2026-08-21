from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from akgm_n0.evaluator.high_school_benchmark_v6 import (
    run_high_school_benchmark,
    verify_high_school_report,
)
from akgm_n0.evaluator.high_school_room_v6 import HighSchoolCapabilityRoom


ROOT = Path(__file__).resolve().parents[1]


class HighSchoolCoreV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.persisted = json.loads(
            (ROOT / "reports/data/high_school_core_v6_latest.json").read_text(encoding="utf-8")
        )
        cls.benchmark = cls.persisted["benchmark"]

    def test_high_school_core_threshold_requires_all_domains(self) -> None:
        self.assertTrue(self.benchmark["passed"])
        self.assertEqual(self.benchmark["passed_competency_count"], 20)
        self.assertEqual(self.benchmark["passed_category_count"], 9)
        self.assertEqual(self.benchmark["level_verdict"], "high_school_core_symbolic_threshold_passed")

    def test_all_prerequisite_proofs_replayed(self) -> None:
        audit = self.benchmark["prerequisite_audit"]
        self.assertTrue(audit["passed"])
        self.assertEqual(len(audit["checks"]), 7)
        self.assertTrue(all(item["passed"] for item in audit["checks"]))

    def test_targets_were_anonymous_and_unique(self) -> None:
        self.assertTrue(all(not item["name_visible_to_learner"] for item in self.benchmark["competencies"]))
        self.assertTrue(all(item["exact_candidate_count"] == 1 for item in self.benchmark["competencies"]))

    def test_report_replays_and_tampering_fails(self) -> None:
        self.assertTrue(verify_high_school_report(self.benchmark)["passed"])
        forged = json.loads(json.dumps(self.benchmark))
        forged["competencies"][0]["program"]["opaque_mode"] = 19
        self.assertFalse(verify_high_school_report(forged)["passed"])

    def test_success_room_replays_twenty_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "high-school.jsonl"
            room = HighSchoolCapabilityRoom(path)
            for record in self.benchmark["competencies"]:
                room.record(record)
            self.assertEqual(len(HighSchoolCapabilityRoom(path).records), 20)

    def test_prerequisite_failure_blocks_level(self) -> None:
        report = run_high_school_benchmark(prerequisite_audit={"passed": False, "checks": []})
        self.assertFalse(report["passed"])
        self.assertEqual(report["level_verdict"], "below_high_school_core_symbolic_threshold")


if __name__ == "__main__":
    unittest.main()
