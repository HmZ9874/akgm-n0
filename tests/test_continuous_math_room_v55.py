import tempfile
import unittest
from pathlib import Path

from akgm_n0.evaluator.continuous_math_room_v55 import ContinuousMathSuccessRoomV55
from akgm_n0.learner.continuous_math_research_v55 import (
    ContinuousMathResearchV55,
    ContinuousResearchStateV55,
)


class ContinuousMathSuccessRoomV55Tests(unittest.TestCase):
    def test_room_is_hash_chained_replayable_and_idempotent(self):
        result = ContinuousMathResearchV55().run(
            ContinuousResearchStateV55.initial(),
            target_new=5,
            maximum_rounds=12,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "success.jsonl"
            room = ContinuousMathSuccessRoomV55(path)
            added = room.sync(result.after.operators)
            self.assertEqual(len(added), len(result.after.operators))
            self.assertFalse(room.sync(result.after.operators))
            replayed = ContinuousMathSuccessRoomV55(path)
            self.assertEqual(len(replayed.records), len(result.after.operators))
            self.assertEqual(
                replayed.records[-1]["event_hash"], room.records[-1]["event_hash"]
            )


if __name__ == "__main__":
    unittest.main()
