"""Anonymous composition-graph search over previously proven operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .metamachine_gen2 import InvalidReflectiveProgram, ReflectiveExecutor, ReflectiveProgram
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class CompositionNode:
    operation_id: str
    arguments: tuple[str, ...]

    def to_dict(self): return {"operation_id": self.operation_id, "arguments": list(self.arguments)}


@dataclass(frozen=True, slots=True)
class CompositionExecution:
    output_value: float


@dataclass(frozen=True, slots=True)
class CompositionGraphProgram:
    nodes: tuple[CompositionNode, ...]

    def to_dict(self):
        return {"substrate": "anonymous_verified_composition_graph_v0.1",
                "nodes": [node.to_dict() for node in self.nodes], "output": f"node:{len(self.nodes)-1}"}

    @classmethod
    def from_dict(cls, value):
        if value.get("substrate") != "anonymous_verified_composition_graph_v0.1":
            raise ValueError("invalid composition substrate")
        nodes = tuple(CompositionNode(str(item["operation_id"]), tuple(item["arguments"])) for item in value["nodes"])
        if value.get("output") != f"node:{len(nodes)-1}" or not nodes:
            raise ValueError("invalid composition output")
        return cls(nodes)

    @property
    def component_operation_ids(self): return tuple(dict.fromkeys(node.operation_id for node in self.nodes))


class CompositionExecutor:
    def __init__(self, library: Mapping[str, ReflectiveProgram], *, maximum_steps=100000):
        self.library = dict(library); self.executor = ReflectiveExecutor(maximum_steps=maximum_steps)

    def execute(self, program: CompositionGraphProgram, inputs):
        values = []
        for index, node in enumerate(program.nodes):
            args = []
            for ref in node.arguments:
                kind, raw = ref.split(":", 1); position = int(raw)
                if kind == "input": args.append(inputs[position])
                elif kind == "node" and position < index: args.append(values[position])
                else: raise InvalidReflectiveProgram("invalid composition reference")
            component = self.library.get(node.operation_id)
            if component is None: raise InvalidReflectiveProgram("unavailable proven component")
            values.append(self.executor.execute(component, tuple(args)).output_value)
        return CompositionExecution(values[-1])


@dataclass(frozen=True, slots=True)
class CompositionCandidate:
    candidate_id: str; program: CompositionGraphProgram; fit_error: float
    maximum_absolute_error: float; outputs: tuple[float, ...]; behavior_signature: tuple[float, ...]
    @property
    def exact(self): return self.maximum_absolute_error == 0
    def to_dict(self):
        return {"candidate_id": self.candidate_id, "program": self.program.to_dict(),
                "fit_error": self.fit_error, "maximum_absolute_error": self.maximum_absolute_error,
                "outputs": list(self.outputs), "behavior_signature": list(self.behavior_signature),
                "instruction_count": len(self.program.nodes), "exact": self.exact}


@dataclass(frozen=True, slots=True)
class CompositionSearchReport:
    programs_generated: int; programs_executed: int; programs_rejected: int
    behavior_classes: int; top_candidates: tuple[CompositionCandidate, ...]


def composition_key(program):
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


class CompositionGraphSearch:
    def __init__(self, library, arities, *, top_k=100):
        self.library=dict(library); self.arities=dict(arities); self.top_k=top_k
        self.executor=CompositionExecutor(self.library)
        unary=[op for op in self.library if self.arities.get(op)==1]
        binary=[op for op in self.library if self.arities.get(op)==2]
        programs=[]
        for inner in unary:
            for outer in unary:
                if inner != outer:
                    programs.append(CompositionGraphProgram((CompositionNode(inner,("input:0",)),CompositionNode(outer,("node:0",)))))
        for left in unary:
            for right in unary:
                if left == right: continue
                for outer in binary:
                    programs.append(CompositionGraphProgram((CompositionNode(left,("input:0",)),CompositionNode(right,("input:0",)),CompositionNode(outer,("node:0","node:1")))))
        self.programs=tuple(programs)

    def search(self, observation: NumericTableObservation):
        valid=tuple((row,out) for row,out,ok in zip(observation.input_rows,observation.output_values,observation.validity_mask) if ok)
        call_cache={}
        def execute_cached(program,row):
            values=[]
            for index,node in enumerate(program.nodes):
                args=[]
                for ref in node.arguments:
                    kind,raw=ref.split(":",1); position=int(raw)
                    args.append(row[position] if kind=="input" else values[position])
                cache_key=(node.operation_id,tuple(args))
                if cache_key not in call_cache:
                    call_cache[cache_key]=self.executor.executor.execute(self.library[node.operation_id],tuple(args)).output_value
                values.append(call_cache[cache_key])
            return values[-1]
        candidates=[]; rejected=0
        for program in self.programs:
            try: outputs=tuple(execute_cached(program,row) for row,_ in valid)
            except (InvalidReflectiveProgram, IndexError, OverflowError): rejected+=1; continue
            errors=tuple(actual-float(target) for actual,(_,target) in zip(outputs,valid))
            key=composition_key(program)
            candidates.append(CompositionCandidate("CG-"+hashlib.sha256(key.encode()).hexdigest()[:16],program,
                sum(e*e for e in errors)/len(errors),max(abs(e) for e in errors),outputs,outputs))
        candidates.sort(key=lambda c:(c.fit_error,c.maximum_absolute_error,len(c.program.nodes),composition_key(c.program)))
        return CompositionSearchReport(len(self.programs),len(candidates),rejected,len({c.outputs for c in candidates}),tuple(candidates[:self.top_k]))


def composition_logic_signature(program):
    topology=tuple((len(node.arguments),node.arguments) for node in program.nodes)
    semantics=tuple(node.operation_id for node in program.nodes)
    return hashlib.sha256(json.dumps((topology,semantics),sort_keys=True).encode()).hexdigest()
