# CI/CD Flow Diagram

## Diagram

```mermaid
sequenceDiagram
    actor Dev as Developer
    participant Git as Git (push / PR)
    participant PaC as Pipeline-as-Code
    participant PR as PipelineRun (build)
    participant Tasks as Tekton Tasks
    participant Quay as Image Registry (Quay)
    participant KF as Konflux controllers
    participant Snap as Snapshot
    participant Int as Integration Service
    participant PRi as PipelineRun (integration)
    participant Pol as Enterprise Contract / policies
    participant Prom as Release / promotion
    participant OCP as OpenShift (deploy/)

    Dev->>Git: Commit to component path
    Git->>PaC: Webhook (push or PR)
    PaC->>PR: Create build PipelineRun<br/>(path filter e.g. components/api/***)

    PR->>Tasks: git-clone → buildah → scans
    Tasks->>Quay: Push image (tag + digest)
    Tasks-->>PR: Results IMAGE_URL, IMAGE_DIGEST

    Note over PR,Quay: Separate PipelineRuns per component<br/>(api and frontend)

    PR->>KF: Build succeeded + digest recorded
    KF->>Snap: Create/update Snapshot with digests

    Snap->>Int: Trigger IntegrationTestScenarios
    Int->>PRi: PipelineRun against Snapshot
    PRi->>PRi: verify-api / verify-frontend checks
    PRi-->>Snap: Test status (pass/fail)

    Snap->>Pol: Policy evaluation (trusted tasks, CVEs, etc.)
    Pol-->>Prom: Snapshot acceptable

    Prom->>Quay: Promote immutable digests (not :latest drift)
    Dev->>OCP: oc apply -k deploy/openshift<br/>(kustomize image digests)
    OCP->>Quay: Pull @sha256 into Pods
```

## Explanation

The brewspace CI/CD path starts when a developer pushes code or opens a PR. **Pipeline-as-Code** reads `.tekton/` templates, evaluates CEL path filters, and instantiates a **build PipelineRun** for the affected component. Tekton tasks clone source, build with Buildah, run checks, and push to **Quay**. Konflux records digests and forms a **Snapshot** representing one coherent application build. **Integration tests** run as separate PipelineRuns against that Snapshot. Policy gates (Enterprise Contract) must pass before **promotion**. Deployment in this repo is manual OpenShift apply using digests from Kustomize—Konflux builds and tests; `deploy/openshift/` runs the result.

## How this appears in Konflux UI

1. **Activity** after push: new Pipeline run on the component (Running → Succeeded/Failed).
2. **Component** page: latest image pull spec with digest.
3. **Application** → **Snapshots**: new entry when all required component builds complete.
4. **Integration tests**: runs linked to the Snapshot; green/red per scenario.
5. **Security / compliance** panels: task trust, vulnerability scan outcomes from build tasks.
6. **Release** (optional): promotion request from a passing Snapshot.

## How this maps to Tekton resources

| Stage | Tekton / K8s resources |
|-------|-------------------------|
| Git Push | PaC `Repository` CR; annotations on `PipelineRun` templates in `.tekton/` |
| Component Build | `PipelineRun` (`brewspace-api-on-push`, `brewspace-frontend-on-push`, PR variants) |
| Clone / build | `TaskRun` from bundles: `task-git-clone-oci-ta`, `task-buildah-oci-ta`, … |
| Image Registry | `PipelineRun` results + `build.appstudio.redhat.com` annotations; image written to `output-image` param |
| Snapshot | `Snapshot` CR; component status propagated from build PipelineRuns |
| Integration Tests | `PipelineRun` created by Integration Service; may reference Snapshot in params/labels |
| Promotion | `Release`, `ReleasePlan`, `ReleasePlanAdmission` (environment-specific; not in this learning repo) |
| Deployment | Standard `Deployment` / `Service` / `Route`—outside Tekton, applied via `kubectl`/`oc` |

**Path filter example (api push):** changes under `applications/brewspace/components/api/***` or `.tekton/brewspace-api-push.yaml` trigger `brewspace-api-on-push`.
