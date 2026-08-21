from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Mapping
from .linear_algebra_foundation_v9 import replay_linear_algebra_foundation_v9
class LinearAlgebraFoundationV9Room:
    ZERO_HASH="0"*64
    def __init__(self,path:Path):self.path=path.resolve();self._events:list[dict[str,Any]]=[];self._load() if self.path.exists() else None
    @property
    def records(self):return tuple(self._events)
    def record(self,report:Mapping[str,Any]):
        if not replay_linear_algebra_foundation_v9(report)["passed"]:raise ValueError("linear foundation cannot enter room")
        digest=str(report["content_digest"]);existing=next((x for x in self._events if x["content_digest"]==digest),None)
        if existing:return existing
        e={"schema_version":"linear-foundation-v9-event-v0.1","event_index":len(self._events),"timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"content_digest":digest,"report":dict(report),"previous_event_hash":self._events[-1]["event_hash"] if self._events else self.ZERO_HASH};e["event_hash"]=_h(e);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8",newline="\n") as s:s.write(json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n");s.flush();os.fsync(s.fileno())
        self._events.append(e);return e
    def _load(self):
        previous=self.ZERO_HASH
        for number,line in enumerate(self.path.read_text(encoding="utf-8").splitlines(),1):
            if not line:continue
            e=json.loads(line);valid=replay_linear_algebra_foundation_v9(e.get("report",{}))["passed"]
            if e.get("event_index")!=len(self._events) or e.get("previous_event_hash")!=previous or e.get("event_hash")!=_h(e) or not valid:raise ValueError(f"linear room replay failed {number}")
            self._events.append(e);previous=e["event_hash"]
def _h(e:Mapping[str,Any])->str:return hashlib.sha256(json.dumps({k:v for k,v in e.items() if k!="event_hash"},ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
