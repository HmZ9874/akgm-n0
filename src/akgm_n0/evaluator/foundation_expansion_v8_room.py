from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Mapping
from .foundation_expansion_v8 import replay_foundation_expansion_v8

class FoundationExpansionV8Room:
    ZERO_HASH="0"*64
    def __init__(self,path:Path)->None:
        self.path=path.resolve();self._events:list[dict[str,Any]]=[]
        if self.path.exists():self._load()
    @property
    def records(self):return tuple(self._events)
    def record(self,report:Mapping[str,Any])->Mapping[str,Any]:
        replay=replay_foundation_expansion_v8(report)
        if not replay["passed"] or report.get("passed") is not True:raise ValueError("foundation expansion cannot enter room")
        digest=str(report["content_digest"]);existing=next((e for e in self._events if e["content_digest"]==digest),None)
        if existing:return existing
        event={"schema_version":"foundation-expansion-v8-event-v0.1","event_index":len(self._events),"timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"content_digest":digest,"report":dict(report),"previous_event_hash":self._events[-1]["event_hash"] if self._events else self.ZERO_HASH}
        event["event_hash"]=_hash(event);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n");stream.flush();os.fsync(stream.fileno())
        self._events.append(event);return event
    def _load(self)->None:
        previous=self.ZERO_HASH
        for number,line in enumerate(self.path.read_text(encoding="utf-8").splitlines(),1):
            if not line:continue
            event=json.loads(line);valid=replay_foundation_expansion_v8(event.get("report",{}))["passed"]
            if event.get("event_index")!=len(self._events) or event.get("previous_event_hash")!=previous or event.get("event_hash")!=_hash(event) or not valid:raise ValueError(f"foundation expansion room replay failed line {number}")
            self._events.append(event);previous=event["event_hash"]
def _hash(event:Mapping[str,Any])->str:
    payload={k:v for k,v in event.items() if k!="event_hash"};return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
