# Brewspace Deployment Readiness Review

**Reviewer role:** Principal Konflux and OpenShift Engineer  
**Application:** `brewspace`  
**Components:** `brewspace-api`, `brewspace-frontend`  
**Konflux tenant namespace:** `sfathii-tenant`  
**Repository:** `applications/brewspace`  
**Review date:** 2026-06-09  
**Cluster evidence:** Live `oc` queries against `sfathii-tenant` on `kflux-prd-rh02`

---

## Executive summary

Brewspace is **well-structured for deployment** at the manifest and application-design level, but it is **not deployable end-to-end today** in your tenant. The CI/CD control plane exists (Application, Components, PaC pipelines, Snapshots), yet three classes of blocker remain:

1. **No workload namespace** — `sfathii` cannot create `Deployment`, `Service`, or `Route` objects in `sfathii-tenant` (Konflux tenant namespaces are build/metadata only).
2. **Incomplete build artifacts** — `brewspace-api` has empty Component status; the latest Snapshot contains **frontend only**. A full two-component Snapshot last existed on 2026-05-06.
3. **Deploy manifests not wired to real digests** — Kustomize still references `:latest`, while Konflux publishes `:<git-sha>` tags. Manifests have never been applied to a runtime namespace.

The fastest path to `https://<route>` is: obtain a dev namespace → pin images from Snapshot `brewspace-20260506-115231-000` (or rebuild both components) → `oc apply -k` → verify frontend Route and `/health` proxy.

---

## Current cluster state (`sfathii-tenant`)

| Resource | Status |
|----------|--------|
| `Application/brewspace` | Exists (33d) |
| `Component/brewspace-api` | Exists; **status empty** (no `lastBuiltCommit` / `lastPromotedImage`) |
| `Component/brewspace-frontend` | Exists; `lastBuiltCommit: c0384da`, promoted image digest present |
| `PipelineRun` (build) | **None** currently in namespace |
| `Snapshot` | 4 total; latest `brewspace-20260530-083833-000` is **frontend-only** |
| `IntegrationTestScenario` | Only `brewspace-enterprise-contract` (auto-provisioned EC policy) |
| `Deployment` / `Service` / `Route` | **Cannot list** — RBAC denied in tenant namespace |

### Snapshot inventory

| Snapshot | Components | API digest | Frontend digest |
|----------|------------|------------|-----------------|
| `brewspace-20260506-100724-000` | frontend only | — | `sha256:0cf39929…` |
| `brewspace-20260506-112443-000` | frontend only | — | `sha256:0a1fd97b…` |
| `brewspace-20260506-115231-000` | **api + frontend** | `sha256:0c0f9434…` | `sha256:0a1fd97b…` |
| `brewspace-20260530-083833-000` | frontend only | — | `sha256:472802c1…` |

Annotation on latest Snapshot:

```text
Component(s) 'brewspace-api' is(are) not included in snapshot due to missing valid containerImage or git source
```

### RBAC

```bash
oc auth can-i create deployments.apps -n sfathii-tenant   # no
oc auth can-i create services -n sfathii-tenant           # no
oc auth can-i create routes.route.openshift.io -n sfathii-tenant  # no
oc auth can-i create projectrequests                       # no
```

Only project visible to this user: `sfathii-tenant`.

---

## Question-by-question analysis

### 1. What is missing before this application can be deployed?

| Gap | Severity | Detail |
|-----|----------|--------|
| Workload namespace + RBAC | **Blocker** | Tenant namespace cannot host Deployments. User cannot self-provision a project. |
| Successful `brewspace-api` build | **Blocker** | API Component status is empty; no API digest in latest Snapshot. |
| Image digest pinning in Kustomize | **Blocker** | `kustomization.yaml` uses `newTag: latest`; Konflux tags images with commit SHA. |
| Manifest apply to runtime namespace | **Blocker** | `deploy/openshift/` has never been applied (no Routes exist). |
| Namespace-scoped pull secrets | **High** | Deploy namespace must pull from `quay.io/redhat-user-workloads/sfathii-tenant/`. Konflux links this automatically in *workload* namespaces; must be confirmed after namespace is provisioned. |
| Fix Git placeholder URLs | Medium | Repo `component.yaml` and `integration/verify-*.yaml` still reference `example-org`; cluster Components are correctly wired to `tomswallaRH`. |
| Register functional integration scenarios | Medium | `brewspace-verify-api` / `brewspace-verify-frontend` not on cluster. |
| `ReleasePlan` / GitOps automation | Low (for manual deploy) | Not required for first `oc apply -k` deploy; required for Konflux-native promotion. |

**What is already in place:**

- Konflux `Application` and both `Component` CRs on cluster
- PaC push pipelines (`.tekton/brewspace-*-push.yaml`) targeting correct Quay paths
- Valid OpenShift Deployment/Service/Route manifests
- Frontend nginx reverse-proxy for `/health` → `brewspace-api` Service
- Health endpoints in API (`GET /health`) and static frontend (`GET /`)
- At least one historical Snapshot with **both** component digests

---

### 2. Are the OpenShift manifests valid?

**Yes — structurally valid.**

```bash
kustomize build applications/brewspace/deploy/openshift
```

exits 0 and produces coherent `Deployment`, `Service`, and `Route` objects.

| Check | Result |
|-------|--------|
| API schema / required fields | Pass |
| Label selectors Deployment ↔ Service | Pass (`app.kubernetes.io/name`) |
| Port alignment (8080 throughout) | Pass |
| Route `targetPort: http` matches Service port name | Pass |
| Kustomize image rewrite | Pass (rewrites placeholder to Quay path) |
| `kubectl apply --dry-run=server` | Not run (no deploy namespace RBAC) |

**Gaps (not invalid, but incomplete for production):**

- No `namespace:` in Kustomization (must pass `-n` at apply time)
- No `imagePullSecrets` (rely on namespace default / linked secrets)
- No `imagePullPolicy: Always` explicit (defaults to `Always` for `:latest` tag — use digest pinning instead)
- No `NetworkPolicy`, `PodDisruptionBudget`, HPA, or resource quotas
- No `ConfigMap` / `Secret` for runtime configuration (acceptable for this minimal app)

---

### 3. Are the Deployments referencing the correct image locations?

**Partially — correct registry/repo, wrong tag strategy.**

Kustomize output after build:

```text
quay.io/redhat-user-workloads/sfathii-tenant/brewspace-api:latest
quay.io/redhat-user-workloads/sfathii-tenant/brewspace-frontend:latest
```

PaC pipelines publish:

```text
quay.io/redhat-user-workloads/sfathii-tenant/brewspace-api:<git-sha>
quay.io/redhat-user-workloads/sfathii-tenant/brewspace-frontend:<git-sha>
```

The registry and repository paths **match**. The tag `latest` is a **placeholder** and is unlikely to resolve unless manually tagged. Konflux `apply-tags` task tags with commit SHA, not `latest`.

**Recommended pins** (from Snapshot `brewspace-20260506-115231-000`):

```text
brewspace-api:      @sha256:0c0f943433952f8ab7ba69d619dbab0fe6a41f4050a645abaf02e53277412ef6
brewspace-frontend: @sha256:0a1fd97bf2f6d50662320f1041b8b0bf117d3beac1ad7ca289df9c2f50daa444
```

Or use digests from a **new** green build after retriggering both components.

---

### 4. Are Services configured correctly?

**Yes.**

| Service | Selector | Port | Target | Backend |
|---------|----------|------|--------|---------|
| `brewspace-api` | `app.kubernetes.io/name: brewspace-api` | 8080 (`http`) | 8080 | Flask/gunicorn |
| `brewspace-frontend` | `app.kubernetes.io/name: brewspace-frontend` | 8080 (`http`) | 8080 | nginx UBI image |

Both Services are `ClusterIP` (default), which is correct: only Routes expose externally; frontend reaches API via in-cluster DNS `brewspace-api.sfathii-<dev>.svc.cluster.local`.

---

### 5. Are Routes configured correctly?

**Yes for a minimal dev deployment.**

| Route | Service | TLS | Notes |
|-------|---------|-----|-------|
| `brewspace-frontend` | `brewspace-frontend` | edge, redirect HTTP | **Primary user URL** |
| `brewspace-api` | `brewspace-api` | edge, redirect HTTP | Debug / direct API access |

- `spec.port.targetPort: http` correctly references the named Service port.
- Edge termination is standard for OpenShift dev Routes.
- No custom hostname — OpenShift assigns `brewspace-frontend-<ns>.apps.<cluster-domain>`.

**Not configured (acceptable for v1):**

- No single-host ingress with path-based routing (`/` → frontend, `/api` → api). Cross-origin is avoided because the browser calls `/health` through the frontend nginx proxy.

---

### 6. Can frontend communicate with API?

**Yes — when both Pods run in the same namespace.**

Architecture:

```text
Browser  →  Route(brewspace-frontend)  →  nginx:8080
                                              │
                    fetch('/health')  ────────┤ location /health
                                              │   proxy_pass http://brewspace-api:8080
                                              ▼
                                         brewspace-api Service → Flask /health
```

Evidence in repo:

- `nginx-default.conf` proxies `/health` to `http://brewspace-api:8080`
- `index.html` defaults to `fetch('/health')` (same-origin via nginx proxy)
- Optional override: `?api=https://<api-route>` for cross-Route testing

**Failure modes:**

| Scenario | Symptom | Cause |
|----------|---------|-------|
| API Pod down | UI shows "API Status: Unreachable" | nginx proxy returns 502 |
| API in different namespace | Proxy fails DNS lookup | Service name not FQDN-qualified |
| Only frontend deployed | Same unreachable message | Partial Snapshot deploy |
| CORS via separate API Route | Works only with `?api=` query param | Browser blocks cross-origin without CORS headers on API |

For the target URL `https://<frontend-route>/`, the default `/health` proxy path is the correct design.

---

### 7. Are health checks present?

**Yes on both Deployments.**

| Workload | Readiness | Liveness | Endpoint | Notes |
|----------|-----------|----------|----------|-------|
| `brewspace-api` | `GET /health:8080` | `GET /health:8080` | Flask JSON `{"status":"ok"}` | Aligns with Containerfile (`gunicorn`) |
| `brewspace-frontend` | `GET /:8080` | `GET /:8080` | Static `index.html` | Valid; could also use `/health` via proxy |

Timing: readiness `initialDelaySeconds: 3`, liveness `initialDelaySeconds: 10` — reasonable for small images.

**Not present:** startupProbe (unnecessary at this scale).

---

### 8. Are IntegrationTestScenarios sufficient?

**No — not for functional deployment validation.**

#### On cluster today

| Scenario | Type | Validates |
|----------|------|-----------|
| `brewspace-enterprise-contract` | Enterprise Contract policy | Image signature, SBOM, CVE policy — **not** runtime HTTP behavior |

#### In Git repo (`applications/brewspace/integration/`)

| File | Problem |
|------|---------|
| `verify-api.yaml` | `resolverRef.pathInRepo` points to **itself** (an `IntegrationTestScenario` CR), not a Tekton `Pipeline` |
| `verify-frontend.yaml` | Same self-reference issue |
| Both | `resolverRef.params.url` = `https://github.com/example-org/dno-automation-services` (wrong fork) |
| Both | Missing `resolverRef.resourceKind: pipeline` |
| Both | **Not applied** to `sfathii-tenant` |

These files are **learning placeholders**, not runnable integration pipelines. They document intent (`expected-status: ok`, `expected-text: API Status: OK`) but do not ship the Tekton pipeline that deploys ephemeral Pods and curls `/health`.

**What sufficient integration would require:**

1. Tekton `Pipeline` (or reference to `konflux-ci/build-definitions` test pipeline) that deploys Snapshot images and asserts HTTP responses
2. `IntegrationTestScenario` with `resourceKind: pipeline` and correct `pathInRepo`
3. Scenarios registered on cluster and passing against a **complete** Snapshot (api + frontend)
4. Optional: scenario that validates frontend→api proxy wiring, not just isolated API health

**EC alone is necessary but not sufficient** for proving `https://<route>` works.

---

### 9. What Konflux resources are still missing?

| Resource | On cluster? | Required for deploy? |
|----------|-------------|----------------------|
| `Application/brewspace` | Yes | Yes |
| `Component/brewspace-api` | Yes (no build status) | Yes |
| `Component/brewspace-frontend` | Yes (built) | Yes |
| PaC `PipelineRun` templates | Yes (in Git → PaC) | Yes (for fresh builds) |
| Complete `Snapshot` (api + frontend) | Partial only (latest) | Yes (for digest pinning) |
| `IntegrationTestScenario` verify-* | **No** | Recommended |
| `IntegrationTestScenario` enterprise-contract | Yes | Policy gate |
| `ReleasePlan` | **No** | Optional (GitOps promotion) |
| `ReleasePlanAdmission` | **No** | Optional |
| `SnapshotEnvironmentBinding` | **No** | Optional |
| Runtime `Deployment/Service/Route` | **No** | **Yes** |

---

## Architecture reference

```mermaid
flowchart TB
    subgraph konflux["sfathii-tenant (Konflux — build only)"]
        APP[Application brewspace]
        API_C[Component brewspace-api]
        FE_C[Component brewspace-frontend]
        PR[PipelineRuns]
        SNAP[Snapshot]
        INT[IntegrationTestScenario]
    end

    subgraph quay["Quay"]
        API_IMG[brewspace-api@sha256]
        FE_IMG[brewspace-frontend@sha256]
    end

    subgraph runtime["sfathii-*-dev (MISSING — workload namespace)"]
        API_D[Deployment brewspace-api]
        FE_D[Deployment brewspace-frontend]
        API_S[Service brewspace-api]
        FE_S[Service brewspace-frontend]
        FE_R[Route brewspace-frontend]
    end

    APP --> API_C & FE_C
    API_C & FE_C --> PR --> API_IMG & FE_IMG
    PR --> SNAP
    SNAP --> INT
    API_IMG --> API_D
    FE_IMG --> FE_D
    FE_R --> FE_S --> FE_D
    FE_D -->|nginx /health proxy| API_S --> API_D
```

---

## Verdict

### Can brewspace be deployed today?

**No.**

### What must be fixed first (ordered)

| Priority | Action | Owner |
|----------|--------|-------|
| 1 | Provision a **workload namespace** where `sfathii` can create Deployments, Services, Routes, and pull from tenant Quay | Platform / mentor |
| 2 | **Rebuild `brewspace-api`** (or confirm digest `sha256:0c0f9434…` still valid) so a complete two-component Snapshot exists | Developer |
| 3 | **Pin image digests** in `applications/brewspace/deploy/openshift/kustomization.yaml` (replace `latest`) | Developer |
| 4 | **`oc apply -k`** manifests into the workload namespace | Developer |
| 5 | Verify frontend Route URL serves UI with "API Status: OK" | Developer |
| 6 | (Recommended) Fix and register `brewspace-verify-api` / `brewspace-verify-frontend` integration scenarios | Developer |

### Conditional fast path

If platform grants a dev namespace **today**, you can deploy immediately using digests from Snapshot `brewspace-20260506-115231-000` without waiting for new builds — assuming Quay images were not garbage-collected and pull secrets are linked. This gets you to `https://<route>` fastest, but you should still rebuild `brewspace-api` to restore current Component status and fresh Snapshots.

---

## Related documentation

- [Deployment plan](deployment-plan.md) — phased commands to reach `https://<route>`
- [Brewspace README](../../applications/brewspace/README.md) — deploy prerequisites
- [Runtime analysis](../analysis/brewspace-runtime-analysis.md) — build pipeline forensics
- [Quay read-only incident](../analysis/incident-quay-readonly.md) — historical build blocker
