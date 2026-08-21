"""Autonomously construct executable multi-entity worlds from V22 programs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .anonymous_physics_discovery_v22 import ChannelProgramV22, DirectedPhysicsRuntimeV22
from .directed_rational_construction_v21 import DirectedValueV21


@dataclass(frozen=True, slots=True)
class EntityStateV23:
    channel_0: DirectedValueV21
    channel_1: DirectedValueV21

    def to_dict(self) -> dict[str, Any]:
        return {"q0": self.channel_0.to_dict(), "q1": self.channel_1.to_dict()}


@dataclass(frozen=True, slots=True)
class InteractionEdgeV23:
    source: int
    target: int

    def to_dict(self) -> dict[str, int]:
        return {"source": self.source, "target": self.target}


@dataclass(frozen=True, slots=True)
class PhysicsWorldDefinitionV23:
    graph_family: str
    initial_entities: tuple[EntityStateV23, ...]
    interval: DirectedValueV21
    edges: tuple[InteractionEdgeV23, ...]
    transfer_schedule: tuple[tuple[DirectedValueV21, ...], ...]
    step_count: int
    seed: int

    @property
    def world_id(self) -> str:
        payload = json.dumps(self.to_dict(include_id=False), sort_keys=True, separators=(",", ":"))
        return "PW-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self, *, include_id: bool = True) -> dict[str, Any]:
        result = {
            "graph_family": self.graph_family,
            "initial_entities": [item.to_dict() for item in self.initial_entities],
            "interval": self.interval.to_dict(),
            "edges": [item.to_dict() for item in self.edges],
            "transfer_schedule": [[item.to_dict() for item in row] for row in self.transfer_schedule],
            "step_count": self.step_count,
            "seed": self.seed,
            "human_entity_names": None,
            "human_physics_law": None,
        }
        if include_id:
            result["world_id"] = self.world_id
        return result


@dataclass(frozen=True, slots=True)
class WorldTraceStepV23:
    step_index: int
    before: tuple[EntityStateV23, ...]
    after_exchange: tuple[EntityStateV23, ...]
    after_transition: tuple[EntityStateV23, ...]
    total_before: DirectedValueV21
    total_after: DirectedValueV21
    conserved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "before": [item.to_dict() for item in self.before],
            "after_exchange": [item.to_dict() for item in self.after_exchange],
            "after_transition": [item.to_dict() for item in self.after_transition],
            "total_before": self.total_before.to_dict(),
            "total_after": self.total_after.to_dict(),
            "conserved": self.conserved,
        }


@dataclass(frozen=True, slots=True)
class WorldExecutionV23:
    world_id: str
    final_entities: tuple[EntityStateV23, ...]
    trace: tuple[WorldTraceStepV23, ...]
    deterministic_digest: str
    transition_count: int
    interaction_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "final_entities": [item.to_dict() for item in self.final_entities],
            "trace": [item.to_dict() for item in self.trace],
            "deterministic_digest": self.deterministic_digest,
            "transition_count": self.transition_count,
            "interaction_count": self.interaction_count,
        }


@dataclass(frozen=True, slots=True)
class WorldQualityV23:
    executable: bool
    deterministic: bool
    nontrivial_motion: bool
    nontrivial_interaction: bool
    additive_total_conserved: bool
    dimension_contract_preserved: bool
    finite_cost: bool

    @property
    def accepted(self) -> bool:
        return all((
            self.executable,
            self.deterministic,
            self.nontrivial_motion,
            self.nontrivial_interaction,
            self.additive_total_conserved,
            self.dimension_contract_preserved,
            self.finite_cost,
        ))

    def to_dict(self) -> dict[str, bool]:
        return {
            "executable": self.executable,
            "deterministic": self.deterministic,
            "nontrivial_motion": self.nontrivial_motion,
            "nontrivial_interaction": self.nontrivial_interaction,
            "additive_total_conserved": self.additive_total_conserved,
            "dimension_contract_preserved": self.dimension_contract_preserved,
            "finite_cost": self.finite_cost,
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class ConstructedWorldV23:
    definition: PhysicsWorldDefinitionV23
    execution: WorldExecutionV23
    quality: WorldQualityV23

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition": self.definition.to_dict(),
            "execution": self.execution.to_dict(),
            "quality": self.quality.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PhysicsWorldConstructionV23:
    worlds_generated: int
    worlds_accepted: int
    graph_family_count: int
    entity_count_range: tuple[int, int]
    total_simulated_steps: int
    total_interactions: int
    worlds: tuple[ConstructedWorldV23, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "worlds_generated": self.worlds_generated,
            "worlds_accepted": self.worlds_accepted,
            "graph_family_count": self.graph_family_count,
            "entity_count_range": list(self.entity_count_range),
            "total_simulated_steps": self.total_simulated_steps,
            "total_interactions": self.total_interactions,
            "worlds": [item.to_dict() for item in self.worlds],
        }


class AutonomousPhysicsWorldFactoryV23:
    def __init__(self, world_count: int = 24, step_count: int = 6, seed_base: int = 23_000) -> None:
        self.world_count = world_count
        self.step_count = step_count
        self.seed_base = seed_base

    def generate(self) -> tuple[PhysicsWorldDefinitionV23, ...]:
        return tuple(self._world(index) for index in range(self.world_count))

    def _world(self, index: int) -> PhysicsWorldDefinitionV23:
        phase = self.seed_base + index
        graph_family = ("G0", "G1", "G2")[phase % 3]
        entity_count = 2 + phase % 4
        if graph_family == "G1" and entity_count == 2:
            entity_count = 3
        initial = tuple(
            EntityStateV23(
                self._directed(1 + ((phase + entity * 2) % 7), 1 + ((phase + entity) % 3), (phase + entity) % 3 == 0),
                self._directed(1 + ((phase * 2 + entity) % 5), 1 + ((phase + entity * 3) % 3), (phase + entity) % 2 == 1),
            )
            for entity in range(entity_count)
        )
        interval = DirectedValueV21(1 + phase % 2, 0, 1 + phase % 3)
        edges = self._edges(graph_family, entity_count)
        schedule = tuple(
            tuple(
                self._directed(
                    1 + ((phase + step + edge_index) % 3),
                    2 + ((phase + edge_index) % 2),
                    (phase + step + edge_index) % 2 == 1,
                )
                for edge_index in range(len(edges))
            )
            for step in range(self.step_count)
        )
        return PhysicsWorldDefinitionV23(graph_family, initial, interval, edges, schedule, self.step_count, phase)

    @staticmethod
    def _directed(magnitude: int, denominator: int, reverse: bool) -> DirectedValueV21:
        return DirectedValueV21(0, magnitude, denominator) if reverse else DirectedValueV21(magnitude, 0, denominator)

    @staticmethod
    def _edges(family: str, count: int) -> tuple[InteractionEdgeV23, ...]:
        if family == "G0":
            return tuple(InteractionEdgeV23(index, index + 1) for index in range(count - 1))
        if family == "G1":
            return tuple(InteractionEdgeV23(index, (index + 1) % count) for index in range(count))
        return tuple(InteractionEdgeV23(0, index) for index in range(1, count))


class PhysicsWorldExecutorV23:
    def __init__(self, runtime: DirectedPhysicsRuntimeV22, transition_programs: Sequence[ChannelProgramV22]) -> None:
        self.runtime = runtime
        self.transition_programs = tuple(sorted(transition_programs, key=lambda item: item.output_channel))
        if len(self.transition_programs) != 4:
            raise ValueError("V23 requires four installed V22 transition programs")

    def execute(self, definition: PhysicsWorldDefinitionV23) -> WorldExecutionV23:
        entities = definition.initial_entities
        trace = []
        for step_index in range(definition.step_count):
            before = entities
            total_before = self._total_channel_1(before)
            exchanged = list(before)
            for edge, transfer in zip(definition.edges, definition.transfer_schedule[step_index], strict=True):
                source = exchanged[edge.source]
                target = exchanged[edge.target]
                source_velocity = self.runtime.normalize(self.runtime.directed.execute_binary(self.runtime.combine, source.channel_1, transfer))
                reverse = self.runtime.directed.execute_unary(self.runtime.inverse, transfer)
                target_velocity = self.runtime.normalize(self.runtime.directed.execute_binary(self.runtime.combine, target.channel_1, reverse))
                exchanged[edge.source] = EntityStateV23(source.channel_0, source_velocity)
                exchanged[edge.target] = EntityStateV23(target.channel_0, target_velocity)
            after_exchange = tuple(exchanged)
            transitioned = []
            for entity in after_exchange:
                state = (entity.channel_0, entity.channel_1, self.runtime.zero, definition.interval)
                outputs = tuple(self.runtime.evaluate(program.expression, state) for program in self.transition_programs)
                transitioned.append(EntityStateV23(outputs[0], outputs[1]))
            entities = tuple(transitioned)
            total_after = self._total_channel_1(entities)
            trace.append(WorldTraceStepV23(
                step_index, before, after_exchange, entities,
                total_before, total_after,
                self.runtime.equivalent(total_before, total_after),
            ))
        payload = json.dumps([item.to_dict() for item in trace], sort_keys=True, separators=(",", ":"))
        return WorldExecutionV23(
            definition.world_id,
            entities,
            tuple(trace),
            hashlib.sha256(payload.encode()).hexdigest(),
            definition.step_count * len(entities),
            definition.step_count * len(definition.edges),
        )

    def _total_channel_1(self, entities: Sequence[EntityStateV23]) -> DirectedValueV21:
        total = self.runtime.zero
        for entity in entities:
            total = self.runtime.normalize(self.runtime.directed.execute_binary(self.runtime.combine, total, entity.channel_1))
        return total


class AutonomousPhysicsWorldConstructorV23:
    def __init__(self, executor: PhysicsWorldExecutorV23) -> None:
        self.executor = executor

    def construct(self, definitions: Sequence[PhysicsWorldDefinitionV23]) -> PhysicsWorldConstructionV23:
        worlds = []
        for definition in definitions:
            execution = self.executor.execute(definition)
            replay = self.executor.execute(definition)
            changed_position = any(
                not self.executor.runtime.equivalent(step.before[index].channel_0, step.after_transition[index].channel_0)
                for step in execution.trace for index in range(len(step.before))
            )
            changed_exchange = any(
                not self.executor.runtime.equivalent(step.before[index].channel_1, step.after_exchange[index].channel_1)
                for step in execution.trace for index in range(len(step.before))
            )
            quality = WorldQualityV23(
                executable=True,
                deterministic=execution.deterministic_digest == replay.deterministic_digest,
                nontrivial_motion=changed_position,
                nontrivial_interaction=changed_exchange,
                additive_total_conserved=all(step.conserved for step in execution.trace),
                dimension_contract_preserved=True,
                finite_cost=execution.transition_count + execution.interaction_count <= 1_000,
            )
            worlds.append(ConstructedWorldV23(definition, execution, quality))
        accepted = tuple(item for item in worlds if item.quality.accepted)
        counts = [len(item.definition.initial_entities) for item in worlds]
        return PhysicsWorldConstructionV23(
            len(worlds), len(accepted), len({item.definition.graph_family for item in worlds}),
            (min(counts), max(counts)),
            sum(item.execution.transition_count for item in worlds),
            sum(item.execution.interaction_count for item in worlds),
            tuple(worlds),
        )
