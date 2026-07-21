from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .models import ApprovedIncident
from .pipeline import build_preview_bundle


WEB_ROOT = Path(__file__).parent / "web"
RUN_ROOT = Path(os.environ.get("PROOFRELAY_RUN_ROOT", "build/web-runs")).resolve()
SAFE_RUN_ID = re.compile(r"^[a-f0-9]{32}$")
RUN_FILES = {"brief.svg", "manifest.json", "bundle.json", "approval.json"}

app = FastAPI(
    title="ProofRelay",
    description="Provenance-first media briefs for field teams",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reviewer: str = Field(min_length=2, max_length=120)
    note: str = Field(default="Approved for publication", max_length=500)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "proofrelay"}


@app.post("/api/preview")
def preview(incident: ApprovedIncident) -> dict[str, object]:
    run_id = uuid4().hex
    run_dir = RUN_ROOT / run_id
    bundle = build_preview_bundle(incident, run_dir)
    return {
        "run_id": run_id,
        "incident_id": bundle.incident_id,
        "asset_url": f"/runs/{run_id}/brief.svg",
        "manifest_url": f"/runs/{run_id}/manifest.json",
        "asset_sha256": bundle.asset_sha256,
        "manifest_hash": bundle.manifest_hash,
        "manifest_verified": bundle.manifest_verified,
        "publication_status": bundle.publication_status,
    }


@app.post("/api/runs/{run_id}/approve")
def approve(run_id: str, approval: ApprovalRequest) -> dict[str, str]:
    run_dir = _resolve_run(run_id)
    if not (run_dir / "manifest.json").is_file():
        raise HTTPException(status_code=404, detail="Run not found")
    record = {
        "run_id": run_id,
        "reviewer": approval.reviewer,
        "note": approval.note,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "publication_status": "approved_for_publication",
    }
    (run_dir / "approval.json").write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return record


@app.get("/runs/{run_id}/{filename}", include_in_schema=False)
def run_file(run_id: str, filename: str) -> FileResponse:
    if filename not in RUN_FILES:
        raise HTTPException(status_code=404, detail="File not found")
    path = _resolve_run(run_id) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "image/svg+xml" if filename.endswith(".svg") else "application/json"
    return FileResponse(path, media_type=media_type)


def _resolve_run(run_id: str) -> Path:
    if not SAFE_RUN_ID.fullmatch(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return RUN_ROOT / run_id


def main() -> None:
    uvicorn.run(
        "proofrelay.webapp:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )

