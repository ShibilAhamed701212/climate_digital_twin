from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from copilot.api.copilot_api import CopilotAPI

app = FastAPI(title="Climate Copilot API", version="1.0.0")
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


@app.get("/health")
def health():
    llm_ok, llm_msg = api.orchestrator.llm_client.health_check()
    return {
        "status": "healthy",
        "service": "copilot-agent",
        "version": "1.0.0",
        "ollama": {"ok": llm_ok, "message": llm_msg},
        "tools": api.health_check().get("tools", {}),
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
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/conversations")
def list_conversations():
    return api.list_conversations()
