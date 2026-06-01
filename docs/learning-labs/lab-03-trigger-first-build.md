# Lab 03 — Trigger First Build

## Objective

Trigger a real **build PipelineRun** by changing component code and pushing to Git. Observe how Pipeline-as-Code (PaC) creates Tekton objects—not how a Jenkins controller polls or receives a generic webhook without Git context.

## Prerequisites

- [Lab 01](lab-01-create-application.md) and [Lab 02](lab-02-create-components.md) complete.
- PaC webhook configured for your fork (push + pull_request).
- Write access to Git branch `main` (or use a PR first with `brewspace-api-pull-request.yaml`).

## Jenkins → Konflux framing

| Jenkins | Konflux (this lab) |
|---------|-------------------|
| `git push` → webhook → **Build #N** | `git push` → PaC → **PipelineRun** `brewspace-api-on-push` |
| Console log per stage | PipelineRun → TaskRuns in OpenShift |
| Built JAR/WAR in workspace | Image in Quay at `@sha256:...` |

---

## Step-by-step instructions

### 1. Choose a component to exercise

Start with **API** (simpler runtime surface). Frontend is identical flow with different paths.

### 2. Make a code change

Edit `applications/brewspace/components/api/src/app.py`—add a harmless field to the health JSON:

```python
return jsonify({
    'status': 'ok',
    'service': 'brewspace-api',
    'lab': '03-first-build',
}), 200
```

Or add a comment in `app.py` if you prefer zero behavior change.

### 3. Commit and push to `main`

```bash
git checkout main
git add applications/brewspace/components/api/src/app.py
git commit -m "lab-03: trigger brewspace-api build"
git push origin main
```

**Alternative (PR path):** open a PR that only touches `applications/brewspace/components/api/**` and watch `.tekton/brewspace-api-pull-request.yaml` fire instead of push.

### 4. Confirm PaC should trigger

Push template CEL (abbreviated) requires:

- `event == "push"`
- `target_branch == "main"`
- Path change under `applications/brewspace/components/api/***` OR Containerfile OR `.tekton/brewspace-api-push.yaml`

If you only changed `README.md` at repo root, **no API build** runs—that is intentional path filtering.

### 5. Observe PipelineRun (UI)

1. **Applications** → **brewspace** → **brewspace-api**
2. Open **Activity** or **Pipeline runs**
3. Find run named like `brewspace-api-on-push-<suffix>`
4. Watch status: `Running` → `Succeeded` (or `Failed`—go to Lab 04 troubleshooting)

### 6. Observe PipelineRun (CLI)

```bash
oc get pipelinerun -n <tenant-namespace> \
  -l appstudio.openshift.io/component=brewspace-api \
  --sort-by=.metadata.creationTimestamp

# Latest run details
PR=$(oc get pipelinerun -n <tenant-namespace> \
  -l appstudio.openshift.io/component=brewspace-api \
  --sort-by=.metadata.creationTimestamp -o name | tail -1)
oc describe $PR -n <tenant-namespace>
```

### 7. Record results

From PipelineRun status/results or UI:

- `IMAGE_URL`
- `IMAGE_DIGEST` (sha256:…)
- Duration and failed task (if any)

### 8. Optional: trigger frontend build

Change `applications/brewspace/components/frontend/index.html` (e.g. heading text), push, confirm `brewspace-frontend-on-push` runs.

---

## Expected Konflux UI view

| UI location | Expected state |
|-------------|----------------|
| Component **brewspace-api** | Latest pipeline run **Succeeded** (green) |
| Pipeline run detail | Task graph with `clone-repository`, `build-container`, scans, etc. |
| Logs tab | `build-container` shows push to Quay |
| Component summary | Pull spec shows image@sha256 |

### Expected UI screenshots

| # | Filename | Capture |
|---|----------|---------|
| 1 | `07-activity-running.png` | Pipeline run in progress |
| 2 | `08-activity-succeeded.png` | Green pipeline run |
| 3 | `09-image-digest.png` | IMAGE_DIGEST / pull spec on component |

---

## Expected Tekton resources

| Resource | Expected |
|----------|----------|
| `PipelineRun` | `brewspace-api-on-push` (generated name suffix) |
| Labels | `appstudio.openshift.io/application=brewspace`, `component=brewspace-api`, `pipelines.appstudio.openshift.io/type=build` |
| `TaskRun` | One per pipeline task (Lab 04 explores each) |
| Params | `output-image=quay.io/redhat-user-workloads/<tenant>/brewspace-api:<git-sha>` |
| Results | `IMAGE_URL`, `IMAGE_DIGEST` on PipelineRun |

```bash
oc get taskrun -n <tenant-namespace> --selector tekton.dev/pipelineRun=<pipelinerun-name>
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No PipelineRun after push | Path filter excluded your files | Touch path under `components/api/**` |
| No PipelineRun | Webhook/PaC not on fork | Configure PaC on your Git remote |
| PipelineRun **Failed** at clone | Git auth secret | Check `git-auth` workspace / PaC secret |
| PipelineRun **Failed** at build | Containerfile or deps | Read `build-container` TaskRun log |
| Wrong component built | Changed frontend files | Check labels on PipelineRun |
| PR build but not push | Expected on non-main | Merge to `main` for push template |

---

## Quiz questions

1. What three labels on a build PipelineRun identify application, component, and run type?

2. **Short answer:** Why does Konflux use path filters instead of building the whole repo on every commit?

3. If you push a change only to `.tekton/brewspace-api-push.yaml`, does the API build run? Why?

4. **Compare:** Jenkins `buildNow` vs Konflux trigger for brewspace-api—which is Git-native?

5. **Hands-on:** Write the `oc` command you used to list PipelineRuns for `brewspace-api`.

---

## Next lab

→ [Lab 04 — Investigate PipelineRun](lab-04-investigate-pipelinerun.md)
