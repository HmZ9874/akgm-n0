"""Replay room for finite joint-event discoveries."""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from akgm_n0.learner.joint_frontier import JointFoundationSemantic
from .joint_frontier_proof import verify_joint_foundation_semantic


class JointFrontierRoom:
    ZERO_HASH = "0"*64
    def __init__(self,path:Path)->None:
        self.path=path.resolve(); self._events:list[dict[str,Any]]=[]
        if self.path.exists(): self._load()
    @property
    def records(self)->tuple[Mapping[str,Any],...]: return tuple(self._events)
    def record(self,semantic:JointFoundationSemantic,proof:Mapping[str,Any])->Mapping[str,Any]:
        recomputed=verify_joint_foundation_semantic(semantic)
        if not recomputed["passed"] or dict(proof)!=recomputed: raise ValueError("joint proof cannot be reproduced")
        old=next((x for x in self._events if x["semantic"]["semantic_id"]==semantic.semantic_id),None)
        if old is not None:return old
        event={"schema_version":"joint-frontier-event-v0.1","event_index":len(self._events),"timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"semantic":semantic.to_dict(),"proof":recomputed,"previous_event_hash":self._events[-1]["event_hash"] if self._events else self.ZERO_HASH}
        event["event_hash"]=_h(event); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8",newline="\n") as s:s.write(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n");s.flush();os.fsync(s.fileno())
        self._events.append(event);return event
    def _load(self)->None:
        prev=self.ZERO_HASH
        with self.path.open("r",encoding="utf-8") as s:
            for n,line in enumerate(s,1):
                if not line.strip():continue
                e=json.loads(line)
                if e.get("event_index")!=len(self._events) or e.get("previous_event_hash")!=prev or e.get("event_hash")!=_h(e):raise ValueError(f"joint room chain mismatch at line {n}")
                sem=JointFoundationSemantic.from_dict(e["semantic"]); proof=verify_joint_foundation_semantic(sem)
                if not proof["passed"] or e.get("proof")!=proof:raise ValueError("stored joint proof cannot replay")
                self._events.append(e);prev=e["event_hash"]


def _h(e:Mapping[str,Any])->str:
    p={k:v for k,v in e.items() if k!="event_hash"};return hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
