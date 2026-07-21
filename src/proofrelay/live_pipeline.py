from __future__ import annotations

import os
from pathlib import Path

from genblaze_core import KeyStrategy, Modality, ObjectStorageSink, Pipeline
from genblaze_openai import DalleProvider
from genblaze_s3 import S3StorageBackend
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .compositor import ProofCardProvider
from .models import ApprovedIncident


class LivePipelineSettings(BaseModel):
    """Secrets and storage coordinates required by the live media pipeline."""

    model_config = ConfigDict(str_strip_whitespace=True)

    openai_api_key: SecretStr
    b2_key_id: SecretStr
    b2_app_key: SecretStr
    b2_bucket: str = Field(min_length=3, max_length=63)
    b2_region: str | None = None
    b2_public_url_base: str | None = None

    @classmethod
    def from_environment(cls) -> "LivePipelineSettings":
        missing = [
            name
            for name in ("OPENAI_API_KEY", "B2_KEY_ID", "B2_APP_KEY", "B2_BUCKET")
            if not os.environ.get(name)
        ]
        if missing:
            raise RuntimeError(
                "Live pipeline is not configured; missing " + ", ".join(missing)
            )
        return cls(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            b2_key_id=os.environ["B2_KEY_ID"],
            b2_app_key=os.environ["B2_APP_KEY"],
            b2_bucket=os.environ["B2_BUCKET"],
            b2_region=os.environ.get("B2_REGION"),
            b2_public_url_base=os.environ.get("B2_PUBLIC_URL_BASE"),
        )


class LiveVisualResult(BaseModel):
    incident_id: str
    run_id: str
    provider: str
    model: str
    asset_url: str
    asset_sha256: str
    manifest_uri: str | None
    manifest_hash: str
    manifest_verified: bool
    publication_status: str = "awaiting_human_approval"


def build_visual_prompt(incident: ApprovedIncident) -> str:
    """Create an illustration-only prompt grounded in the approved report."""

    return "\n".join(
        [
            "Create a documentary-style editorial illustration for a field briefing.",
            "Show only a plausible environmental context, not an invented event or person.",
            "Do not add any text, logos, faces, injuries, or identifying information.",
            "Use a restrained natural palette with clear negative space for a later factual overlay.",
            "Landscape composition, 3:2 aspect ratio, production-ready and respectful.",
            f"Approved report title: {incident.title}",
            f"Approved report summary: {incident.summary}",
            f"General location: {incident.location}",
            f"Severity: {incident.severity}",
        ]
    )


def build_live_visual(
    incident: ApprovedIncident,
    output_dir: Path,
    settings: LivePipelineSettings | None = None,
) -> LiveVisualResult:
    """Generate one visual with Genblaze and persist asset + manifest to B2."""

    settings = settings or LivePipelineSettings.from_environment()
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = DalleProvider(
        api_key=settings.openai_api_key.get_secret_value(),
        output_dir=output_dir,
    )
    backend = S3StorageBackend.for_backblaze(
        settings.b2_bucket,
        region=settings.b2_region,
        key_id=settings.b2_key_id.get_secret_value(),
        app_key=settings.b2_app_key.get_secret_value(),
        public_url_base=settings.b2_public_url_base,
    )
    sink = ObjectStorageSink(
        backend,
        prefix="proofrelay",
        key_strategy=KeyStrategy.HIERARCHICAL,
    )
    result = (
        Pipeline(
            "proofrelay-approved-visual",
            tenant_id="prototype",
            project_id="proofrelay",
            chain=True,
        )
        .step(
            provider,
            model="gpt-image-2",
            prompt=build_visual_prompt(incident),
            modality=Modality.IMAGE,
            size="1536x1024",
            quality="low",
            output_format="png",
            moderation="auto",
            incident_id=incident.incident_id,
            human_approved=True,
        )
        .step(
            ProofCardProvider(incident, output_dir),
            model="proof-card-v1",
            prompt=(
                "Compose the generated illustration with the exact human-approved "
                "report fields and a visible provenance notice."
            ),
            modality=Modality.IMAGE,
            input_from=0,
            incident_id=incident.incident_id,
            deterministic_overlay=True,
        )
        .run(sink=sink, timeout=180, raise_on_failure=True)
    )

    if result.error_summary():
        raise RuntimeError(result.error_summary())
    step = result.run.steps[-1]
    if not step.assets:
        raise RuntimeError("The live provider completed without returning an asset.")
    asset = step.assets[0]

    return LiveVisualResult(
        incident_id=incident.incident_id,
        run_id=result.run.run_id,
        provider=step.provider,
        model=step.model,
        asset_url=asset.url,
        asset_sha256=asset.sha256 or "",
        manifest_uri=result.manifest.manifest_uri,
        manifest_hash=result.manifest.canonical_hash,
        manifest_verified=result.manifest.verify(),
    )
