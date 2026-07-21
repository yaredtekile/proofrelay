# ProofRelay

[![Test ProofRelay](https://github.com/yaredtekile/proofrelay/actions/workflows/test.yml/badge.svg)](https://github.com/yaredtekile/proofrelay/actions/workflows/test.yml)

**Verified evidence in. Publishable media out.**

ProofRelay turns an approved field report into a multilingual media brief while
preserving the provenance of every generated asset. It is designed for NGOs,
public-infrastructure teams, local newsrooms, and other organizations that need
to communicate quickly without losing the line between evidence and AI output.

This repository is the working prototype for the **Backblaze Generative Media
Hackathon**. The final product will use Genblaze to orchestrate image and audio
generation and Backblaze B2 to store source evidence, generated assets, and
their hash-verifiable manifests.

## Product flow

1. Import an already reviewed incident report.
2. Select audience, language, and publication channel.
3. Generate a visual briefing card and spoken update.
4. Store the assets and Genblaze provenance manifest in Backblaze B2.
5. Require a human approval before an asset can be marked publishable.
6. Let recipients verify the asset hash and inspect how it was produced.

## What works now

The first vertical slice is intentionally credential-free. It creates a real
SVG briefing card, records it as a Genblaze image-generation step, writes a
canonical manifest, and verifies the asset SHA-256. This makes the provenance
contract testable before any paid model or storage credentials are added.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

proofrelay build examples/incident.json --output build/demo
pytest
```

Run the complete local web experience:

```bash
proofrelay-web
```

Open `http://127.0.0.1:8000`. The interface implements report intake, media
generation, manifest verification, asset download, and a separate publication
approval event with an audit record.

## Deploy

The repository includes a production Docker image and a Render Blueprint. The
credential-free proof flow works immediately; adding the server-side OpenAI and
B2 variables enables the live generation pipeline.

```bash
docker build -t proofrelay .
docker run --rm -p 8000:8000 proofrelay
```

The container exposes `/health` for deployment checks and stores ephemeral demo
runs under `/tmp/proofrelay-runs`. Production deployments should rely on B2 for
durable assets and manifests.

The command writes:

- `brief.svg` — the generated media asset
- `manifest.json` — the canonical Genblaze provenance record
- `bundle.json` — a compact index for the application UI

When the required secrets are available, the live path uses the current OpenAI
image model through Genblaze, feeds that output into a second deterministic
Genblaze composition step, and writes the final factual SVG plus the complete
two-step manifest to Backblaze B2:

```bash
proofrelay generate-live examples/incident.json --output build/live
```

## Production path

The next integration replaces the deterministic preview step with a Genblaze
provider pipeline and passes the completed run to `ObjectStorageSink` backed by
`S3StorageBackend.for_backblaze(...)`. Credentials stay server-side:

```text
B2_KEY_ID=
B2_APP_KEY=
B2_BUCKET=
OPENAI_API_KEY=
```

No media is published automatically. Generation and approval remain separate
events in the audit trail.

The AI model is never responsible for rendering incident facts. It produces an
illustration without people, logos, or text. `ProofCardProvider` then adds the
exact reviewed wording and provenance notice as a deterministic second step, so
judges can inspect both operations in the same manifest.

## Why this is commercially useful

Many teams already have field evidence but lack a fast, trusted way to turn it
into donor updates, public advisories, or internal briefings. ProofRelay can be
sold internationally as a per-workspace subscription with usage-based media
generation and storage, while the open provenance format reduces vendor lock-in.

## Status

- Contest deadline: August 3, 2026 at 5:00 PM EDT
- Prize pool: $10,000 cash
- Eligibility: international adults, subject to the official exclusions
- Current milestone: provenance-first media bundle generator
- Genblaze integration feedback: [backblaze-labs/genblaze#172](https://github.com/backblaze-labs/genblaze/issues/172)
