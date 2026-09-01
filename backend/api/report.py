from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from copilot.clients.report_client import ReportClient

logger = logging.getLogger(__name__)

app = FastAPI(title="Climate Report Service", version="2.1.0")
client = ReportClient()


class ReportRequest(BaseModel):
    location: str
    report_type: str = "summary"


@app.get("/health")
def health():
    return {"status": "healthy", "service": "report-service", "version": "2.1.0"}


@app.post("/report")
def generate_report(req: ReportRequest) -> dict[str, Any]:
    valid_types = ["summary", "detailed", "risk", "forecast", "disaster"]
    if req.report_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"report_type must be one of {valid_types}")
    report = client.generate_report(req.location, req.report_type)
    return {"location": req.location, "report_type": req.report_type, "report": report}
