# Lab 01 — Create Application

## Objective

Create (or recognize) the Konflux **Application** `brewspace` and understand how it differs from a Jenkins folder or multibranch project. By the end you can name the Konflux objects that group components and explain what an Application does *not* do (it does not build code by itself).

## Prerequisites

- Access to Konflux / Red Hat Developer Hub and your **tenant namespace** (this repo’s PaC uses `sfathii-tenant`—substitute yours).
- `oc` logged in: `oc whoami` succeeds.
- Skimmed [Lab roadmap](README.md) and [Application model diagram](../diagrams/02-konflux-application-model.md).

## Jenkins → Konflux framing

| Jenkins | Konflux |
|---------|---------|
| Folder / organization | **Application** |
| Job | **Component** (Lab 02) |
| Build number | **PipelineRun** (Lab 03+) |

An Application is a **product boundary**, not a pipeline executor.

---

## What Konflux objects to create

| Object | API | Name for brewspace | Purpose |
|--------|-----|-------------------|---------|
| **Application** | `appstudio.redhat.com/v1alpha1` | `brewspace` | Groups components, snapshots, integration tests, releases |
| *(Later labs)* Component | `v1alpha1` | `brewspace-api`, `brewspace-frontend` | Lab 02 |
| *(Later labs)* IntegrationTestScenario | `v1beta1` | `brewspace-verify-*` | Lab 06 |
| **Pipeline-as-Code Repository** | PaC / `pipelinesascode` | Linked to `dno-automation-services` | Discovers `.tekton/` templates |

You typically create the Application via UI wizard or `kubectl`; this learning repo documents intent in Git under `applications/brewspace/`.

**Example Application manifest (reference):**

```yaml
apiVersion: appstudio.redhat.com/v1alpha1
kind: Application
metadata:
  name: brewspace
  namespace: <tenant-namespace>
spec:
  displayName: brewspace
```

---

## Step-by-step instructions

### 1. Confirm cluster context

```bash
oc config current-context
oc auth can-i create applications.appstudio.redhat.com -n <tenant-namespace>
```

If `no`, ask your platform admin for Konflux tenant access.

### 2. Create the Application (UI path)

1. Open **Konflux** / **Developer Hub** → **Applications**.
2. Choose **Create application** (wording may vary).
3. Set **Name:** `brewspace`.
4. Link the **Git repository** `dno-automation-services` (your fork URL if applicable).
5. Complete onboarding (namespace, secrets, PaC) per your org’s wizard.

### 3. Create the Application (CLI path)

If your tenant already has CRDs installed:

```bash
oc apply -f - <<EOF
apiVersion: appstudio.redhat.com/v1alpha1
kind: Application
metadata:
  name: brewspace
  namespace: <tenant-namespace>
spec:
  displayName: brewspace
EOF
```

### 4. Verify the Application exists

```bash
oc get application brewspace -n <tenant-namespace>
oc describe application brewspace -n <tenant-namespace>
```

### 5. Map to this repository

Read `applications/brewspace/README.md` and note: runtime Deployments live under `deploy/openshift/`, **not** in the tenant namespace.

---

## Expected Konflux UI view

Navigate: **Applications** → **brewspace**.

You should see:

| UI area | What to look for |
|---------|------------------|
| **Overview** | Application name `brewspace`, empty or growing component list |
| **Components** | Tab exists; may be empty until Lab 02 |
| **Integration tests** | Tab exists; scenarios appear after Lab 06 onboarding |
| **Activity** | May be empty until first PipelineRun |

### Expected UI screenshots (capture these yourself)

Save screenshots under `docs/learning-labs/screenshots/lab-01/` (create folder locally; not committed unless you choose).

| # | Filename suggestion | What to capture |
|---|---------------------|-----------------|
| 1 | `01-applications-list.png` | Applications list with `brewspace` row |
| 2 | `02-brewspace-overview.png` | Application overview / details header |
| 3 | `03-empty-components.png` | Components tab before Lab 02 (optional baseline) |

**Wireframe (overview page):**

```
┌─────────────────────────────────────────────────────────┐
│  Application: brewspace                    [Actions ▼]  │
├─────────────────────────────────────────────────────────┤
│  [Overview] [Components] [Integration tests] [Activity] │
├─────────────────────────────────────────────────────────┤
│  Display name: brewspace                                │
│  Git: github.com/.../dno-automation-services            │
│  Components: 0 (→ after Lab 02: 2)                      │
└─────────────────────────────────────────────────────────┘
```

---

## Expected Tekton resources

At Application-only stage:

| Resource | Present? |
|----------|----------|
| `Application` CR | Yes |
| `Component` CR | Not yet (Lab 02) |
| `PipelineRun` | Not yet |
| `TaskRun` | Not yet |

PaC may create a `Repository` CR pointing at your Git remote; that is not a Tekton pipeline yet.

```bash
oc get application,component,pipelinerun -n <tenant-namespace> | grep brewspace || true
```

---

## Questions to answer (worksheet)

Write answers in your notes before Lab 02.

1. What three things will eventually belong to Application `brewspace` in this repo?
2. Why is `brewspace` **not** equivalent to a Jenkins job?
3. Which namespace hosts Application metadata vs runtime Pods for brewspace?
4. Where in Git is the human-readable description of the app layout?
5. What happens if you delete the Application CR but leave Quay images?

---

## Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Cannot create Application | Missing RBAC in tenant | Request `Application` create on tenant namespace |
| Application exists but no Git link | Incomplete onboarding | Re-run import/wizard; verify PaC webhook |
| Duplicate name error | App already created | `oc get application brewspace`; reuse instead of recreate |
| UI shows different namespace | Wrong cluster/context | `oc config get-contexts` |

---

## Quiz questions

1. **Multiple choice:** An Application primarily…  
   - A) Builds container images  
   - B) Groups components and coordinates snapshots  
   - C) Replaces Kubernetes Deployment  
   - **Answer:** B

2. **Short answer:** In Jenkins you might use a folder `brewspace/` with jobs `api` and `frontend`. What are the Konflux names for the folder and jobs?

3. **True/false:** Deleting an Application automatically deletes all images in Quay.  
   **Answer:** False

4. **Scenario:** A teammate says “trigger the brewspace application build.” What do you correct them to say?

5. **Reflection:** What is one thing you currently configure in Jenkins job settings that Konflux will put in Git (Lab 02–03)?

---

## Next lab

→ [Lab 02 — Create Components](lab-02-create-components.md)
