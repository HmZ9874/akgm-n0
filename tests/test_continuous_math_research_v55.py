import json
import tempfile
import unittest
from pathlib import Path

from akgm_n0.evaluator.continuous_math_research_v55 import verify_v55_transition
from akgm_n0.learner.continuous_math_research_v55 import (
    ContinuousMathResearchV55,
    ContinuousResearchStateStoreV55,
    ContinuousResearchStateV55,
)


class ContinuousMathResearchV55Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.state_path = Path(cls.temporary.name) / "state.json"
        cls.store = ContinuousResearchStateStoreV55(cls.state_path)
        engine = ContinuousMathResearchV55()
        cls.initial = cls.store.load()
        cls.first = engine.run(cls.initial, target_new=5, maximum_rounds=12)
        cls.first_acceptance = verify_v55_transition(cls.first)
        cls.store.save(cls.first.after)
        cls.loaded = cls.store.load()
        cls.second = engine.run(cls.loaded, target_new=1, maximum_rounds=12)
        cls.second_acceptance = verify_v55_transition(cls.second)
        cls.store.save(cls.second.after)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_first_invocation_discovers_at_least_five_exact_semantics(self):
        self.assertTrue(self.first_acceptance["passed"])
        self.assertGreaterEqual(len(self.first.discoveries), 5)

    def test_second_invocation_resumes_and_discovers_something_additional(self):
        self.assertTrue(self.second_acceptance["passed"])
        self.assertEqual(self.loaded.state_digest, self.first.after.state_digest)
        self.assertGreaterEqual(len(self.second.discoveries), 1)
        self.assertGreater(len(self.second.after.operators), len(self.first.after.operators))

    def test_exact_behaviors_never_repeat_across_invocations(self):
        first = {item.exact_semantic.exact_signature for item in self.first.discoveries}
        second = {item.exact_semantic.exact_signature for item in self.second.discoveries}
        self.assertFalse(first & second)
        self.assertEqual(len(self.second.after.exact_signatures), len(set(self.second.after.exact_signatures)))

    def test_registry_and_rounds_are_append_only(self):
        self.assertEqual(
            self.second.after.operators[: len(self.first.after.operators)],
            self.first.after.operators,
        )
        self.assertEqual(self.second.before.next_round_index, self.first.after.next_round_index)
        self.assertEqual(self.second.after.run_count, 2)

    def test_state_digest_detects_corruption(self):
        payload = self.second.after.to_dict()
        payload["next_round_index"] += 1
        with self.assertRaises(ValueError):
            ContinuousResearchStateV55.from_dict(json.loads(json.dumps(payload)))

    def test_no_cloud_tokens_or_named_formula_targets(self):
        payload = self.second.to_dict()
        self.assertEqual(payload["api_tokens"], 0)
        self.assertEqual(payload["cloud_model_calls"], 0)
        self.assertTrue(
            all(
                discovery.exact_semantic.to_dict()["human_math_name"] is None
                for discovery in self.first.discoveries + self.second.discoveries
            )
        )


if __name__ == "__main__":
    unittest.main()
