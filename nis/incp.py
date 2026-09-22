"""
INCP — Inter-Node Communication Protocol [DERIVED]
Canonical v1.1: envelope + trace logger
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import uuid
import time
import json
from enum import Enum

class EnvelopeType(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    EVENT = "EVENT"
    BLOCKED = "BLOCKED"  # CoT firewall

@dataclass
class Envelope:
    envelope_id: str
    trace_id: str
    from_node: str
    to_node: str
    type: EnvelopeType
    payload: Any
    metadata: dict = field(default_factory=dict)
    control: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "envelope_id": self.envelope_id,
            "trace_id": self.trace_id,
            "from": self.from_node,
            "to": self.to_node,
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "payload": self.payload,
            "metadata": self.metadata,
            "control": self.control
        }

def make_envelope(from_node: str, to_node: str, payload: Any, trace_id: str, deliberation_level: str = "L0", priority: int = 3, state: str = "", type: EnvelopeType = EnvelopeType.REQUEST, **control) -> Envelope:
    return Envelope(
        envelope_id=f"nis:turn:{trace_id}:msg:{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        from_node=from_node,
        to_node=to_node,
        type=type,
        payload=payload,
        metadata={
            "deliberation_level": deliberation_level,
            "priority": priority,
            "state": state,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        control=control
    )

@dataclass
class TraceEvent:
    ts: float
    trace_id: str
    stage: str  # INPUT, INTENT, MEMORY, DELIBERATION, PLAN, TOOL_DECISION, PERMISSION, EXECUTION, VERIFICATION, RESPONSE
    node: str
    input_state: str
    output_state: str
    process: str
    payload_summary: str
    deliberation_level: str = ""
    duration_ms: float = 0.0
    envelope_id: str = ""

class TraceLogger:
    def __init__(self):
        self.events = []
        self.start_ts = time.time()

    def log(self, trace_id: str, stage: str, node: str, input_state: str, output_state: str, process: str, payload: Any, deliberation_level: str = "", duration_ms: float = 0, envelope_id: str = ""):
        # Summarize payload for logging
        if isinstance(payload, dict):
            summary = json.dumps(payload, ensure_ascii=False)[:400]
        elif isinstance(payload, str):
            summary = payload[:400]
        else:
            try:
                summary = json.dumps(str(payload))[:400]
            except:
                summary = str(payload)[:400]
        ev = TraceEvent(
            ts=time.time(),
            trace_id=trace_id,
            stage=stage,
            node=node,
            input_state=input_state,
            output_state=output_state,
            process=process,
            payload_summary=summary,
            deliberation_level=deliberation_level,
            duration_ms=duration_ms,
            envelope_id=envelope_id
        )
        self.events.append(ev)
        return ev

    def trace_for(self, trace_id: str):
        return [e for e in self.events if e.trace_id == trace_id]

    def to_dict(self, trace_id: str):
        return [asdict(e) for e in self.trace_for(trace_id)]

    def print_trace(self, trace_id: str):
        print(f"\n{'='*90}")
        print(f"TRACE {trace_id}")
        print(f"{'='*90}")
        for e in self.trace_for(trace_id):
            print(f"[{e.stage:15s}] {e.node:20s} {e.input_state:18s} → {e.output_state:18s} | {e.process[:60]}")
            if e.payload_summary:
                print(f"  └─ {e.payload_summary[:200]}")
            if e.deliberation_level:
                print(f"  └─ level={e.deliberation_level} duration={e.duration_ms:.1f}ms")
        print(f"{'='*90}\n")

# Global logger for MVV
GLOBAL_TRACE = TraceLogger()
