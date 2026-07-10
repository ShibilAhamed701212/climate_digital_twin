from __future__ import annotations

import uuid
from typing import Any

from runtime.models.runtime import RuntimeContext


class TraceManager:
    @staticmethod
    def new_trace_id() -> str:
        return uuid.uuid4().hex[:16]

    @staticmethod
    def create_context(**kwargs: Any) -> RuntimeContext:
        if "trace_id" not in kwargs:
            kwargs["trace_id"] = TraceManager.new_trace_id()
        return RuntimeContext(**kwargs)

    @staticmethod
    def format_trace_log(context: RuntimeContext) -> str:
        if not context.trace_log:
            return f"Trace {context.trace_id}: no stages logged"
        lines = [f"Trace {context.trace_id} ({context.elapsed_ms():.1f}ms):"]
        for entry in context.trace_log:
            lines.append(
                f"  [{entry['elapsed_ms']:>8.1f}ms] {entry['stage']}"
                + (f" -- {entry['details']}" if entry.get("details") else "")
            )
        return "\n".join(lines)
