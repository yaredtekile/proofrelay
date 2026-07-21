const form = document.querySelector("#brief-form");
const formStatus = document.querySelector("#form-status");
const emptyState = document.querySelector("#empty-state");
const resultState = document.querySelector("#result-state");
const proofBadge = document.querySelector("#proof-badge");
const approveButton = document.querySelector("#approve-button");
let currentRunId = null;

function shortHash(value) {
  return `${value.slice(0, 15)}…${value.slice(-8)}`;
}

function setRail(id, complete = true) {
  document.querySelector(id).classList.toggle("complete", complete);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button[type='submit']");
  const data = new FormData(form);
  const incident = Object.fromEntries(data.entries());
  incident.incident_id = `PR-${Date.now()}`;
  incident.approved_at = new Date().toISOString();

  button.disabled = true;
  button.querySelector("span").textContent = "Building provenance…";
  formStatus.textContent = "Rendering asset · hashing bytes · signing manifest";

  try {
    const response = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(incident),
    });
    if (!response.ok) throw new Error(`Preview failed (${response.status})`);
    const result = await response.json();
    currentRunId = result.run_id;

    document.querySelector("#asset-preview").src = `${result.asset_url}?v=${Date.now()}`;
    document.querySelector("#asset-hash").textContent = shortHash(result.asset_sha256);
    document.querySelector("#asset-hash").title = result.asset_sha256;
    document.querySelector("#manifest-hash").textContent = shortHash(result.manifest_hash);
    document.querySelector("#manifest-hash").title = result.manifest_hash;
    document.querySelector("#verify-state").textContent = result.manifest_verified ? "TRUE ✓" : "FAILED";
    document.querySelector("#publication-state").textContent = "Awaiting approval";
    document.querySelector("#download-link").href = result.asset_url;
    document.querySelector("#manifest-link").href = result.manifest_url;

    approveButton.disabled = false;
    approveButton.innerHTML = "Approve for publication <b>✓</b>";
    emptyState.hidden = true;
    resultState.hidden = false;
    proofBadge.textContent = "VERIFIED";
    proofBadge.className = "proof-badge ready";
    setRail("#rail-generated");
    setRail("#rail-verified", result.manifest_verified);
    setRail("#rail-approved", false);
    formStatus.textContent = "Bundle complete. A second human approval is still required.";
  } catch (error) {
    formStatus.textContent = error.message;
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "Generate proof bundle";
  }
});

approveButton.addEventListener("click", async () => {
  if (!currentRunId) return;
  const reviewer = new FormData(form).get("approved_by");
  approveButton.disabled = true;
  approveButton.textContent = "Recording approval…";

  try {
    const response = await fetch(`/api/runs/${currentRunId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer, note: "Approved for publication after media review" }),
    });
    if (!response.ok) throw new Error(`Approval failed (${response.status})`);
    document.querySelector("#publication-state").textContent = "Approved ✓";
    proofBadge.textContent = "APPROVED";
    proofBadge.className = "proof-badge approved";
    approveButton.innerHTML = "Publication approval recorded <b>✓</b>";
    setRail("#rail-approved");
    formStatus.textContent = "Approval recorded in the run audit trail.";
  } catch (error) {
    approveButton.disabled = false;
    approveButton.textContent = "Try approval again";
    formStatus.textContent = error.message;
  }
});
