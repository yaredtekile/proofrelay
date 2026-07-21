from __future__ import annotations

import base64
import hashlib
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

from genblaze_core.models.asset import Asset
from genblaze_core.models.step import Step
from genblaze_core.providers.base import SyncProvider
from genblaze_core.runnable.config import RunnableConfig

from .models import ApprovedIncident
from .pipeline import _wrap


class ProofCardProvider(SyncProvider):
    """Deterministic Genblaze step that adds a factual overlay to an AI image.

    The generative provider creates only an illustration. This second step adds
    human-approved text and a visible provenance notice without asking a model
    to render facts or typography. Both steps remain in one Genblaze manifest.
    """

    name = "proofrelay-layout"

    def __init__(self, incident: ApprovedIncident, output_dir: Path) -> None:
        super().__init__()
        self._incident = incident
        self._output_dir = output_dir

    def generate(self, step: Step, config: RunnableConfig | None = None) -> Step:
        if not step.inputs:
            raise ValueError("ProofCardProvider requires an illustration input")

        source = step.inputs[0]
        image_bytes = _read_asset(source)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        media_type = source.media_type if source.media_type.startswith("image/") else "image/png"
        svg_bytes = _compose_svg(self._incident, encoded, media_type)

        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / f"{step.step_id}-proof-card.svg"
        path.write_bytes(svg_bytes)
        step.assets.append(
            Asset(
                url=path.resolve().as_uri(),
                media_type="image/svg+xml",
                sha256=hashlib.sha256(svg_bytes).hexdigest(),
                size_bytes=len(svg_bytes),
            )
        )
        return step


def _read_asset(asset: Asset) -> bytes:
    parsed = urlparse(asset.url)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path)).read_bytes()
    if parsed.scheme == "https":
        with urlopen(asset.url, timeout=30) as response:  # noqa: S310 - trusted pipeline asset
            return response.read(20_000_001)
    raise ValueError("ProofCardProvider accepts only file:// or https:// inputs")


def _compose_svg(
    incident: ApprovedIncident,
    image_base64: str,
    media_type: str,
) -> bytes:
    summary = "".join(
        f'<text x="76" y="{402 + index * 34}" class="body">{escape(line)}</text>'
        for index, line in enumerate(_wrap(incident.summary, 63)[:5])
    )
    approved_at = incident.approved_at.isoformat(timespec="minutes")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="1024" viewBox="0 0 1536 1024">
  <defs>
    <linearGradient id="shade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#11130f" stop-opacity=".84"/><stop offset=".64" stop-color="#11130f" stop-opacity=".48"/><stop offset="1" stop-color="#11130f" stop-opacity=".12"/></linearGradient>
    <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .09"/></feComponentTransfer></filter>
  </defs>
  <image width="1536" height="1024" preserveAspectRatio="xMidYMid slice" href="data:{escape(media_type)};base64,{image_base64}"/>
  <rect width="1536" height="1024" fill="url(#shade)"/>
  <rect width="1536" height="1024" filter="url(#grain)" opacity=".35"/>
  <rect x="52" y="52" width="1432" height="920" rx="22" fill="none" stroke="#f6f0df" stroke-width="3"/>
  <style>
    .mono {{ font: 700 21px ui-monospace, monospace; letter-spacing: 3px; fill: #d8f64a; }}
    .title {{ font: 700 74px Georgia, serif; fill: #fffaf0; }}
    .meta {{ font: 600 25px ui-sans-serif, sans-serif; fill: #f3ead7; }}
    .body {{ font: 500 29px ui-sans-serif, sans-serif; fill: #fffaf0; }}
    .small {{ font: 600 17px ui-monospace, monospace; fill: #f3ead7; }}
    .badge {{ font: 800 18px ui-monospace, monospace; letter-spacing: 2px; fill: #151612; }}
  </style>
  <text x="76" y="104" class="mono">PROOFRELAY / VERIFIED MEDIA BRIEF</text>
  <rect x="1247" y="74" width="186" height="48" rx="24" fill="#d8f64a"/>
  <text x="1340" y="105" text-anchor="middle" class="badge">{incident.severity.upper()}</text>
  <text x="76" y="238" class="title">{escape(incident.title)}</text>
  <text x="76" y="300" class="meta">{escape(incident.location)} · {escape(incident.audience)}</text>
  {summary}
  <line x1="76" y1="860" x2="1460" y2="860" stroke="#f6f0df" stroke-opacity=".7"/>
  <text x="76" y="905" class="small">SOURCE APPROVED BY {escape(incident.approved_by).upper()} · {escape(approved_at)}</text>
  <text x="1460" y="905" text-anchor="end" class="small">{escape(incident.incident_id)}</text>
  <text x="76" y="942" class="small">AI ILLUSTRATION + DETERMINISTIC FACTUAL OVERLAY · VERIFY MANIFEST BEFORE REDISTRIBUTION</text>
</svg>"""
    return svg.encode("utf-8")

