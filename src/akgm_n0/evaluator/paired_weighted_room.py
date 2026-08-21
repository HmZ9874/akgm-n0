from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Mapping
from akgm_n0.learner.paired_weighted_frontier import PairedWeightedSemantic
from .paired_weighted_proof import verify_paired_weighted_semantic
class PairedWeightedRoom:
    ZERO_HASH="0"*64
    def __init__(self,path:Path)->None:self.path=path.resolve();self._events:list[dict[str,Any]]=[];self._load() if self.path.exists() else None
    @property
    def records(self)->tuple[Mapping[str,Any],...]:return tuple(self._events)
    def record(self,s:PairedWeightedSemantic,p:Mapping[str,Any])->Mapping[str,Any]:
        r=verify_paired_weighted_semantic(s)
        if not r["passed"] or dict(p)!=r:raise ValueError("paired proof cannot replay")
        old=next((x for x in self._events if x["semantic"]["semantic_id"]==s.semantic_id),None)
        if old:return old
        e={"schema_version":"paired-weighted-event-v0.1","event_index":len(self._events),"timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"semantic":s.to_dict(),"proof":r,"previous_event_hash":self._events[-1]["event_hash"] if self._events else self.ZERO_HASH};e["event_hash"]=_h(e);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8",newline="\n") as f:f.write(json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n");f.flush();os.fsync(f.fileno())
        self._events.append(e);return e
    def _load(self)->None:
        prev=self.ZERO_HASH
        for n,line in enumerate(self.path.read_text(encoding="utf-8").splitlines(),1):
            if not line:continue
            e=json.loads(line)
            if e.get("event_index")!=len(self._events) or e.get("previous_event_hash")!=prev or e.get("event_hash")!=_h(e):raise ValueError(f"paired room chain mismatch {n}")
            s=PairedWeightedSemantic.from_dict(e["semantic"]);p=verify_paired_weighted_semantic(s)
            if not p["passed"] or e.get("proof")!=p:raise ValueError("stored paired proof cannot replay")
            self._events.append(e);prev=e["event_hash"]
def _h(e:Mapping[str,Any])->str:return hashlib.sha256(json.dumps({k:v for k,v in e.items() if k!="event_hash"},ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
