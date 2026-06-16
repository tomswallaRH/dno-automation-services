# Brewspace Deployment Plan

**Goal:** Serve the frontend at `https://<route>` with the UI successfully calling the API backend.

**Prerequisites:**

- `oc` logged in as `sfathii` on `kflux-prd-rh02`
- Konflux Application `brewspace` and Components exist in `sfathii-tenant`
- A **workload namespace** `<deploy-ns>` where you can create Deployments (not `sfathii-tenant`)

```bash
export TENANT_NS=sfathii-tenant
export DEPLOY_NS=<your-workload-namespace>   # e.g. sfathii-dev — must be provisioned by platform
export REPO_ROOT=/path/to/dno-automation-services
```

> **Blocker today:** `sfathii` cannot create Deployments in `sfathii-tenant` and cannot self-provision projects. Complete **Phase 0** before Phase 3.

---

## Phase 0 — Provision workload namespace (prerequisite)

Platform team or mentor must complete this before deployment phases.

### Commands

```bash
# Confirm you are not deploying into the Konflux tenant
oc auth can-i create deployments.apps -n $TENANT_NS
# Expected: no

# After namespace is created for you
oc auth can-i create deployments.apps -n $DEPLOY_NS
oc auth can-i create services -n $DEPLOY_NS
oc auth can-i create routes.route.openshift.io -n $DEPLOY_NS
```

### Expected results

| Check | Expected |
|-------|----------|
| Tenant namespace RBAC | `no` for Deployments |
| Workload namespace RBAC | `yes` for Deployments, Services, Routes |
| Quay pull | Namespace can pull `quay.io/redhat-user-workloads/sfathii-tenant/*` (linked pull secret or global pull secret) |

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| No workload namespace provisioned | All `oc apply` commands fail with Forbidden |
| Missing pull secret | Pods stuck `ImagePullBackOff` |
| Deploying into tenant namespace | `oc apply` rejected or pods never scheduled |

### Recovery actions

1. Request a dev namespace from Konflux platform team with Deployment + Route RBAC.
2. Ask admin to link `redhat-user-workloads` Quay pull credentials to `<deploy-ns>`.
3. Never apply runtime manifests to `sfathii-tenant`.

---

## Phase 1 — Build images

Produce fresh container images for **both** components in Quay.

### Commands

```bash
cd $REPO_ROOT

# Option A — trigger via empty commit (touch one component path at a time to avoid duplicate runs)
git commit --allow-empty -m "chore: retrigger brewspace-api build"
git push origin main

# Wait for api build, then frontend (or push both paths in one commit if acceptable)
git commit --allow-empty -m "chore: retrigger brewspace-frontend build"
git push origin main

# Monitor builds
oc get pipelinerun -n $TENANT_NS -l appstudio.openshift.io/application=brewspace -w

# Per-component detail
oc get pipelinerun -n $TENANT_NS -l appstudio.openshift.io/component=brewspace-api --sort-by=.metadata.creationTimestamp
oc get pipelinerun -n $TENANT_NS -l appstudio.openshift.io/component=brewspace-frontend --sort-by=.metadata.creationTimestamp

# Extract digests on success
API_PR=$(oc get pipelinerun -n $TENANT_NS -l appstudio.openshift.io/component=brewspace-api --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
FE_PR=$(oc get pipelinerun -n $TENANT_NS -l appstudio.openshift.io/component=brewspace-frontend --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')

oc get pipelinerun $API_PR -n $TENANT_NS -o jsonpath='build-api: {.status.results[?(@.name=="IMAGE_URL")].value}{"\n"}digest: {.status.results[?(@.name=="IMAGE_DIGEST")].value}{"\n"}'
oc get pipelinerun $FE_PR -n $TENANT_NS -o jsonpath='build-fe: {.status.results[?(@.name=="IMAGE_URL")].value}{"\n"}digest: {.status.results[?(@.name=="IMAGE_DIGEST")].value}{"\n"}'

# Confirm Component status updated
oc get component brewspace-api brewspace-frontend -n $TENANT_NS -o yaml | grep -E 'lastBuiltCommit|lastPromotedImage'
```

### Expected results

| Resource | Expected |
|----------|----------|
| `PipelineRun/brewspace-api-on-push-*` | `Succeeded` |
| `PipelineRun/brewspace-frontend-on-push-*` | `Succeeded` |
| `IMAGE_DIGEST` results | Non-empty `sha256:…` on both PipelineRuns |
| `Component/brewspace-api` status | `lastBuiltCommit` and image digest populated |
| New `Snapshot` | Contains **both** `brewspace-api` and `brewspace-frontend` digests |

### Failure scenarios

| Failure | Symptom | Likely cause |
|---------|---------|--------------|
| PipelineRun stuck on `clone-repository` | TaskRun Running 10m+; logs show `oras push` retries | Quay read-only / registry outage |
| `prefetch-dependencies` Failed | API build only | PyPI / proxy / `requirements.txt` |
| `build-container` Failed | buildah errors in logs | Containerfile, base image pull, OOM |
| `clair-scan` / EC Failed | PipelineRun Failed at scan stage | CVE policy violation |
| Partial Snapshot | Only frontend in Snapshot | API build did not complete |
| No PipelineRun created | Push did not match CEL path filter | Wrong branch or paths not changed |

### Recovery actions

1. **Quay read-only:** Open platform ticket; cancel stuck PipelineRuns; re-push after registry recovery. See [incident-quay-readonly.md](../analysis/incident-quay-readonly.md).
2. **Duplicate api runs:** Cancel older PipelineRun; avoid rapid successive pushes to `applications/brewspace/components/api/`.
3. **Scan failure:** Inspect failing TaskRun logs; fix CVE or request policy waiver from platform.
4. **No trigger:** Ensure push is to `main` and touches `applications/brewspace/components/<component>/**` or `.tekton/brewspace-*-push.yaml`.

### Fast-path alternative (skip rebuild)

If you accept images from 2026-05-06, use Snapshot `brewspace-20260506-115231-000` digests in Phase 3 instead of waiting for new builds:

```text
brewspace-api:      sha256:0c0f943433952f8ab7ba69d619dbab0fe6a41f4050a645abaf02e53277412ef6
brewspace-frontend: sha256:0a1fd97bf2f6d50662320f1041b8b0bf117d3beac1ad7ca289df9c2f50daa444
```

---

## Phase 2 — Verify images exist in Quay

Confirm the digests you will deploy are pullable.

### Commands

```bash
# From PipelineRun or Snapshot
SNAP=brewspace-20260506-115231-000   # or latest complete snapshot
oc get snapshot $SNAP -n $TENANT_NS -o jsonpath='{range .spec.components[*]}{.name}{"\t"}{.containerImage}{"\n"}{end}'

# From cluster (authenticated pull — most reliable)
API_IMAGE="quay.io/redhat-user-workloads/sfathii-tenant/brewspace-api@sha256:<api-digest>"
FE_IMAGE="quay.io/redhat-user-workloads/sfathii-tenant/brewspace-frontend@sha256:<fe-digest>"

oc run img-check-api --image=$API_IMAGE -n $DEPLOY_NS --restart=Never --command -- sleep 30
oc run img-check-fe --image=$FE_IMAGE -n $DEPLOY_NS --restart=Never --command -- sleep 30
oc get pod img-check-api img-check-fe -n $DEPLOY_NS
oc delete pod img-check-api img-check-fe -n $DEPLOY_NS
```

### Expected results

| Check | Expected |
|-------|----------|
| Snapshot components | Both `brewspace-api` and `brewspace-frontend` with `@sha256:` URIs |
| Test pods | `Running` then `Completed`; no `ImagePullBackOff` |
| Component status | `lastPromotedImage` matches intended digest (if freshly built) |

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| Image deleted / expired | `ImagePullBackOff`, `manifest unknown` |
| Wrong digest | Pod pulls but wrong application version |
| No pull secret | `401 Unauthorized` on pull |
| Only frontend in Snapshot | API image line missing — cannot deploy full stack |

### Recovery actions

1. Re-run Phase 1 for the missing component.
2. Request Quay pull secret linkage for `$DEPLOY_NS`.
3. Copy exact digest from `PipelineRun.status.results[IMAGE_DIGEST]`, not tag names.

---

## Phase 3 — Deploy manifests

Apply OpenShift manifests with real digests into the workload namespace.

### Commands

```bash
cd $REPO_ROOT/applications/brewspace/deploy/openshift

# Pin digests (replace with your PipelineRun / Snapshot values)
kustomize edit set image \
  brewspace-api=quay.io/redhat-user-workloads/sfathii-tenant/brewspace-api@sha256:<api-digest>
kustomize edit set image \
  brewspace-frontend=quay.io/redhat-user-workloads/sfathii-tenant/brewspace-frontend@sha256:<fe-digest>

# Validate rendered output
kustomize build .

# Apply
oc apply -k . -n $DEPLOY_NS

# Confirm resources created
oc get deployment,service,route -n $DEPLOY_NS -l app.kubernetes.io/part-of=brewspace
```

### Expected results

| Resource | Expected |
|----------|----------|
| `Deployment/brewspace-api` | Created, 1 desired replica |
| `Deployment/brewspace-frontend` | Created, 1 desired replica |
| `Service/brewspace-api` | ClusterIP port 8080 |
| `Service/brewspace-frontend` | ClusterIP port 8080 |
| `Route/brewspace-frontend` | Host assigned under `*.apps.kflux-prd-rh02.0fk9.p1.openshiftapps.com` |
| `Route/brewspace-api` | Host assigned (optional direct API access) |

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| Forbidden on apply | Wrong namespace / no RBAC |
| Invalid image reference | Deployment created but pods fail immediately |
| Route not created | Cluster lacks route RBAC or ingress controller issue |
| Still using `:latest` | `ImagePullBackOff` — tag does not exist |

### Recovery actions

1. Verify `$DEPLOY_NS` is not `$TENANT_NS`.
2. Re-run `kustomize edit set image` with `@sha256:` digests, never `latest`.
3. `oc describe route brewspace-frontend -n $DEPLOY_NS` for router errors.
4. `oc delete -k . -n $DEPLOY_NS` and re-apply after fixing images.

---

## Phase 4 — Verify Pods

Confirm both workloads are running and probes are passing.

### Commands

```bash
oc get pods -n $DEPLOY_NS -l app.kubernetes.io/part-of=brewspace -w

oc describe pod -n $DEPLOY_NS -l app.kubernetes.io/name=brewspace-api | tail -30
oc describe pod -n $DEPLOY_NS -l app.kubernetes.io/name=brewspace-frontend | tail -30

# Direct health check inside cluster
oc exec -n $DEPLOY_NS deploy/brewspace-api -- curl -sf http://localhost:8080/health
oc exec -n $DEPLOY_NS deploy/brewspace-frontend -- curl -sf http://localhost:8080/
oc exec -n $DEPLOY_NS deploy/brewspace-frontend -- curl -sf http://localhost:8080/health
```

### Expected results

| Pod | Expected |
|-----|----------|
| `brewspace-api-*` | `Running`, `READY 1/1` |
| `brewspace-frontend-*` | `Running`, `READY 1/1` |
| API `/health` | `{"status":"ok","service":"brewspace-api"}` |
| Frontend `/` | HTML containing `Brewspace` |
| Frontend `/health` (proxied) | Same JSON as API `/health` |

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| `ImagePullBackOff` | Wrong digest or missing pull secret |
| `CrashLoopBackOff` (api) | gunicorn/flask startup error |
| `CrashLoopBackOff` (frontend) | nginx config syntax error |
| Readiness probe failing | `/health` or `/` returns non-2xx |
| API up, frontend `/health` fails | nginx cannot resolve `brewspace-api` Service (wrong namespace) |

### Recovery actions

1. `oc logs -n $DEPLOY_NS deploy/brewspace-api` / `deploy/brewspace-frontend`.
2. `oc get events -n $DEPLOY_NS --sort-by=.lastTimestamp | tail -20`.
3. Confirm both Deployments are in the **same** namespace.
4. `oc rollout restart deployment/brewspace-api -n $DEPLOY_NS` after image fix.

---

## Phase 5 — Verify Services

Confirm Service endpoints map to healthy Pods.

### Commands

```bash
oc get svc brewspace-api brewspace-frontend -n $DEPLOY_NS
oc get endpoints brewspace-api brewspace-frontend -n $DEPLOY_NS

# In-cluster curl via a temporary pod
oc run curl-test --image=registry.redhat.io/ubi9/ubi-minimal -n $DEPLOY_NS --restart=Never --command -- sleep 300
oc wait --for=condition=Ready pod/curl-test -n $DEPLOY_NS --timeout=60s
oc exec -n $DEPLOY_NS curl-test -- curl -sf http://brewspace-api:8080/health
oc exec -n $DEPLOY_NS curl-test -- curl -sf http://brewspace-frontend:8080/health
oc delete pod curl-test -n $DEPLOY_NS
```

### Expected results

| Service | Endpoints | Curl |
|---------|-----------|------|
| `brewspace-api` | `10.x.x.x:8080` | `/health` → 200 JSON |
| `brewspace-frontend` | `10.x.x.x:8080` | `/health` → proxied 200 JSON |

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| Empty endpoints | Service selector does not match Pod labels |
| Connection refused | Pod not listening on 8080 |
| Frontend `/health` 502 | API Service has no endpoints |

### Recovery actions

1. Compare `spec.selector` on Service with `metadata.labels` on Pod template.
2. `oc get pods -n $DEPLOY_NS --show-labels`.
3. Fix Deployment labels or redeploy API first, then frontend.

---

## Phase 6 — Verify Routes

Confirm external HTTPS URLs are reachable.

### Commands

```bash
FE_HOST=$(oc get route brewspace-frontend -n $DEPLOY_NS -o jsonpath='{.spec.host}')
API_HOST=$(oc get route brewspace-api -n $DEPLOY_NS -o jsonpath='{.spec.host}')

echo "Frontend: https://$FE_HOST"
echo "API:      https://$API_HOST"

curl -sf "https://$FE_HOST/" | head -20
curl -sf "https://$FE_HOST/health"
curl -sf "https://$API_HOST/health"

# TLS redirect check (HTTP should redirect)
curl -sI "http://$FE_HOST/" | head -5
```

### Expected results

| Route | Expected |
|-------|----------|
| `https://$FE_HOST/` | 200 HTML with `<h1>Brewspace</h1>` |
| `https://$FE_HOST/health` | `{"status":"ok",…}` via nginx proxy |
| `https://$API_HOST/health` | `{"status":"ok",…}` direct |
| `http://$FE_HOST/` | 302 redirect to HTTPS |

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| Route host empty | Route not admitted by ingress controller |
| 503 on Route | No endpoints behind Service |
| `/` works, `/health` 502 | API not running or proxy misconfigured |
| TLS errors | Corporate proxy / cert trust issue on client |

### Recovery actions

1. `oc describe route brewspace-frontend -n $DEPLOY_NS`.
2. Return to Phase 4 if endpoints are empty.
3. Test in-cluster first (Phase 5) to isolate in-cluster vs edge routing.

---

## Phase 7 — Verify frontend → API communication

Validate the user-facing success criterion: browser loads frontend and API health check passes.

### Commands

```bash
FE_HOST=$(oc get route brewspace-frontend -n $DEPLOY_NS -o jsonpath='{.spec.host}')

# Simulates browser fetch to /health (same-origin via nginx)
curl -sf "https://$FE_HOST/health" | jq .

# Open in browser
echo "Open: https://$FE_HOST/"
# Expected visible text: "API Status: OK"

# Optional — test cross-route mode
API_HOST=$(oc get route brewspace-api -n $DEPLOY_NS -o jsonpath='{.spec.host}')
echo "Cross-route test: https://$FE_HOST/?api=https://$API_HOST"
# Note: may fail without CORS headers on API; default proxy path is preferred
```

### Manual browser checklist

| Step | Expected |
|------|----------|
| Navigate to `https://<frontend-route>/` | Page title "Brewspace Frontend" |
| Page loads | Heading "Brewspace" visible |
| JavaScript runs | Status text changes from "Checking…" to **"API Status: OK"** |
| DevTools Network tab | `GET /health` returns 200, `Content-Type: application/json` |

### Expected results

- UI displays **API Status: OK**
- No CORS errors (because `/health` is same-origin via nginx proxy)
- Response body `{"status":"ok","service":"brewspace-api"}`

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| "API Status: Unreachable" | `/health` fetch failed (502/timeout) |
| "API Status: Unexpected Response" | API returned non-ok status field |
| Page shows "Checking…" forever | JavaScript error; check browser console |
| Works via curl, fails in browser | Mixed content or corporate TLS inspection |

### Recovery actions

1. Verify nginx proxy: `oc exec deploy/brewspace-frontend -n $DEPLOY_NS -- cat /etc/nginx/conf.d/default.conf`.
2. Confirm `brewspace-api` Service DNS resolves inside frontend pod:
   `oc exec deploy/brewspace-frontend -n $DEPLOY_NS -- curl -v http://brewspace-api:8080/health`.
3. Redeploy API before frontend if API was scaled to zero.
4. Do **not** rely on separate API Route for default UI; fix in-cluster proxy first.

---

## Phase 8 — Verify integration tests

Validate Konflux integration pipeline results for the deployed Snapshot.

### Commands

```bash
# List scenarios
oc get integrationtestscenario -n $TENANT_NS

# Latest snapshot
oc get snapshot -n $TENANT_NS -l appstudio.openshift.io/application=brewspace --sort-by=.metadata.creationTimestamp

# Enterprise Contract (always present)
oc get pipelinerun -n $TENANT_NS | grep -i enterprise-contract

# If verify scenarios are registered
oc get pipelinerun -n $TENANT_NS | grep -i verify

# Snapshot test status annotation
oc get snapshot <snapshot-name> -n $TENANT_NS -o jsonpath='{.metadata.annotations.test\.appstudio\.openshift\.io/git-reporter-status}' | jq .
```

### Register functional scenarios (recommended, one-time)

Before this phase is meaningful for `brewspace-verify-*`, fix Git URLs and apply scenarios:

```bash
# Edit resolverRef url in both files to:
#   https://github.com/tomswallaRH/dno-automation-services
# And point pathInRepo to a real Tekton Pipeline (not the scenario CR itself)

oc apply -f applications/brewspace/integration/verify-api.yaml -n $TENANT_NS
oc apply -f applications/brewspace/integration/verify-frontend.yaml -n $TENANT_NS
```

### Expected results

| Test | Expected |
|------|----------|
| `brewspace-enterprise-contract` | `Succeeded` / TestPassed on complete Snapshot |
| `brewspace-verify-api` (if registered) | Passes with `expected-status: ok` |
| `brewspace-verify-frontend` (if registered) | Passes with `expected-text: API Status: OK` |
| Snapshot annotation | Scenarios marked passed in `git-reporter-status` |

### Failure scenarios

| Failure | Symptom |
|---------|---------|
| EC failed | CVE / policy violation on image |
| verify scenarios never run | Not registered on cluster |
| verify scenarios fail at resolver | `example-org` URL or self-referential `pathInRepo` |
| Partial Snapshot | Integration runs only against frontend digest |
| Tests pass, Route fails | Integration does not deploy your Routes — manual Phase 7 still required |

### Recovery actions

1. Fix failing EC issues or request policy exception.
2. Update `integration/verify-*.yaml` resolver URLs to `tomswallaRH` fork.
3. Replace placeholder scenarios with pipelines from `konflux-ci/build-definitions` or custom Tekton that deploy Snapshot images and curl `/health`.
4. Trigger new builds to produce a fresh complete Snapshot, then re-run integration.

---

## Success criteria summary

You are done when all of the following are true:

```text
✓  Both images exist in Quay at pinned @sha256 digests
✓  Deployments/Service/Routes applied in workload namespace (not tenant)
✓  brewspace-api and brewspace-frontend Pods Running 1/1
✓  https://<frontend-route>/ shows "API Status: OK"
✓  https://<frontend-route>/health returns {"status":"ok"}
✓  https://<api-route>/health returns {"status":"ok"} (optional direct check)
✓  Enterprise Contract integration passed on complete Snapshot
```

---

## Final verdict

### Can brewspace be deployed today?

**No — not without platform action.**

| Blocker | Status (2026-06-09) |
|---------|---------------------|
| Workload namespace with Deployment RBAC | **Missing** — only `sfathii-tenant` accessible; Deployments forbidden |
| Complete image set for deploy | **Partial** — latest Snapshot is frontend-only; API Component status empty |
| Kustomize image tags | **Wrong** — `latest` placeholder, not build digests |
| Manifests applied | **Not done** — no Routes in a runtime namespace |
| Functional integration tests | **Insufficient** — only EC on cluster; verify scenarios are placeholders |

### Minimum fix sequence

```text
1. Platform provisions <deploy-ns> with Route + Quay pull access     [BLOCKER]
2. Rebuild brewspace-api OR use sha256:0c0f9434… from 2026-05-06 Snapshot
3. kustomize edit set image …@sha256:… for both components
4. oc apply -k applications/brewspace/deploy/openshift -n <deploy-ns>
5. Open https://<frontend-route>/ and confirm "API Status: OK"
```

**Estimated time after namespace is provisioned:**

| Path | Duration |
|------|----------|
| Fast path (existing digests from May 2026) | 15–30 minutes |
| Full rebuild both components | 30–60 minutes (healthy registry) |

---

## Related documentation

- [Deployment readiness review](deployment-readiness-review.md) — detailed gap analysis
- [Brewspace README](../../applications/brewspace/README.md)
- [Lab 07 — Release and Promotion](../learning-labs/lab-07-release-and-promotion.md)
