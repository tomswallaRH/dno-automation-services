# Lab 05 — Understand Snapshots

## Objective

Observe **Snapshot** creation for Application `brewspace`, explain why Snapshots exist, and compare them to Jenkins artifacts and “last green build” semantics.

## Prerequisites

- [Lab 03](lab-03-trigger-first-build.md) and [Lab 04](lab-04-investigate-pipelinerun.md) complete.
- **Both** components have successful push builds (run Lab 03 for frontend if needed).
- Read [Snapshot diagram](../diagrams/02-konflux-application-model.md).

## Jenkins → Konflux framing

| Jenkins | Konflux Snapshot |
|---------|------------------|
| `archiveArtifacts '**/target/*.jar'` | Not used—images live in Quay |
| `lastSuccessfulBuild` + copied WAR | **Snapshot** records digests for all components |
| Mutable `BUILD_NUMBER` tag | Immutable `sha256` per component in Snapshot |
| “What did we test?” (often unclear) | Snapshot is explicit application state |

---

## Step-by-step instructions

### 1. Ensure two component digests exist

```bash
export NS=<tenant-namespace>
for C in brewspace-api brewspace-frontend; do
  echo "=== $C ==="
  oc get pipelinerun -n $NS -l appstudio.openshift.io/component=$C \
    --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].status.results}{"\n"}' 2>/dev/null | head -5
done
```

Note each `IMAGE_DIGEST`.

### 2. Observe Snapshot creation (UI)

1. **Applications** → **brewspace** → **Snapshots** (or **Overview** snapshot section).
2. Open the **latest** Snapshot.
3. Verify it lists:
   - `brewspace-api` → `sha256:...`
   - `brewspace-frontend` → `sha256:...`

Timing: Snapshots appear after Konflux controllers correlate successful component builds for the same application revision window—not necessarily the instant a single PipelineRun finishes.

### 3. Observe Snapshot creation (CLI)

```bash
oc get snapshots.appstudio.redhat.com -n $NS 2>/dev/null || \
oc get snapshot -n $NS

SNAP=$(oc get snapshot -n $NS -o jsonpath='{.items[-1].metadata.name}')
oc get snapshot $SNAP -n $NS -o yaml | less
```

Look for `spec.components` or status fields referencing container images and digests (exact schema varies by Konflux version).

### 4. Explain why Snapshots exist

Write this explanation in your own words:

1. **Immutability:** A Snapshot pins exact digests—re-tagging Quay does not change what was tested.
2. **Application-level truth:** brewspace is two images; the Snapshot is one “release candidate” object.
3. **Integration input:** Integration Service runs scenarios **against** Snapshot content (Lab 06).
4. **Promotion gate:** Release/plan admission uses tested Snapshot, not “whatever :latest is” (Lab 07).
5. **Audit:** Answers “which API digest paired with which frontend digest for test run X?”

### 5. Compare to Jenkins artifacts

| Question | Jenkins typical answer | Konflux answer |
|----------|------------------------|----------------|
| Where is the artifact? | Controller archive or external storage | Quay; Snapshot holds references |
| How do you reproduce a test? | Re-run job on old SHA (maybe) | Re-run integration on same Snapshot digests |
| Can someone change artifact after test? | Replace stored JAR or retag image | Digest unchanged; new tag ≠ new digest |
| Multi-module repo | One archive with many files | One Snapshot with many component digests |

### 6. Connect to Git commit

Correlate Snapshot to Git:

- PipelineRun annotation `build.appstudio.redhat.com/commit_sha`
- Image tag often equals commit SHA in PaC `output-image`

Ask: “If I check out this Git SHA and rebuild, do I get the same digest?” (Hermetic builds: should be reproducible; still verify digest not tag.)

### 7. Optional: read educational pipeline comment

`applications/brewspace/pipelines/brewspace-pipeline.yaml` task `summarize-for-snapshot` documents human-readable digest summary—controllers still create the real Snapshot CR.

---

## Expected Konflux UI view

| UI area | Expected content |
|---------|------------------|
| Snapshots list | Rows with timestamp, pass/fail indicators for tests (after Lab 06) |
| Snapshot detail | Table: Component name → image@sha256 |
| Application overview | “Current” or “Latest” snapshot reference |

### Expected UI screenshots

| # | Filename | Capture |
|---|----------|---------|
| 1 | `13-snapshots-list.png` | Multiple snapshots over time |
| 2 | `14-snapshot-components.png` | Both brewspace digests in one snapshot |
| 3 | `15-snapshot-test-status.png` | Integration status column (after Lab 06) |

---

## Expected Tekton resources

Snapshots are **not** PipelineRuns; they are Konflux CRs fed by build outcomes.

| Resource | Role |
|----------|------|
| `Snapshot` | Application state = set of component digests |
| `PipelineRun` (build) | Produces digests consumed into Snapshot |
| Labels/annotations | Link builds → snapshot assembly (controller-managed) |

```bash
oc get snapshot -n $NS -o wide
oc describe snapshot $SNAP -n $NS
```

Integration PipelineRuns (Lab 06) reference Snapshot in labels/params.

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| No Snapshot | Only one component built | Complete frontend + api builds on same app |
| Snapshot missing a component | One build failed or old | Re-run failed component PipelineRun |
| Duplicate snapshots | Each push pair | Normal; compare digests across entries |
| UI empty, builds green | RBAC or UI cache | Verify with `oc get snapshot` |
| Digest mismatch vs Quay | Looking at tag not digest | Use `sha256` from PipelineRun results |

---

## Quiz questions

1. **Short answer:** What problem does a Snapshot solve that two separate “green” Jenkins jobs do not?

2. Can a Snapshot exist with only `brewspace-api` digest if frontend build never ran?

3. **True/false:** Changing a Quay tag to point at a new digest updates an existing Snapshot’s meaning.  
   **Answer:** False (Snapshot holds original digests)

4. **Scenario:** QA asks “what exactly did we test yesterday?” What object do you show them?

5. **Compare:** Jenkins archived `app.war` vs brewspace Snapshot—what is the deployable unit for each?

6. **Reflection:** Where would you store “pairing” of api+frontend versions in Jenkins without Snapshots?

---

## Next lab

→ [Lab 06 — Integration Tests](lab-06-integration-tests.md)
