import json
import unittest
from pathlib import Path

from akgm_n0.learner.live_experiment_v39 import batch_commitment_v39

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/data/external_physical_science_v40_latest.json"


class ExternalPhysicalScienceV40Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.acceptance = cls.report["acceptance"]

    def test_external_physical_acceptance(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(self.acceptance["discovery_gates"]["external_physical_apparatus"])

    def test_fresh_unique_receipts(self):
        audit = self.acceptance["physical_receipt_audit"]
        self.assertEqual(audit["receipt_count"], 8)
        self.assertEqual(audit["unique_raw_digest_count"], 8)
        self.assertTrue(audit["all_device_transactions_have_duration"])

    def test_raw_images_not_retained(self):
        audit = self.acceptance["physical_receipt_audit"]
        self.assertTrue(audit["all_raw_images_deleted_after_statistics"])
        self.assertTrue(all(not item["raw_image_retained"] for item in audit["receipts"]))

    def test_domain_blind_observations(self):
        self.assertTrue(self.acceptance["discovery_gates"]["domain_blind_learner"])
        self.assertTrue(all(item["human_quantity_names"] is None for item in self.acceptance["observations"]))

    def test_adaptive_interventions(self):
        audit = self.acceptance["adaptive_experiment_audit"]
        self.assertEqual(audit["round_count"], 3)
        self.assertTrue(audit["later_rounds_gap_driven"])

    def test_batch_commitments_recompute(self):
        audit = self.acceptance["randomization_and_commitment_audit"]
        for batch in audit["batches"]:
            expected = batch_commitment_v39(batch["batch_id"], batch["randomized_order"], batch["seed_commitment"])
            self.assertEqual(expected, batch["batch_commitment"])
            self.assertTrue(batch["commit_precedes_measurement"])

    def test_created_semantic(self):
        semantic = self.acceptance["created_semantic"]
        self.assertTrue(semantic["semantic_id"].startswith("PHYS-SEM-"))
        self.assertFalse(semantic["domain_formula_supplied"])
        self.assertEqual(semantic["knot_count"], 5)

    def test_prospective_holdout(self):
        holdout = self.acceptance["prospective_holdout_audit"]
        self.assertTrue(holdout["commitment_precedes_measurement"])
        self.assertTrue(holdout["passed"])

    def test_new_process_replication(self):
        replication = self.acceptance["new_process_replication_audit"]
        self.assertTrue(replication["new_broker_process"])
        self.assertTrue(replication["passed"])

    def test_claim_boundary(self):
        claim = self.acceptance["claim_state"]
        self.assertTrue(claim["external_physical_experiment_verified"])
        self.assertFalse(claim["human_unknown_claim_allowed"])
        self.assertFalse(claim["new_natural_law_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
