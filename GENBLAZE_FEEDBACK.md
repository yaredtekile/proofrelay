# Genblaze feedback from building ProofRelay

**Project:** [ProofRelay](https://github.com/yaredtekile/proofrelay) turns a
human-approved field report into a publishable media brief while preserving a
hash-verifiable provenance trail.

**Tested packages:** `genblaze-core==0.3.4`, `genblaze-openai==0.3.2`, and
`genblaze-s3==0.3.4`.

## Workflow exercised

ProofRelay uses a two-step Genblaze pipeline:

1. `DalleProvider` with `gpt-image-2` generates a contextual illustration that
   is explicitly prohibited from rendering facts, text, faces, or logos.
2. A custom deterministic `SyncProvider` applies the exact human-approved
   title, summary, location, audience, reviewer, and provenance notice.
3. `ObjectStorageSink` is configured for Backblaze B2 with hierarchical keys.
4. A separate application event records the final human publication approval.

The credential-free path, custom provider, two-step manifest, asset hashes,
and publication gate are covered by automated tests. The live OpenAI/B2 wiring
is implemented but is not represented as executed without production
credentials.

## What worked well

- `input_from=0` made the generative-to-deterministic handoff explicit.
- A local deterministic `SyncProvider` could participate in the same manifest
  as the AI image provider. That made factual rendering auditable instead of a
  hidden post-processing step.
- `Manifest.verify()` provided a clean fail-closed gate before the review UI
  exposed the publication action.
- `KeyStrategy.HIERARCHICAL` removed most object-key design work from the B2
  integration.

## Highest-impact friction: business provenance metadata in the released API

ProofRelay needs to record `incident_id`, `human_approved`, `reviewer`, and the
approval policy as provenance metadata. These values describe the workflow;
they are not model parameters and should not be forwarded to an AI provider.

In the released `genblaze-core==0.3.4`, the public signature is:

```python
Pipeline.step(..., expected_duration_sec=None, **params)
```

It does not expose `metadata` or `prompt_visibility`. Passing either name is
silently treated as a provider parameter. ProofRelay therefore has to choose
between putting governance fields in the wrong namespace or maintaining a
separate side index that weakens the manifest as the audit artifact.

Issue #53 correctly identified this behavior, and the repository's current
main branch appears to contain the right fix: explicit step metadata,
`prompt_visibility`, and pipeline metadata. The remaining user-facing gap is
that the fix is not available in the released package used by hackathon
projects.

### Suggested release/documentation action

1. Publish the `Pipeline.step(metadata=..., prompt_visibility=...)` fix in a
   tagged `genblaze-core` release before the hackathon submission window ends,
   if release timing allows.
2. Add one migration example showing governance fields moving from `**params`
   into first-class provenance metadata:

```python
pipeline.metadata(workspace="proofrelay", workflow="field-briefing").step(
    provider,
    model="gpt-image-2",
    prompt=prompt,
    metadata={
        "incident_id": incident.incident_id,
        "human_approved": True,
        "reviewer": incident.approved_by,
    },
)
```

3. Call out that metadata is preserved in manifests but is not sent to the
   upstream model provider.

## Secondary friction: custom deterministic transformation providers

The custom `ProofCardProvider` works, but it has to implement its own safe
`file://` / `https://` input loading, output-file management, byte hashing, and
`Asset` construction. The repository already has internal helpers for similar
work in the FFmpeg providers, and issue #41 plus the feedback execution plan
recognize the duplication.

A short public recipe for an input-asset-to-output-bytes `SyncProvider`, backed
by shared `read_asset_bytes` and `emit_bytes` helpers, would make custom
deterministic steps both shorter and safer. These steps are important for
watermarks, exact factual overlays, redaction, and other transformations where
calling another generative model is the wrong abstraction.

## Reproduction and evidence

- Pipeline implementation:
  [`src/proofrelay/live_pipeline.py`](https://github.com/yaredtekile/proofrelay/blob/main/src/proofrelay/live_pipeline.py)
- Deterministic provider:
  [`src/proofrelay/compositor.py`](https://github.com/yaredtekile/proofrelay/blob/main/src/proofrelay/compositor.py)
- Tests:
  [`tests/test_pipeline.py`](https://github.com/yaredtekile/proofrelay/blob/main/tests/test_pipeline.py)

Thank you for making provenance a first-class pipeline artifact. The design made
it possible to keep generated illustration and approved factual communication
separate without losing their shared chain of custody.
