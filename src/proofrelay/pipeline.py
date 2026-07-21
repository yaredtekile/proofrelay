from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path

from genblaze_core import Manifest, Modality, RunBuilder, StepBuilder, StepStatus

from .models import ApprovedIncident, BriefBundle


SEVERITY_COLORS = {
    "low": ("#1f7a5a", "#d9f7ea"),
    "medium": ("#9a6700", "#fff1c2"),
    "high": ("#b54708", "#ffead5"),
    "critical": ("#b42318", "#fee4e2"),
}


def _wrap(text: str, width: int = 58) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and len(candidate) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:7]


def _render_svg(incident: ApprovedIncident) -> bytes:
    accent, wash = SEVERITY_COLORS[incident.severity]
    summary_lines = _wrap(incident.summary)
    text_rows = "".join(
        f'<text x="72" y="{286 + index * 38}" class="body">{escape(line)}</text>'
        for index, line in enumerate(summary_lines)
    )
    approved_at = incident.approved_at.isoformat(timespec="minutes")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
  <rect width="1200" height="675" fill="#f6f2e8"/>
  <rect x="32" y="32" width="1136" height="611" rx="28" fill="#fffdf8" stroke="#1d2939" stroke-width="2"/>
  <rect x="32" y="32" width="18" height="611" rx="9" fill="{accent}"/>
  <style>
    .eyebrow {{ font: 700 20px ui-monospace, SFMono-Regular, monospace; letter-spacing: 2px; fill: #475467; }}
    .title {{ font: 700 52px Inter, system-ui, sans-serif; fill: #101828; }}
    .meta {{ font: 600 22px Inter, system-ui, sans-serif; fill: #344054; }}
    .body {{ font: 400 28px Inter, system-ui, sans-serif; fill: #1d2939; }}
    .small {{ font: 500 18px Inter, system-ui, sans-serif; fill: #667085; }}
    .badge {{ font: 800 19px Inter, system-ui, sans-serif; fill: {accent}; letter-spacing: 1px; }}
  </style>
  <text x="72" y="90" class="eyebrow">PROOFRELAY / VERIFIED FIELD BRIEF</text>
  <rect x="890" y="61" width="226" height="48" rx="24" fill="{wash}"/>
  <text x="1003" y="92" text-anchor="middle" class="badge">{incident.severity.upper()}</text>
  <text x="72" y="174" class="title">{escape(incident.title)}</text>
  <text x="72" y="224" class="meta">{escape(incident.location)} · {escape(incident.audience)}</text>
  {text_rows}
  <line x1="72" y1="558" x2="1120" y2="558" stroke="#d0d5dd"/>
  <text x="72" y="597" class="small">Human-approved by {escape(incident.approved_by)} · {escape(approved_at)}</text>
  <text x="1120" y="597" text-anchor="end" class="small">ID {escape(incident.incident_id)}</text>
  <text x="72" y="624" class="small">AI-assisted media · verify provenance before redistribution</text>
</svg>"""
    return svg.encode("utf-8")


def build_preview_bundle(
    incident: ApprovedIncident,
    output_dir: Path,
) -> BriefBundle:
    """Build a real media asset and a verifiable Genblaze manifest locally.

    This deterministic step is the safe development fallback. The production
    pipeline will swap in a Genblaze image/audio provider and B2 sink while
    preserving this bundle contract and the separate publication approval gate.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    asset_path = output_dir / "brief.svg"
    manifest_path = output_dir / "manifest.json"
    bundle_path = output_dir / "bundle.json"

    asset_bytes = _render_svg(incident)
    asset_path.write_bytes(asset_bytes)
    asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()

    prompt = (
        "Create a concise, factual field briefing card from an already "
        "human-approved report. Preserve severity, location, audience, and "
        "approval attribution; do not invent details."
    )
    step = (
        StepBuilder("proofrelay", "approved-report-card-v1")
        .prompt(prompt)
        .modality(Modality.IMAGE)
        .params(
            incident_id=incident.incident_id,
            language=incident.language,
            audience=incident.audience,
            human_approved=True,
        )
        .status(StepStatus.SUCCEEDED)
        .asset(
            asset_path.resolve().as_uri(),
            "image/svg+xml",
            sha256=asset_sha256,
            size_bytes=len(asset_bytes),
        )
        .build()
    )
    run = (
        RunBuilder("proofrelay-approved-brief")
        .project("proofrelay")
        .tenant("prototype")
        .meta(
            incident_id=incident.incident_id,
            approved_by=incident.approved_by,
            publication_status="awaiting_human_approval",
        )
        .add_step(step)
        .build()
    )
    manifest = Manifest.from_run(run)
    manifest_verified = manifest.verify()
    manifest_path.write_text(manifest.to_canonical_json(), encoding="utf-8")

    index = {
        "incident_id": incident.incident_id,
        "asset": asset_path.name,
        "asset_sha256": asset_sha256,
        "manifest": manifest_path.name,
        "manifest_hash": manifest.canonical_hash,
        "manifest_verified": manifest_verified,
        "publication_status": "awaiting_human_approval",
    }
    bundle_path.write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return BriefBundle(
        incident_id=incident.incident_id,
        asset_path=asset_path,
        manifest_path=manifest_path,
        bundle_path=bundle_path,
        asset_sha256=asset_sha256,
        manifest_hash=manifest.canonical_hash,
        manifest_verified=manifest_verified,
    )

