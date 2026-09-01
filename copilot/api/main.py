from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from copilot.api.copilot_api import CopilotAPI

app = FastAPI(title="Climate Copilot API", version="2.1.0")
api = CopilotAPI()


class AskRequest(BaseModel):
    query: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[str] = []
    intermediate_steps: list[dict[str, Any]] = []
    latency_ms: float = 0.0
    intent: str = ""


@app.get("/health/live")
def health_live():
    return {"status": "alive", "service": "copilot-agent"}


@app.get("/health")
def health():
    llm_ok, llm_msg = False, "not initialized"
    try:
        if hasattr(api.orchestrator, "llm_client"):
            result = [None]

            def _check():
                try:
                    result[0] = api.orchestrator.llm_client.health_check()
                except Exception:
                    result[0] = (False, "check failed")

            t = threading.Thread(target=_check, daemon=True)
            t.start()
            t.join(timeout=1.0)
            if result[0] is not None:
                llm_ok, llm_msg = result[0]
            else:
                llm_msg = "ollama health check timed out"
    except Exception as e:
        llm_msg = str(e)

    tools: dict[str, Any] = {}
    try:
        tools_result: list[Any] = [None]

        def _tools_check():
            try:
                tools_result[0] = api.health_check().get("tools", {}) or {}
            except Exception:
                tools_result[0] = {}

        tt = threading.Thread(target=_tools_check, daemon=True)
        tt.start()
        tt.join(timeout=2.0)
        if tools_result[0] is not None:
            tools = tools_result[0]
    except Exception:
        tools = {}

    return {
        "status": "healthy",
        "service": "copilot-agent",
        "version": "2.1.0",
        "ollama": {"ok": llm_ok, "message": llm_msg},
        "tools": tools,
    }


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    result = api.ask(req.query, req.conversation_id)
    if result.error:
        raise HTTPException(status_code=400, detail=result.error)
    return AskResponse(
        answer=result.answer,
        citations=result.citations,
        intermediate_steps=result.intermediate_steps,
        latency_ms=result.latency_ms,
        intent=result.intent.value if result.intent else "",
    )


@app.post("/conversation")
def create_conversation():
    conv_id = api.new_conversation()
    return {"conversation_id": conv_id}


@app.get("/conversation/{conversation_id}/history")
def get_history(conversation_id: str):
    try:
        return api.get_history(conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@app.get("/conversations")
def list_conversations():
    return api.list_conversations()
