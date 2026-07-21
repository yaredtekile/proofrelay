# ProofRelay - Backblaze Generative Media Hackathon submission

## One-line pitch

ProofRelay turns human-approved field evidence into multilingual media briefs
with a hash-verifiable provenance trail for every generated asset.

## Tagline

**Make the update. Keep the proof.**

## Submission links

- Working app: **pending public deployment**
- Source repository: **https://github.com/yaredtekile/proofrelay**
- Demo video: **pending final live pipeline recording**
- Genblaze feedback issue: **https://github.com/backblaze-labs/genblaze/issues/172**

## Inspiration

Field teams often capture important evidence in camera rolls, chat threads, and
paper notes. When that evidence becomes a donor update, public advisory, or
maintenance briefing, the communication process can lose its audit trail. AI
makes media production faster, but it can also blur the line between a verified
fact and a generated visual.

ProofRelay was built to preserve that line. It combines an AI-generated
illustration with exact, human-approved wording through a deterministic layout
step. The source approval, generation provider, model, prompt, asset hashes, and
final publication approval remain inspectable in one provenance workflow.

## What it does

1. Accepts an incident report that has already passed a human source review.
2. Generates a respectful, non-identifying contextual illustration without
   text, logos, faces, or invented people.
3. Feeds that asset into a second Genblaze provider that adds the exact approved
   title, summary, location, audience, severity, and provenance notice.
4. Stores generated assets and the canonical manifest in Backblaze B2.
5. Verifies the manifest and asset SHA-256 before presenting the result.
6. Requires a separate human decision before recording the media as approved
   for publication.

The credential-free demo path also works locally. It generates a briefing card,
creates a Genblaze manifest, and verifies the asset hash without pretending that
a live model or B2 call occurred.

## How we built it

- **Genblaze** orchestrates the media pipeline and creates the canonical
  provenance manifest.
- **OpenAI GPT Image 2** generates the contextual illustration in the live path.
- **ProofCardProvider**, a custom deterministic Genblaze provider, composes the
  illustration with human-approved factual text.
- **Backblaze B2** is the durable object store for illustrations, final media,
  manifests, and content hashes.
- **FastAPI and Pydantic** enforce the server contract and validated report
  schema.
- **Vanilla HTML, CSS, and JavaScript** provide a fast editorial proof-desk
  interface.
- **Docker** packages the app for a reproducible public deployment.

The live pipeline is deliberately two-step. The generative model is never asked
to reproduce incident facts or typography. That separation makes it possible to
change the art provider without changing the approved wording.

## AI providers and models

- OpenAI `gpt-image-2` through Genblaze `DalleProvider`
- ProofRelay `proof-card-v1` deterministic composition provider

The provider list will be updated if a fallback model is added before the final
submission.

## How Backblaze B2 is used

The live Genblaze run uses `S3StorageBackend.for_backblaze(...)` inside an
`ObjectStorageSink` with a hierarchical key strategy. B2 receives:

- the original generated illustration;
- the final composed briefing card;
- the canonical Genblaze manifest;
- asset SHA-256 and size metadata; and
- the durable, credential-free asset URLs returned to the application.

This is not a decorative upload at the end of the demo. Storage is part of the
media chain: the final application reads the B2-backed asset URL and exposes the
manifest URL for inspection before publication approval.

## Challenges we ran into

The main design challenge was preventing generated media from quietly becoming
the source of truth. Asking an image model to render exact incident wording
would make factual accuracy and typography probabilistic. We solved this by
splitting generation and factual composition into separate Genblaze steps.

A second challenge was keeping the prototype honest when credentials are not
configured. The app fails closed for the live path and offers an explicitly
local proof flow instead of displaying simulated network results.

## Accomplishments we are proud of

- One manifest captures both the generative illustration and deterministic
  factual-composition steps.
- Every produced asset is SHA-256 covered and `Manifest.verify()` is tested.
- Publication approval is a separate persisted audit event.
- Untrusted incident text is escaped before it reaches SVG output.
- The complete web flow is browser-tested and packaged as a deployable wheel and
  Docker image.
- The product addresses a real communication need for NGOs, public
  infrastructure teams, and local newsrooms.

## What we learned

Media provenance becomes more useful when it shapes the product workflow rather
than living in hidden metadata. Users need to see when evidence was reviewed,
when AI generated an asset, whether the manifest verified, and whether a person
approved publication. Genblaze made those stages explicit enough to become the
interface itself.

## What's next

- Add a speech brief as a third Genblaze step for low-literacy and hands-free
  audiences.
- Support Amharic factual overlays with a bundled, openly licensed font.
- Add expiring reviewer links and organization-level approval policies.
- Store source-evidence hashes alongside generated-media hashes in B2.
- Add signed manifests or C2PA for adversarial verification environments.
- Pilot with field operations and nonprofit communications teams.

## Judging criteria mapping

### Real-world utility

ProofRelay helps teams publish timely updates without losing the distinction
between observed evidence and generated media. The target users already create
this content manually and have a clear reason to adopt a faster audited flow.

### Production readiness

The app validates inputs, escapes generated SVG content, fails closed when live
credentials are absent, records human approvals, exposes a health endpoint, has
automated tests, and ships with a production container.

### B2 storage and data orchestration

B2 stores every media stage and its manifest through the Genblaze object-storage
sink. Durable asset and manifest URLs drive the review screen.

### Use of Genblaze

Genblaze orchestrates two materially different media steps, propagates the first
asset into the second, captures provider/model/prompt/parameter lineage, uploads
outputs to B2, and verifies the resulting manifest.

## Demo video plan - target 2:35

### 0:00-0:18 - Problem

Show a field photo/report moving through disconnected chat messages. Explain:
"Teams need fast public updates, but AI-generated media can detach the message
from its evidence."

### 0:18-0:42 - Approved report intake

Open ProofRelay. Point out the incident title, verified summary, location,
severity, audience, and the named source reviewer.

### 0:42-1:15 - Genblaze pipeline

Generate the live bundle. Show the contextual illustration and explain that the
model is explicitly prevented from adding facts, people, logos, or text. Show
the deterministic second step applying the approved wording.

### 1:15-1:42 - B2 and provenance

Open the manifest. Highlight both steps, provider/model names, prompts, B2 URLs,
asset SHA-256 values, and the successful `Manifest.verify()` result.

### 1:42-2:03 - Human publication gate

Return to the proof desk. Click **Approve for publication** and show the audit
rail moving from evidence review through generation and verification to final
approval.

### 2:03-2:25 - Production path

Briefly show the Docker deployment, health endpoint, automated tests, and the B2
hierarchical run layout.

### 2:25-2:35 - Close

"ProofRelay makes generated communication fast without making trust optional.
Make the update. Keep the proof."

## Final checklist

- [x] Real local application flow
- [x] Genblaze canonical manifest generation
- [x] Two-step Genblaze media chain
- [x] SHA-256 verification
- [x] Separate publication approval event
- [x] Browser QA
- [x] Automated tests
- [x] Docker deployment package
- [ ] Backblaze account and B2 bucket
- [ ] Live OpenAI image generation run
- [ ] Verify final assets and manifest in B2
- [ ] Public deployment
- [x] Public source repository
- [x] Genblaze feedback issue
- [ ] Public demo video under three minutes
- [ ] Devpost registration and submission
