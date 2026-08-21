"""Run a small evaluator-side autonomous program-search smoke test."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenSequenceEnvironment, SequenceWorldSpec
from akgm_n0.learner import NextValueProgramSearch


def main() -> int:
    environment = HiddenSequenceEnvironment(
        SequenceWorldSpec("affine", (7.0, 3.0), 12),
        seed=104729,
        secret=b"local-search-smoke-only",
    )
    observation = environment.observe(10)
    report = NextValueProgramSearch(maximum_nodes=3, top_k=5).search(observation)
    payload = {
        "claim": "autonomous_search_smoke_test_only",
        "learner_observation": observation.to_public_dict(),
        "search_report": report.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

