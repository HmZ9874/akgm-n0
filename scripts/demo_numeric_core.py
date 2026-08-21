"""Evaluator-side smoke demo for the anonymous numeric execution path.

The candidate in this demo is manually constructed. This script proves that the
interface and executor work; it is not evidence of autonomous discovery.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenSequenceEnvironment, SequenceWorldSpec
from akgm_n0.learner import (
    ExecutionContext,
    ProgramExecutor,
    read_offset,
    subtract,
)


def main() -> int:
    environment = HiddenSequenceEnvironment(
        SequenceWorldSpec("polynomial2", (1.0, 0.0, 1.0), 8),
        seed=20260817,
        secret=b"local-smoke-demo-only",
    )
    observation = environment.observe(5)

    candidate = subtract(read_offset(1), read_offset(0))
    context = ExecutionContext.create(
        observation.sequence_values,
        index=0,
        validity_mask=observation.validity_mask,
    )
    outputs = ProgramExecutor().evaluate_over_valid_indices(candidate, context)

    report = {
        "claim": "manual_smoke_test_only",
        "learner_observation": observation.to_public_dict(),
        "candidate_program": candidate.to_dict(),
        "candidate_outputs": list(outputs),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

