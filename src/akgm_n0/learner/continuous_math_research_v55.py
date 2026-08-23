"""Persistent target-free discovery of exact natural-counter state semantics."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from .autonomous_research_loop_v17 import (
    AutonomousWorldFactoryV17,
    ExperimentPlanV17,
    KnowledgeGapAnalyzerV17,
    KnowledgeGapV17,
)
from .cold_start_semantics_v16 import (
    DATA_OPS,
    ColdStartSemanticResearcherV16,
    OperatorDefinitionV16,
    RuntimeInstruction,
)


STATE_VERSION_V55 = "continuous-math-research-state-v55.0"
ZERO_DIGEST_V55 = "0" * 64


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def instruction_from_dict_v55(payload: Mapping[str, Any]) -> RuntimeInstruction:
    return RuntimeInstruction(
        op=str(payload["op"]),
        operands=tuple(int(item) for item in payload.get("operands", ())),
        target=None if payload.get("target") is None else int(payload["target"]),
    )


def operator_from_dict_v55(payload: Mapping[str, Any]) -> OperatorDefinitionV16:
    return OperatorDefinitionV16(
        operator_id=str(payload["operator_id"]),
        generation=int(payload["generation"]),
        arity=int(payload["arity"]),
        body=tuple(instruction_from_dict_v55(item) for item in payload["body"]),
        primitive_body=tuple(
            instruction_from_dict_v55(item) for item in payload["primitive_body"]
        ),
        parent_operators=tuple(str(item) for item in payload["parent_operators"]),
        train_family_support=int(payload["train_family_support"]),
        train_occurrences=int(payload["train_occurrences"]),
        primitive_span=int(payload["primitive_span"]),
        token_gain_per_use=int(payload["token_gain_per_use"]),
        net_training_reward=int(payload["net_training_reward"]),
        behavior_signature=str(payload["behavior_signature"]),
        certificate_digest=str(payload["certificate_digest"]),
    )


@dataclass(frozen=True, slots=True)
class SymbolicCounterV55:
    minimum_input: int | None
    output_kind: str
    output_value: int

    @classmethod
    def identity(cls) -> "SymbolicCounterV55":
        return cls(0, "input_offset", 0)

    def apply(self, op: str) -> "SymbolicCounterV55":
        if self.minimum_input is None:
            return self
        if op == "u_zero":
            return SymbolicCounterV55(self.minimum_input, "constant", 0)
        if op == "u_unit":
            return SymbolicCounterV55(self.minimum_input, "constant", 1)
        if op == "u_inc":
            return SymbolicCounterV55(
                self.minimum_input, self.output_kind, self.output_value + 1
            )
        if op != "u_dec":
            raise ValueError(f"V55 exact interpreter does not admit {op}")
        if self.output_kind == "constant":
            if self.output_value == 0:
                return SymbolicCounterV55(None, "always_error", 0)
            return SymbolicCounterV55(
                self.minimum_input, "constant", self.output_value - 1
            )
        required = max(self.minimum_input, 1 - self.output_value)
        return SymbolicCounterV55(required, "input_offset", self.output_value - 1)

    def to_dict(self) -> dict[str, Any]:
        if self.minimum_input is None:
            return {"success_domain": "empty", "output": "error"}
        output: dict[str, Any]
        if self.output_kind == "constant":
            output = {"kind": "constant", "value": self.output_value}
        else:
            output = {"kind": "input_offset", "offset": self.output_value}
        return {"minimum_input": self.minimum_input, "output": output}


@dataclass(frozen=True, slots=True)
class ExactCounterSemanticV55:
    arity: int
    alias_partitions: tuple[dict[str, Any], ...]
    exact_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "arity": self.arity,
            "all_natural_inputs": True,
            "all_role_alias_partitions": True,
            "alias_partitions": list(self.alias_partitions),
            "exact_signature": self.exact_signature,
            "finite_sample_hash": False,
            "human_math_name": None,
        }


def exact_semantic_from_body_v55(
    arity: int, primitive_body: Sequence[RuntimeInstruction]
) -> ExactCounterSemanticV55:
    if arity not in (1, 2):
        raise ValueError("V55 exact semantics currently supports arity one or two")
    if any(item.op not in DATA_OPS or len(item.operands) != 1 for item in primitive_body):
        raise ValueError("V55 exact semantics requires unary primitive counter instructions")
    mappings = ((0,),) if arity == 1 else ((0, 1), (0, 0))
    partition_reports = []
    for mapping in mappings:
        group_count = max(mapping) + 1
        counters = [SymbolicCounterV55.identity() for _ in range(group_count)]
        always_error = False
        for instruction in primitive_body:
            group = mapping[instruction.operands[0]]
            counters[group] = counters[group].apply(instruction.op)
            if counters[group].minimum_input is None:
                always_error = True
                break
        partition_reports.append({
            "role_to_physical_group": list(mapping),
            "always_error": always_error,
            "physical_groups": [] if always_error else [item.to_dict() for item in counters],
        })
    semantic_payload = {"arity": arity, "alias_partitions": partition_reports}
    signature = hashlib.sha256(_canonical_json(semantic_payload).encode()).hexdigest()
    return ExactCounterSemanticV55(arity, tuple(partition_reports), signature)


def exact_semantic_for_operator_v55(
    definition: OperatorDefinitionV16,
) -> ExactCounterSemanticV55:
    return exact_semantic_from_body_v55(definition.arity, definition.primitive_body)


def base_exact_signatures_v55() -> tuple[str, ...]:
    return tuple(sorted({
        exact_semantic_from_body_v55(
            1, (RuntimeInstruction(op, (0,)),)
        ).exact_signature
        for op in DATA_OPS
    }))


def exact_semantic_text_v55(semantic: ExactCounterSemanticV55) -> str:
    parts = []
    for partition in semantic.alias_partitions:
        mapping = ",".join(str(item) for item in partition["role_to_physical_group"])
        if partition["always_error"]:
            parts.append(f"roles[{mapping}]: undefined")
            continue
        outputs = []
        for index, group in enumerate(partition["physical_groups"]):
            output = group["output"]
            domain = group["minimum_input"]
            if output["kind"] == "constant":
                expression = str(output["value"])
            else:
                offset = output["offset"]
                expression = f"n{index}{offset:+d}" if offset else f"n{index}"
            outputs.append(f"n{index}>={domain} => {expression}")
        parts.append(f"roles[{mapping}]: " + "; ".join(outputs))
    return " | ".join(parts)


@dataclass(frozen=True, slots=True)
class CurriculumLevelV55:
    level: int
    workloads_per_family: int
    instruction_count: int
    maximum_primitive_span: int
    maximum_generation: int


CURRICULUM_V55 = (
    CurriculumLevelV55(0, 48, 36, 3, 3),
    CurriculumLevelV55(1, 56, 42, 4, 4),
    CurriculumLevelV55(2, 64, 48, 4, 5),
)


@dataclass(frozen=True, slots=True)
class ContinuousResearchStateV55:
    campaign_seed: int
    run_count: int
    next_round_index: int
    curriculum_level: int
    sterile_rounds_at_level: int
    operators: tuple[OperatorDefinitionV16, ...]
    exact_signatures: tuple[str, ...]
    previous_state_digest: str
    state_digest: str

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": STATE_VERSION_V55,
            "campaign_seed": self.campaign_seed,
            "run_count": self.run_count,
            "next_round_index": self.next_round_index,
            "curriculum_level": self.curriculum_level,
            "sterile_rounds_at_level": self.sterile_rounds_at_level,
            "operators": [item.to_dict() for item in self.operators],
            "exact_signatures": list(self.exact_signatures),
            "previous_state_digest": self.previous_state_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "state_digest": self.state_digest}

    @classmethod
    def create(
        cls,
        *,
        campaign_seed: int,
        run_count: int,
        next_round_index: int,
        curriculum_level: int,
        sterile_rounds_at_level: int,
        operators: Sequence[OperatorDefinitionV16],
        exact_signatures: Sequence[str],
        previous_state_digest: str,
    ) -> "ContinuousResearchStateV55":
        draft = cls(
            campaign_seed,
            run_count,
            next_round_index,
            curriculum_level,
            sterile_rounds_at_level,
            tuple(operators),
            tuple(sorted(set(exact_signatures))),
            previous_state_digest,
            "",
        )
        digest = hashlib.sha256(_canonical_json(draft.payload()).encode()).hexdigest()
        return replace(draft, state_digest=digest)

    @classmethod
    def initial(cls, campaign_seed: int = 55_001) -> "ContinuousResearchStateV55":
        return cls.create(
            campaign_seed=campaign_seed,
            run_count=0,
            next_round_index=0,
            curriculum_level=0,
            sterile_rounds_at_level=0,
            operators=(),
            exact_signatures=base_exact_signatures_v55(),
            previous_state_digest=ZERO_DIGEST_V55,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ContinuousResearchStateV55":
        if payload.get("schema_version") != STATE_VERSION_V55:
            raise ValueError("V55 state schema differs")
        state = cls(
            campaign_seed=int(payload["campaign_seed"]),
            run_count=int(payload["run_count"]),
            next_round_index=int(payload["next_round_index"]),
            curriculum_level=int(payload["curriculum_level"]),
            sterile_rounds_at_level=int(payload["sterile_rounds_at_level"]),
            operators=tuple(operator_from_dict_v55(item) for item in payload["operators"]),
            exact_signatures=tuple(str(item) for item in payload["exact_signatures"]),
            previous_state_digest=str(payload["previous_state_digest"]),
            state_digest=str(payload["state_digest"]),
        )
        expected = hashlib.sha256(_canonical_json(state.payload()).encode()).hexdigest()
        if state.state_digest != expected:
            raise ValueError("V55 state digest mismatch")
        return state


class ContinuousResearchStateStoreV55:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def load(self, *, campaign_seed: int = 55_001) -> ContinuousResearchStateV55:
        if not self.path.exists():
            return ContinuousResearchStateV55.initial(campaign_seed)
        return ContinuousResearchStateV55.from_dict(
            json.loads(self.path.read_text(encoding="utf-8"))
        )

    def save(self, state: ContinuousResearchStateV55) -> None:
        if self.path.exists():
            current = self.load(campaign_seed=state.campaign_seed)
            if state.previous_state_digest != current.state_digest:
                raise ValueError("V55 state transition does not extend the stored state")
        elif state.previous_state_digest != ContinuousResearchStateV55.initial(
            state.campaign_seed
        ).state_digest:
            raise ValueError("V55 first persisted transition has an unknown parent")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.path)


@dataclass(frozen=True, slots=True)
class DiscoveryV55:
    definition: OperatorDefinitionV16
    exact_semantic: ExactCounterSemanticV55
    posthoc_formula: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator": self.definition.to_dict(),
            "exact_semantic": self.exact_semantic.to_dict(),
            "posthoc_formula": self.posthoc_formula,
            "posthoc_translation_only": True,
        }


@dataclass(frozen=True, slots=True)
class ContinuousRoundV55:
    round_index: int
    curriculum_level: int
    gap: KnowledgeGapV17
    experiment: ExperimentPlanV17
    world_digest: str
    operator_count_before: int
    proposals: int
    discoveries: tuple[DiscoveryV55, ...]
    rejected: tuple[dict[str, Any], ...]
    cache_stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "curriculum_level": self.curriculum_level,
            "gap": self.gap.to_dict(),
            "experiment": self.experiment.to_dict(),
            "world_digest": self.world_digest,
            "operator_count_before": self.operator_count_before,
            "proposal_count": self.proposals,
            "new_verified_exact_semantic_count": len(self.discoveries),
            "discoveries": [item.to_dict() for item in self.discoveries],
            "rejected": list(self.rejected),
            "cache_stats": self.cache_stats,
        }


@dataclass(frozen=True, slots=True)
class ContinuousResearchResultV55:
    before: ContinuousResearchStateV55
    after: ContinuousResearchStateV55
    rounds: tuple[ContinuousRoundV55, ...]
    discoveries: tuple[DiscoveryV55, ...]
    stop_reason: str
    target_new: int
    maximum_rounds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_state": self.before.to_dict(),
            "after_state": self.after.to_dict(),
            "rounds": [item.to_dict() for item in self.rounds],
            "discoveries": [item.to_dict() for item in self.discoveries],
            "new_verified_exact_semantic_count": len(self.discoveries),
            "stop_reason": self.stop_reason,
            "target_new": self.target_new,
            "maximum_rounds": self.maximum_rounds,
            "cloud_model_calls": 0,
            "api_tokens": 0,
        }


class ContinuousMathResearchV55:
    def __init__(self, *, sterile_patience: int = 3) -> None:
        if sterile_patience != 3:
            raise ValueError("V55 frozen sterile patience differs")
        self.sterile_patience = sterile_patience
        self.gaps = KnowledgeGapAnalyzerV17()
        self.worlds = AutonomousWorldFactoryV17()

    @staticmethod
    def _researcher(
        definitions: Sequence[OperatorDefinitionV16],
    ) -> ColdStartSemanticResearcherV16:
        researcher = ColdStartSemanticResearcherV16(enable_semantic_cache=True)
        for definition in definitions:
            researcher.vm.install_operator(definition)
        return researcher

    def run(
        self,
        state: ContinuousResearchStateV55,
        *,
        target_new: int = 5,
        maximum_rounds: int = 12,
    ) -> ContinuousResearchResultV55:
        if target_new < 1:
            raise ValueError("V55 target-new budget is empty")
        if maximum_rounds < 1 or maximum_rounds > 12:
            raise ValueError("V55 maximum rounds must be from one through twelve")
        researcher = self._researcher(state.operators)
        definitions = list(state.operators)
        known_signatures = set(state.exact_signatures)
        global_discoveries: list[DiscoveryV55] = []
        rounds: list[ContinuousRoundV55] = []
        level_index = state.curriculum_level
        sterile = state.sterile_rounds_at_level
        next_round = state.next_round_index
        stop_reason = "maximum_round_boundary"

        for _ in range(maximum_rounds):
            level = CURRICULUM_V55[level_index]
            before_count = len(definitions)
            gap = self.gaps.inspect(tuple(definitions))
            experiment = self.worlds.plan(
                gap, round_index=next_round, seed=state.campaign_seed
            )
            experiment = replace(
                experiment,
                workloads_per_family=level.workloads_per_family,
                instruction_count=level.instruction_count,
            )
            workloads = self.worlds.generate(experiment, seed=state.campaign_seed)
            world_digest = hashlib.sha256(
                _canonical_json([item.to_dict() for item in workloads]).encode()
            ).hexdigest()
            discovery = researcher.extend(
                workloads,
                maximum_new_operators=8,
                maximum_primitive_span=level.maximum_primitive_span,
                maximum_arity=2,
                maximum_generation=level.maximum_generation,
            )
            accepted: list[DiscoveryV55] = []
            rejected: list[dict[str, Any]] = []
            available_ids = {item.operator_id for item in definitions}
            for definition in discovery.operators:
                semantic = exact_semantic_for_operator_v55(definition)
                missing_parent = next(
                    (item for item in definition.parent_operators if item not in available_ids),
                    None,
                )
                if missing_parent is not None:
                    rejected.append({
                        "candidate_id": definition.operator_id,
                        "reason": "depends_on_unpromoted_candidate",
                        "missing_parent": missing_parent,
                    })
                    continue
                if semantic.exact_signature in known_signatures:
                    rejected.append({
                        "candidate_id": definition.operator_id,
                        "reason": "exact_behavior_already_in_success_library",
                        "exact_signature": semantic.exact_signature,
                    })
                    continue
                item = DiscoveryV55(
                    definition,
                    semantic,
                    exact_semantic_text_v55(semantic),
                )
                accepted.append(item)
                definitions.append(definition)
                available_ids.add(definition.operator_id)
                known_signatures.add(semantic.exact_signature)

            if len(accepted) != len(discovery.operators):
                researcher = self._researcher(tuple(definitions))
            global_discoveries.extend(accepted)
            sterile = 0 if accepted else sterile + 1
            rounds.append(ContinuousRoundV55(
                round_index=next_round,
                curriculum_level=level_index,
                gap=gap,
                experiment=experiment,
                world_digest=world_digest,
                operator_count_before=before_count,
                proposals=len(discovery.operators),
                discoveries=tuple(accepted),
                rejected=tuple(rejected),
                cache_stats=researcher.semantic_cache_stats,
            ))
            next_round += 1

            if len(global_discoveries) >= target_new:
                stop_reason = "target_new_verified_semantics_reached"
                break
            if sterile >= self.sterile_patience:
                if level_index < len(CURRICULUM_V55) - 1:
                    level_index += 1
                    sterile = 0
                else:
                    stop_reason = "final_curriculum_semantic_saturation"
                    break

        after = ContinuousResearchStateV55.create(
            campaign_seed=state.campaign_seed,
            run_count=state.run_count + 1,
            next_round_index=next_round,
            curriculum_level=level_index,
            sterile_rounds_at_level=sterile,
            operators=definitions,
            exact_signatures=known_signatures,
            previous_state_digest=state.state_digest,
        )
        return ContinuousResearchResultV55(
            before=state,
            after=after,
            rounds=tuple(rounds),
            discoveries=tuple(global_discoveries),
            stop_reason=stop_reason,
            target_new=target_new,
            maximum_rounds=maximum_rounds,
        )
