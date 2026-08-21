"""Independent V36 audit for a gated scientific-discovery workflow."""
from __future__ import annotations

import hashlib
import inspect
import itertools
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from akgm_n0.learner.scientific_discovery_machine_v36 import (
    ActiveScientificResearcherV36,
    PointV36,
    SparseProgramV36,
)


@dataclass(slots=True)
class BlindOracleBrokerV36:
    world_id: str
    _coefficients: tuple[int, int, int, int, int, int]
    event_ledger: list[dict[str, Any]]

    def query(self, point: PointV36) -> int:
        output = SparseProgramV36(self._coefficients).execute(point)
        self.event_ledger.append({"index": len(self.event_ledger), "event": "oracle_reveal", "world_id": self.world_id, "point": list(point)})
        return output


class SealedFutureBrokerV36:
    def __init__(self, world_id: str, coefficients, allowed_points, event_ledger):
        self.world_id = world_id
        self.__coefficients = tuple(coefficients)
        self.__allowed = frozenset(allowed_points)
        self.__commitment = None
        self.event_ledger = event_ledger

    def commit(self, commitment: str):
        if self.__commitment is not None:
            raise RuntimeError("sealed prediction already committed")
        self.__commitment = commitment
        self.event_ledger.append({"index": len(self.event_ledger), "event": "prediction_commitment", "world_id": self.world_id, "commitment": commitment})

    def query(self, point: PointV36) -> int:
        if self.__commitment is None:
            raise RuntimeError("future result cannot be revealed before preregistration")
        if point not in self.__allowed:
            raise ValueError("point is outside the sealed future set")
        output = SparseProgramV36(self.__coefficients).execute(point)
        self.event_ledger.append({"index": len(self.event_ledger), "event": "sealed_reveal", "world_id": self.world_id, "point": list(point)})
        return output


class LocalKnowledgeCatalogV36:
    """A deliberately small local registry; absence is never global novelty."""

    ENTRIES = {
        "KNOWN-ZERO": (0, 0, 0, 0, 0, 0),
        "KNOWN-ONE": (1, 0, 0, 0, 0, 0),
        "KNOWN-LEFT": (0, 1, 0, 0, 0, 0),
        "KNOWN-RIGHT": (0, 0, 1, 0, 0, 0),
        "KNOWN-ADD": (0, 1, 1, 0, 0, 0),
        "KNOWN-SUB": (0, 1, -1, 0, 0, 0),
        "KNOWN-PRODUCT": (0, 0, 0, 1, 0, 0),
        "KNOWN-NORM2": (0, 0, 0, 0, 1, 1),
    }

    def compare(self, program: SparseProgramV36):
        matches = [knowledge_id for knowledge_id, coefficients in self.ENTRIES.items() if coefficients == program.coefficients]
        return {
            "catalog_version": "local-knowledge-catalog-v36.0",
            "entry_count": len(self.ENTRIES),
            "exact_matches": matches,
            "locally_unmatched": not matches,
            "global_literature_checked": False,
            "human_novelty_established": False,
        }


def _domain(radius: int):
    return tuple(itertools.product(range(-radius, radius + 1), repeat=2))


def _run_world(world_id: str, coefficients, *, sealed_points):
    ledger: list[dict[str, Any]] = []
    broker = BlindOracleBrokerV36(world_id, tuple(coefficients), ledger)
    researcher = ActiveScientificResearcherV36()
    seeds = ((0, 0),)
    pool = _domain(3)
    discovery = researcher.discover(broker.query, seed_points=seeds, experiment_pool=pool)
    sealed = SealedFutureBrokerV36(world_id + "-SEALED", coefficients, sealed_points, ledger)
    preregistration = researcher.preregister_and_reveal(
        discovery.selected_program,
        sealed_points,
        sealed.query,
        sealed.commit,
    )
    commit_index = next(item["index"] for item in ledger if item["event"] == "prediction_commitment")
    reveal_indices = [item["index"] for item in ledger if item["event"] == "sealed_reveal"]
    return {
        "world_id": world_id,
        "discovery": discovery,
        "preregistration": preregistration,
        "event_ledger": ledger,
        "commitment_precedes_every_future_reveal": bool(reveal_indices) and all(commit_index < index for index in reveal_indices),
        "oracle_query_count": sum(item["event"] == "oracle_reveal" for item in ledger),
    }


def _independent_replication(program: SparseProgramV36, coefficients):
    points = ((-5, -2), (-4, 3), (2, -5), (4, 4), (6, -1), (-3, 6))
    ledger: list[dict[str, Any]] = []
    broker = BlindOracleBrokerV36("FRONTIER-INDEPENDENT-REPLICATION", tuple(coefficients), ledger)
    cases = [
        {"anonymous_inputs": list(point), "predicted": program.execute(point), "observed": broker.query(point)}
        for point in points
    ]
    for case in cases:
        case["passed"] = case["predicted"] == case["observed"]
    return {
        "replicator_id": "independent-broker-v36",
        "points_disjoint_from_training_domain": all(max(abs(x) for x in point) > 3 for point in points),
        "passed": all(case["passed"] for case in cases),
        "cases": cases,
    }


def _mutation_audit(program: SparseProgramV36, coefficients):
    truth = SparseProgramV36(tuple(coefficients))
    challenge = _domain(4)
    results = []
    for index in range(6):
        for delta in (-1, 1):
            changed = list(program.coefficients)
            changed[index] += delta
            mutation = SparseProgramV36(tuple(changed))
            point = next((point for point in challenge if mutation.execute(point) != truth.execute(point)), None)
            results.append({
                "mutation": f"coefficient_{index}_{delta:+d}",
                "program": mutation.to_dict(),
                "rejected": point is not None,
                "counterexample": None if point is None else {
                    "anonymous_inputs": list(point),
                    "mutated": mutation.execute(point),
                    "observed": truth.execute(point),
                },
            })
    return results


def _blindness_audit():
    source = inspect.getsource(ActiveScientificResearcherV36)
    forbidden = ("FRONTIER", "KNOWN-ADD", "human_novelty", "literature")
    return {
        "passed": all(token not in source for token in forbidden),
        "forbidden_target_tokens": list(forbidden),
        "oracle_implementation_available_to_researcher": False,
        "isolation_strength": "logical API isolation, not an operating-system security boundary",
    }


def run_v36_acceptance():
    calibration_coefficients = (0, 1, 1, 0, 0, 0)
    frontier_coefficients = (2, 1, -1, 1, 0, 0)
    calibration = _run_world("CALIBRATION-WORLD", calibration_coefficients, sealed_points=((4, -3), (-4, 2), (3, 4)))
    frontier = _run_world("FRONTIER-WORLD", frontier_coefficients, sealed_points=((4, -3), (-4, 2), (3, 4), (-2, -4)))
    catalog = LocalKnowledgeCatalogV36()
    calibration_novelty = catalog.compare(calibration["discovery"].selected_program)
    frontier_novelty = catalog.compare(frontier["discovery"].selected_program)
    replication = _independent_replication(frontier["discovery"].selected_program, frontier_coefficients)
    mutations = _mutation_audit(frontier["discovery"].selected_program, frontier_coefficients)
    blindness = _blindness_audit()
    gates = {
        "blind_data_interface": blindness["passed"],
        "active_model_discrimination": bool(frontier["discovery"].experiments),
        "unique_executable_hypothesis": frontier["discovery"].final_candidate_count == 1,
        "prospective_prediction": frontier["preregistration"].passed,
        "commit_before_reveal": frontier["commitment_precedes_every_future_reveal"],
        "independent_replication": replication["passed"],
        "counterexample_audit": all(item["rejected"] for item in mutations),
        "local_catalog_unmatched": frontier_novelty["locally_unmatched"],
        "global_literature_novelty": False,
        "real_world_observation": False,
        "external_lab_replication": False,
    }
    human_unknown_allowed = all(gates.values())
    obligations = (
        {"obligation_id": "anonymous_blind_oracle_surface", "passed": blindness["passed"]},
        {"obligation_id": "at_least_five_thousand_competing_models", "passed": frontier["discovery"].initial_candidate_count >= 5000},
        {"obligation_id": "experiments_selected_by_disagreement", "passed": len(frontier["discovery"].experiments) >= 2 and all(item.predicted_output_classes > 1 for item in frontier["discovery"].experiments)},
        {"obligation_id": "frontier_model_unique", "passed": frontier["discovery"].selected_program.coefficients == frontier_coefficients},
        {"obligation_id": "prediction_preregistered_before_reveal", "passed": frontier["commitment_precedes_every_future_reveal"]},
        {"obligation_id": "sealed_future_predictions_pass", "passed": frontier["preregistration"].passed},
        {"obligation_id": "independent_replication_passes", "passed": replication["passed"]},
        {"obligation_id": "nearby_models_receive_counterexamples", "passed": all(item["rejected"] for item in mutations)},
        {"obligation_id": "known_calibration_is_not_called_novel", "passed": not calibration_novelty["locally_unmatched"] and calibration_novelty["exact_matches"] == ["KNOWN-ADD"]},
        {"obligation_id": "frontier_is_only_local_novel_candidate", "passed": frontier_novelty["locally_unmatched"] and not frontier_novelty["human_novelty_established"]},
        {"obligation_id": "synthetic_world_is_not_called_real_science", "passed": not gates["real_world_observation"]},
        {"obligation_id": "human_unknown_claim_remains_blocked", "passed": not human_unknown_allowed},
    )
    return {
        "benchmark_version": "scientific-discovery-machine-v36.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_scientific_discovery_workflow_on_blind_synthetic_oracles_not_a_human_novel_discovery",
        "calibration_world": {
            "discovery": calibration["discovery"].to_dict(),
            "preregistration": calibration["preregistration"].to_dict(),
            "novelty": calibration_novelty,
        },
        "frontier_world": {
            "discovery": frontier["discovery"].to_dict(),
            "preregistration": frontier["preregistration"].to_dict(),
            "novelty": frontier_novelty,
            "oracle_query_count": frontier["oracle_query_count"],
        },
        "independent_replication": replication,
        "mutation_audits": mutations,
        "blindness_audit": blindness,
        "discovery_gates": gates,
        "claim_state": {
            "workflow_capability_verified": all(value for key, value in gates.items() if key not in ("global_literature_novelty", "real_world_observation", "external_lab_replication")),
            "local_novel_candidate": frontier_novelty["locally_unmatched"],
            "human_unknown_claim_allowed": human_unknown_allowed,
            "current_label": "LOCAL_NOVEL_CANDIDATE_ON_SYNTHETIC_ORACLE",
        },
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "calibration_program": "q0+q1",
            "frontier_program": "2+q0-q1+q0*q1",
        },
        "limitations": [
            "The frontier result is generated by a synthetic hidden oracle and is not a discovery about nature.",
            "The six-term sparse polynomial grammar is a supplied inductive bias, not a self-created universal language.",
            "The local knowledge catalog has only eight entries and cannot establish novelty relative to human literature.",
            "Oracle separation is enforced by the learner API and audit, not by an operating-system process boundary.",
            "No noisy measurements, causal interventions, units, uncertainty model, literature review, or external laboratory replication are present yet.",
        ],
    }


def replay_v36_report(report: Mapping[str, Any]):
    replay = run_v36_acceptance()
    return {
        "passed": replay["passed"] and replay["frontier_world"]["discovery"] == report["frontier_world"]["discovery"],
    }
