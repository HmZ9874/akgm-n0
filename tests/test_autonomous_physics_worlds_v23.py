import unittest

from akgm_n0.evaluator.autonomous_physics_worlds_v23 import replay_v23_report, run_v23_acceptance


class AutonomousPhysicsWorldsV23Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v23_acceptance()

    def test_worlds_are_generated_without_human_definitions(self):
        worlds = self.acceptance["construction"]["worlds"]
        self.assertEqual(len(worlds), 24)
        self.assertTrue(all(item["definition"]["human_entity_names"] is None for item in worlds))
        self.assertTrue(all(item["definition"]["human_physics_law"] is None for item in worlds))

    def test_world_population_is_diverse(self):
        construction = self.acceptance["construction"]
        self.assertEqual(construction["graph_family_count"], 3)
        self.assertEqual(construction["entity_count_range"], [2, 5])
        self.assertGreaterEqual(construction["total_simulated_steps"], 500)
        self.assertGreaterEqual(construction["total_interactions"], 400)

    def test_all_worlds_pass_every_quality_gate(self):
        construction = self.acceptance["construction"]
        self.assertEqual(construction["worlds_generated"], 24)
        self.assertEqual(construction["worlds_accepted"], 24)
        self.assertTrue(all(item["quality"]["accepted"] for item in construction["worlds"]))

    def test_every_trace_conserves_additive_total(self):
        worlds = self.acceptance["construction"]["worlds"]
        self.assertTrue(all(step["conserved"] for world in worlds for step in world["execution"]["trace"]))
        self.assertTrue(self.acceptance["proofs"]["world_family"]["passed"])

    def test_different_seed_sealed_worlds_transfer(self):
        sealed = self.acceptance["sealed_worlds"]
        self.assertEqual(sealed["world_count"], 6)
        self.assertEqual(sealed["accepted_count"], 6)
        self.assertTrue(sealed["proof"]["passed"])

    def test_world_mutations_are_rejected(self):
        mutations = self.acceptance["mutation_audits"]
        self.assertEqual(len(mutations), 4)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in mutations))

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        report = {"observed_values": self.acceptance["observed_values"], "construction": self.acceptance["construction"]}
        self.assertTrue(replay_v23_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
