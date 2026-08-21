from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator.environment import HiddenSequenceEnvironment, SequenceWorldSpec
from akgm_n0.learner.observation import PUBLIC_OBSERVATION_FIELDS, NumericObservation
from akgm_n0.contracts import load_learner_contract


class EnvironmentTests(unittest.TestCase):
    def test_public_observation_fields_match_contract_configuration(self) -> None:
        contract = load_learner_contract()
        self.assertEqual(
            set(contract["input_interface"]["fields"]),
            PUBLIC_OBSERVATION_FIELDS,
        )

    def test_public_observation_matches_frozen_contract_exactly(self) -> None:
        environment = HiddenSequenceEnvironment(
            SequenceWorldSpec("polynomial2", (1.0, 0.0, 1.0), 8),
            seed=42,
            secret=b"evaluator-test-secret",
        )
        observation = environment.observe(5)
        public = observation.to_public_dict()
        self.assertEqual(set(public), PUBLIC_OBSERVATION_FIELDS)
        self.assertEqual(public["sequence_values"], [1.0, 2.0, 5.0, 10.0, 17.0])
        serialized = repr(public).casefold()
        self.assertNotIn("polynomial", serialized)
        self.assertNotIn("coefficient", serialized)
        self.assertNotIn("evaluation", serialized)

    def test_private_parameters_are_not_attributes_of_observation(self) -> None:
        environment = HiddenSequenceEnvironment(
            SequenceWorldSpec("affine", (10.0, 3.0), 6),
            seed=7,
            secret=b"evaluator-test-secret",
        )
        observation = environment.observe(4)
        self.assertIsInstance(observation, NumericObservation)
        self.assertFalse(hasattr(observation, "kind"))
        self.assertFalse(hasattr(observation, "parameters"))
        self.assertFalse(hasattr(observation, "seed"))

    def test_opaque_identifiers_depend_on_evaluator_secret(self) -> None:
        spec = SequenceWorldSpec("affine", (1.0, 2.0), 5)
        first = HiddenSequenceEnvironment(spec, seed=3, secret=b"secret-a").observe(3)
        second = HiddenSequenceEnvironment(spec, seed=3, secret=b"secret-b").observe(3)
        self.assertEqual(first.sequence_values, second.sequence_values)
        self.assertNotEqual(first.opaque_session_id, second.opaque_session_id)
        self.assertNotEqual(first.action_receipt, second.action_receipt)

    def test_observation_can_be_extended_without_revealing_rule(self) -> None:
        environment = HiddenSequenceEnvironment(
            SequenceWorldSpec("alternating_increment", (0.0, 1.0, 3.0), 7),
            seed=11,
            secret=b"evaluator-test-secret",
        )
        initial = environment.observe(3)
        extended = environment.observe(6)
        self.assertEqual(initial.sequence_values, extended.sequence_values[:3])
        self.assertNotEqual(initial.action_receipt, extended.action_receipt)


if __name__ == "__main__":
    unittest.main()
