# Lab 02 — Create Components

## Objective

Register two Konflux **Components**—`brewspace-api` and `brewspace-frontend`—each with its own source context, Containerfile, and image destination. Internalize: **one component = one buildable unit = one image lineage**, not one stage in a shared Jenkinsfile.

## Prerequisites

- [Lab 01](lab-01-create-application.md) complete: Application `brewspace` exists.
- Git repo contains:
  - `applications/brewspace/components/api/`
  - `applications/brewspace/components/frontend/`
- PaC templates present: `.tekton/brewspace-api-push.yaml`, `.tekton/brewspace-frontend-push.yaml`.

## Jenkins → Konflux framing

| Jenkins pattern | Konflux pattern in brewspace |
|-----------------|------------------------------|
| `when { changeset "api/**" }` | PaC CEL `pathChanged()` per component |
| `dir('api') { docker.build() }` | Component `source.git.context` |
| One job builds two images | **Two Components**, two PipelineRuns |

---

## API component

### Reference manifest

File: `applications/brewspace/components/api/component.yaml`

| Field | Expected value (learning repo) | Your environment |
|-------|------------------------------|------------------|
| `metadata.name` | `brewspace-api` | Same |
| `spec.application` | `brewspace` | Same |
| `spec.componentName` | `brewspace-api` | Same |
| `spec.source.git.context` | `applications/brewspace/components/api` | Must match repo path |
| `spec.containerImage` | `quay.io/example-org/brewspace-api` | `quay.io/redhat-user-workloads/<tenant>/brewspace-api` |
| Annotation `build.appstudio.openshift.io/pipeline` | `docker-build` | Konflux default image pipeline |

### Source layout

```
applications/brewspace/components/api/
├── component.yaml
├── Containerfile
├── requirements.txt
└── src/app.py          # GET /health → {"status":"ok"}
```

---

## Frontend component

### Reference manifest

File: `applications/brewspace/components/frontend/component.yaml`

| Field | Expected value |
|-------|----------------|
| `metadata.name` | `brewspace-frontend` |
| `spec.application` | `brewspace` |
| `spec.source.git.context` | `applications/brewspace/components/frontend` |
| `spec.containerImage` | `quay.io/.../brewspace-frontend` |
| Pipeline annotation | `docker-build` |

### Source layout

```
applications/brewspace/components/frontend/
├── component.yaml
├── Containerfile
├── index.html          # fetches /health, shows "API Status: OK"
└── nginx-default.conf  # proxies /health → brewspace-api:8080 at runtime
```

---

## Step-by-step instructions

### 1. Review Git manifests

```bash
cd applications/brewspace/components/api
cat component.yaml Containerfile

cd ../frontend
cat component.yaml Containerfile
```

Update `spec.source.git.url` to your fork if not using the example org URL.

### 2. Create API component (UI)

1. **Applications** → **brewspace** → **Create component** (or **Add component**).
2. **Name:** `brewspace-api`
3. **Source context:** `applications/brewspace/components/api`
4. **Containerfile path:** `Containerfile` (relative to context)
5. **Pipeline:** `docker-build` (or platform default for container builds)
6. **Image:** `quay.io/redhat-user-workloads/<tenant>/brewspace-api`

### 3. Create frontend component (UI)

Repeat with:

- **Name:** `brewspace-frontend`
- **Context:** `applications/brewspace/components/frontend`
- **Image:** `.../brewspace-frontend`

### 4. Create components (CLI)

```bash
oc apply -f applications/brewspace/components/api/component.yaml -n <tenant-namespace>
oc apply -f applications/brewspace/components/frontend/component.yaml -n <tenant-namespace>
```

Fix `namespace` in YAML or use `-n` as shown.

### 5. Confirm PaC labels align

Open `.tekton/brewspace-api-push.yaml` and verify labels:

```yaml
appstudio.openshift.io/application: brewspace
appstudio.openshift.io/component: brewspace-api
pipelines.appstudio.openshift.io/type: build
```

Frontend push template uses `brewspace-frontend`.

### 6. Expected Component settings (checklist)

| Setting | brewspace-api | brewspace-frontend |
|---------|---------------|------------------|
| Application | brewspace | brewspace |
| Build pipeline | docker-build | docker-build |
| Source context | `.../components/api` | `.../components/frontend` |
| Dockerfile/Containerfile | `Containerfile` in context | `Containerfile` in context |
| Output registry | `quay.io/redhat-user-workloads/<tenant>/...` | same pattern |
| PR template | `.tekton/brewspace-api-pull-request.yaml` | `.tekton/brewspace-frontend-pull-request.yaml` |
| Push template | `.tekton/brewspace-api-push.yaml` | `.tekton/brewspace-frontend-push.yaml` |

---

## Expected Konflux UI view

**Applications** → **brewspace** → **Components**

| Component | UI fields to verify |
|-----------|---------------------|
| brewspace-api | Context path, last build (none yet), pipeline type, pull spec placeholder |
| brewspace-frontend | Same |

### Expected UI screenshots

| # | Filename | Capture |
|---|----------|---------|
| 1 | `04-components-list.png` | Both components listed under brewspace |
| 2 | `05-api-component-detail.png` | API source context + pipeline |
| 3 | `06-frontend-component-detail.png` | Frontend source context + pipeline |

---

## Expected Tekton resources

| Resource | Name / label |
|----------|----------------|
| `Component` | `brewspace-api`, `brewspace-frontend` |
| `ServiceAccount` | Often `build-pipeline-brewspace-api` (created by Konflux) |
| `PipelineRun` | None until Lab 03 |
| PaC `Repository` | Links `.tekton/` to Git events |

```bash
oc get component -n <tenant-namespace> -l appstudio.openshift.io/application=brewspace
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Component build uses wrong directory | Context path typo | Match `applications/brewspace/components/<name>` exactly |
| Only one component appears | Second create skipped | Add frontend explicitly |
| Pipeline not docker-build | Wrong annotation | Set `build.appstudio.openshift.io/pipeline: docker-build` |
| PaC does not trigger | Repository not configured | Complete PaC onboarding for the Git repo |
| Image push 403 | Quay path mismatch | Align `output-image` in `.tekton` with component image repo |

---

## Quiz questions

1. How many **images** does brewspace produce per successful full application build?

2. What PaC path filter triggers API builds on push to `main`? (Hint: read `on-cel-expression` in `.tekton/brewspace-api-push.yaml`.)

3. **Short answer:** Why should API and frontend be separate Components instead of one Component with two Containerfiles?

4. **Match:** Map Jenkins concept → Konflux  
   - Multibranch path filter → ?  
   - `docker.build('myimg')` → ?  
   - Job name → ?

5. **Scenario:** You change only `index.html`. Which Component build should run?

---

## Next lab

→ [Lab 03 — Trigger First Build](lab-03-trigger-first-build.md)
