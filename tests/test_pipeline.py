import base64
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from genblaze_core import Asset, Manifest, Modality, StepBuilder, StepStatus

from proofrelay.compositor import ProofCardProvider
from proofrelay.live_pipeline import LivePipelineSettings, build_visual_prompt
from proofrelay.models import ApprovedIncident
from proofrelay.pipeline import build_preview_bundle
from proofrelay.webapp import app


def test_build_preview_bundle_is_hash_verified(tmp_path: Path) -> None:
    incident = ApprovedIncident.model_validate_json(
        Path("examples/incident.json").read_text(encoding="utf-8")
    )

    bundle = build_preview_bundle(incident, tmp_path)
    asset_bytes = bundle.asset_path.read_bytes()
    manifest = Manifest.model_validate_json(
        bundle.manifest_path.read_text(encoding="utf-8")
    )
    index = json.loads(bundle.bundle_path.read_text(encoding="utf-8"))

    assert bundle.manifest_verified is True
    assert manifest.verify() is True
    assert bundle.asset_sha256 == hashlib.sha256(asset_bytes).hexdigest()
    assert index["publication_status"] == "awaiting_human_approval"
    assert "VERIFY PROVENANCE" not in bundle.asset_path.read_text(encoding="utf-8")
    assert "verify provenance" in bundle.asset_path.read_text(encoding="utf-8")


def test_rendered_card_escapes_untrusted_text(tmp_path: Path) -> None:
    incident = ApprovedIncident.model_validate(
        {
            "incident_id": "FR-test-001",
            "title": "<script>alert(1)</script>",
            "summary": "Verified note with <unsafe> markup that must be escaped.",
            "location": "Addis & Ababa",
            "severity": "medium",
            "approved_by": "Human Reviewer",
            "approved_at": "2026-07-21T10:00:00+03:00",
        }
    )

    bundle = build_preview_bundle(incident, tmp_path)
    svg = bundle.asset_path.read_text(encoding="utf-8")

    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
    assert "Addis &amp; Ababa" in svg


def test_live_settings_fail_closed_without_credentials(monkeypatch) -> None:
    for name in ("OPENAI_API_KEY", "B2_KEY_ID", "B2_APP_KEY", "B2_BUCKET"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        LivePipelineSettings.from_environment()


def test_live_prompt_is_grounded_and_requests_no_text() -> None:
    incident = ApprovedIncident.model_validate_json(
        Path("examples/incident.json").read_text(encoding="utf-8")
    )

    prompt = build_visual_prompt(incident)

    assert incident.title in prompt
    assert incident.summary in prompt
    assert "Do not add any text" in prompt
    assert "not an invented event or person" in prompt


def test_web_preview_and_approval_flow(tmp_path: Path, monkeypatch) -> None:
    import proofrelay.webapp as webapp

    monkeypatch.setattr(webapp, "RUN_ROOT", tmp_path)
    incident = json.loads(Path("examples/incident.json").read_text(encoding="utf-8"))
    client = TestClient(app)

    health = client.get("/health")
    preview = client.post("/api/preview", json=incident)

    assert health.json()["status"] == "ok"
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["manifest_verified"] is True
    assert client.get(payload["asset_url"]).status_code == 200

    approval = client.post(
        f"/api/runs/{payload['run_id']}/approve",
        json={"reviewer": "Yared Tekileselassie"},
    )
    assert approval.status_code == 200
    assert approval.json()["publication_status"] == "approved_for_publication"
    assert (tmp_path / payload["run_id"] / "approval.json").is_file()


def test_web_rejects_path_traversal(tmp_path: Path, monkeypatch) -> None:
    import proofrelay.webapp as webapp

    monkeypatch.setattr(webapp, "RUN_ROOT", tmp_path)
    client = TestClient(app)

    assert client.get("/runs/not-a-run/manifest.json").status_code == 404
    assert client.get("/runs/" + "a" * 32 + "/secret.txt").status_code == 404


def test_proof_card_provider_composes_generated_image_and_exact_facts(
    tmp_path: Path,
) -> None:
    incident = ApprovedIncident.model_validate_json(
        Path("examples/incident.json").read_text(encoding="utf-8")
    )
    source_path = tmp_path / "illustration.png"
    source_path.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    )
    source = Asset(
        url=source_path.resolve().as_uri(),
        media_type="image/png",
        sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    )
    step = (
        StepBuilder("proofrelay-layout", "proof-card-v1")
        .prompt("Compose approved facts")
        .modality(Modality.IMAGE)
        .status(StepStatus.PROCESSING)
        .input_asset(
            source.url,
            source.media_type,
            sha256=source.sha256,
        )
        .build()
    )

    result = ProofCardProvider(incident, tmp_path).generate(step)
    card = Path(result.assets[0].url.removeprefix("file://")).read_text(
        encoding="utf-8"
    )

    assert incident.title in card
    assert incident.location in card
    assert "data:image/png;base64," in card
    assert "DETERMINISTIC FACTUAL OVERLAY" in card
    assert result.assets[0].sha256 == hashlib.sha256(card.encode()).hexdigest()
