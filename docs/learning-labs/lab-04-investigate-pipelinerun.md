# Lab 04 — Investigate PipelineRun

## Objective

Drill into a **docker-build** PipelineRun for `brewspace-api`: list every **TaskRun**, explain what each task does in Jenkins terms, and understand the **generated image** (URL, digest, tags)—the artifact you promote and deploy, not a workspace tarball.

## Prerequisites

- [Lab 03](lab-03-trigger-first-build.md): at least one **Succeeded** (or **Failed**) `brewspace-api` PipelineRun.
- `oc` access to tenant namespace.

## Jenkins → Konflux framing

| Jenkins stage (conceptual) | Tekton task (brewspace-api push pipeline) |
|----------------------------|-------------------------------------------|
| Checkout | `init`, `clone-repository` |
| Cache/warmup | `init` (cache proxy) |
| Dependency prep | `prefetch-dependencies` |
| `docker build` | `build-container`, `build-image-index` |
| Publish metadata | `push-dockerfile`, `apply-tags` |
| Source archive (optional) | `build-source-image` |
| Security scans | `clair-scan`, `clamav-scan`, `sast-*`, … |
| Compliance | `deprecated-base-image-check`, `ecosystem-cert-preflight-checks`, `rpms-signature-scan` |

---

## Step-by-step instructions

### 1. Select a PipelineRun

```bash
export NS=<tenant-namespace>
export PR=$(oc get pipelinerun -n $NS \
  -l appstudio.openshift.io/component=brewspace-api \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "PipelineRun: $PR"
```

### 2. Find all TaskRuns

```bash
oc get taskrun -n $NS -l tekton.dev/pipelineRun=$PR \
  -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[0].reason,START:.status.startTime
```

UI: open the PipelineRun → **Tasks** graph (parallel columns after `build-image-index`).

### 3. Walk the task graph in order

Use this table while reading logs for each TaskRun.

| Task name | Purpose (Konflux) | Jenkins analogy |
|-----------|-------------------|-----------------|
| **init** | Prepare cache proxy settings | Pre-build agent setup |
| **clone-repository** | Clone Git at `revision` into OCI artifact | `checkout scm` |
| **prefetch-dependencies** | Prefetch deps (cachi2) for hermetic builds | `npm ci` / `pip download` cache stage |
| **build-container** | Buildah builds image from `Containerfile` + context | `docker build` |
| **build-image-index** | Assemble/publish image index; exposes digest results | `docker push` + manifest list |
| **build-source-image** | Optional source image (if enabled) | Archive sources artifact |
| **deprecated-base-image-check** | Policy: base image not deprecated | Custom compliance stage |
| **clair-scan** | Vulnerability scan (Clair) | Sonatype/Clair plugin |
| **ecosystem-cert-preflight-checks** | Red Hat ecosystem certification checks | Vendor policy gate |
| **sast-snyk-check** | SAST via Snyk | Security stage |
| **clamav-scan** | Malware scan | AV scan stage |
| **sast-shell-check** | Shell script SAST | Extra security |
| **sast-unicode-check** | Unicode bidirectional attack check | Security lint |
| **apply-tags** | Apply OCI tags to pushed image | Retag `latest` / promote tag |
| **push-dockerfile** | Push Dockerfile metadata for transparency | Archive Dockerfile |
| **rpms-signature-scan** | RPM signature validation | Compliance |

Many scan tasks run **after** `build-image-index` with `when: skip-checks == false`.

### 4. Inspect build-container (core learning)

```bash
TR=$(oc get taskrun -n $NS -l tekton.dev/pipelineRun=$PR -o name | grep build-container | head -1)
oc logs -n $NS $TR -c step-build
```

Confirm params in PipelineRun spec:

- `dockerfile`: `applications/brewspace/components/api/Containerfile`
- `path-context`: `applications/brewspace/components/api`
- `output-image`: `quay.io/redhat-user-workloads/<tenant>/brewspace-api:<sha>`

### 5. Explain the generated image

Read PipelineRun results:

```bash
oc get pipelinerun $PR -n $NS -o jsonpath='{range .status.results[*]}{.name}={.value}{"\n"}{end}'
```

| Concept | Meaning |
|---------|---------|
| **IMAGE_URL** | Quay repository URL (may include tag = git SHA) |
| **IMAGE_DIGEST** | Immutable `sha256:...` — **this** is what Snapshots store |
| **Tag = revision** | Convenient human pointer; **not** what you trust for promotion |

**Jenkins habit to unlearn:** “deploy `myapp:latest` from last green build.”  
**Konflux habit:** “deploy `myapp@sha256:<digest>` from Snapshot that passed tests.”

Verify in Quay UI (if access): repository `brewspace-api` shows tag and digest.

### 6. Trusted artifacts note

Pipeline description references **OCI artifacts** between tasks (not Jenkins workspace). Source flows: clone → prefetch → buildah as chained artifacts—supports Enterprise Contract **trusted_task** policy.

### 7. Document one failure path (optional)

Re-run mentally: if `clair-scan` fails, image may exist but Snapshot/policy blocks promotion. In Jenkins you might still deploy; Konflux default posture is stricter.

---

## Expected Konflux UI view

| View | What you see |
|------|----------------|
| Pipeline run graph | DAG: linear early tasks, fan-out scans after image build |
| Task: build-container | Longest step; Buildah output |
| Task: clair-scan | CVE report link or log summary |
| Results panel | `IMAGE_URL`, `IMAGE_DIGEST` |
| Component page | Same digest as “latest build” |

### Expected UI screenshots

| # | Filename | Capture |
|---|----------|---------|
| 1 | `10-task-graph.png` | Full task DAG |
| 2 | `11-build-container-log.png` | Successful buildah push |
| 3 | `12-results-digest.png` | Pipeline results with sha256 |

---

## Expected Tekton resources

| Kind | Naming pattern |
|------|----------------|
| `PipelineRun` | `brewspace-api-on-push-*` |
| `TaskRun` | `<pipelinerun>-<task>-*` |
| `Pod` | One pod per TaskRun (check `oc get pods -n $NS \| grep $PR`) |
| `ServiceAccount` | `build-pipeline-brewspace-api` on taskRunTemplate |
| Bundles | Tasks from `quay.io/konflux-ci/tekton-catalog/...` |

Example:

```bash
oc get pipelinerun,taskrun,pod -n $NS | grep brewspace-api-on-push
```

---

## Troubleshooting

| Symptom | Task to inspect | Notes |
|---------|-----------------|-------|
| Failed at clone | `clone-repository` | PAT/token, `git-auth` secret |
| Failed at prefetch | `prefetch-dependencies` | Python requirements; proxy |
| Failed at build | `build-container` | Containerfile, base image pull |
| Failed at scan | `clair-scan`, `sast-*` | Policy may fail PR; ask admin for waiver process |
| No IMAGE_DIGEST | Pipeline cancelled early | Pipeline did not reach `build-image-index` |
| Too many tasks vs diagram | Full docker-build bundle | Educational slim pipeline: `pipelines/brewspace-pipeline.yaml` |

---

## Quiz questions

1. Which task produces the authoritative **IMAGE_DIGEST** used downstream?

2. **Short answer:** Why are there multiple SAST tasks instead of one “security” stage?

3. What is the difference between the image **tag** (`{{revision}}`) and **digest** in promotion?

4. **Map:** `clone-repository` TaskRun ≈ which Jenkins plugin/stage?

5. **Scenario:** `build-container` succeeded but PipelineRun **Failed**. List two tasks that could still cause failure.

6. **Reflection:** Which scan task would you inspect first for a Python Flask API CVE report?

---

## Next lab

→ [Lab 05 — Understand Snapshots](lab-05-understand-snapshots.md)
