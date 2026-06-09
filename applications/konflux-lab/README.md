# konflux-lab

The smallest real-world Konflux learning application in this repository.

One Application, one Component, one Flask API. No frontend, database, auth, or GitOps.

## What you will learn

| Konflux concept | Where in this repo |
|-----------------|-------------------|
| Application | `application.yaml` |
| Component | `components/hello-api/component.yaml` |
| PipelineRun | `.tekton/konflux-lab-hello-api-*.yaml` |
| TaskRun | Child runs of the build PipelineRun (UI or `oc get taskrun`) |
| Snapshot | Created automatically after a successful build |
| IntegrationTestScenario | `integration/verify-hello-api.yaml` |
| OpenShift Deployment | `deploy/openshift/hello-api.yaml` |
| Route | `deploy/openshift/route.yaml` |

Full learning path: [docs/konflux-lab-learning-path.md](../../docs/konflux-lab-learning-path.md)

## Repository layout

```
applications/konflux-lab/
├── application.yaml          # Application CR (Lab 1)
├── architecture.md           # Concept map
├── components/
│   └── hello-api/
│       ├── component.yaml    # Component CR (Lab 2)
│       ├── Containerfile
│       ├── requirements.txt
│       └── src/app.py        # Flask API (< 100 lines)
├── integration/
│   ├── verify-hello-api.yaml
│   └── pipeline/verify-health.yaml
├── pipelines/
│   └── konflux-lab-pipeline.yaml
├── deploy/openshift/
│   ├── hello-api.yaml        # Deployment + Service
│   ├── route.yaml
│   └── kustomization.yaml
└── README.md
```

## HTTP contract

| Endpoint | Response |
|----------|----------|
| `GET /` | `{"status":"ok","application":"konflux-lab"}` |
| `GET /health` | `{"status":"ok","service":"hello-api"}` |

## Step-by-step setup

Replace `<tenant>`, `<tenant-namespace>`, and Git URLs with your environment.

### 1. Lab 1 — Create Application

**UI:** Developer Hub → Create Application → name `konflux-lab`.

**CLI:**

```bash
export TENANT_NS=<tenant-namespace>
oc apply -f applications/konflux-lab/application.yaml -n $TENANT_NS
oc get application konflux-lab -n $TENANT_NS
```

**Learn:** An Application is a product boundary. It does not build code by itself.

### 2. Lab 2 — Create Component

**UI:** Application `konflux-lab` → Add Component → import from `components/hello-api/component.yaml`.

Update `spec.source.git.url` to your fork before applying.

```bash
oc apply -f applications/konflux-lab/components/hello-api/component.yaml -n $TENANT_NS
oc get component hello-api -n $TENANT_NS
```

**Learn:** A Component is a buildable unit with its own source context and image output.

### 3. Lab 3 — Trigger Build

Commit and push a change under `components/hello-api/`, or use the Konflux UI **Build** action.

PaC templates in `.tekton/` trigger on push/PR when paths under `hello-api` change.

```bash
git add applications/konflux-lab/
git commit -m "Add konflux-lab learning application"
git push origin main
```

**Learn:** Git events create PipelineRuns via Pipeline-as-Code — not a Jenkins "Build Now" button.

### 4. Lab 4 — Observe PipelineRun

```bash
oc get pipelinerun -n $TENANT_NS -l appstudio.openshift.io/component=hello-api
oc describe pipelinerun <name> -n $TENANT_NS
oc get taskrun -n $TENANT_NS -l tekton.dev/pipelineRun=<name>
```

In the UI: Component `hello-api` → Pipeline runs → open logs for `build-container`, note `IMAGE_DIGEST`.

**Learn:** A PipelineRun is one build execution. TaskRuns are its steps.

### 5. Lab 5 — Observe Snapshot

After the build succeeds:

```bash
oc get snapshot -n $TENANT_NS -l appstudio.openshift.io/application=konflux-lab
oc get snapshot <name> -n $TENANT_NS -o yaml | grep -E 'hello-api|sha256'
```

**Learn:** A Snapshot freezes image digests for one application state. Promotion and tests use digests, not mutable tags.

### 6. Lab 6 — Integration tests

Update `integration/verify-hello-api.yaml` resolver URL to your Git remote, then apply:

```bash
oc apply -f applications/konflux-lab/integration/verify-hello-api.yaml -n $TENANT_NS
```

After the next Snapshot:

```bash
oc get integrationtestscenario -n $TENANT_NS
oc get pipelinerun -n $TENANT_NS | grep -i verify
```

**Learn:** IntegrationTestScenario runs a Tekton pipeline against Snapshot contents.

### 7. Lab 7 — Deploy and access Route

Konflux tenant namespaces usually cannot host arbitrary Deployments. Use a dev namespace:

```bash
export DEPLOY_NS=<your-dev-namespace>
oc auth can-i create deployments.apps -n $DEPLOY_NS

cd applications/konflux-lab/deploy/openshift
kustomize edit set image hello-api=quay.io/redhat-user-workloads/<tenant>/hello-api@sha256:<digest>
oc apply -k . -n $DEPLOY_NS

oc get route hello-api -n $DEPLOY_NS -o jsonpath='https://{.spec.host}{"\n"}'
curl -s https://<route>/ | jq .
```

Expected:

```json
{
  "status": "ok",
  "application": "konflux-lab"
}
```

**Learn:** Konflux builds images; you deploy them with ordinary OpenShift manifests.

### 8. Lab 8 — Break something and debug it

Try one controlled failure at a time:

1. **Broken health** — change `/health` to return `"status": "broken"`, push, watch readiness probe fail after deploy.
2. **Wrong image digest** — set a bad digest in kustomization, observe `ImagePullBackOff`.
3. **Failed integration** — change `expected-application` in the scenario, watch integration PipelineRun fail.
4. **Failed build** — introduce a syntax error in `app.py`, inspect the failing TaskRun log.

Revert each change after you find the root cause.

## Local smoke test (optional)

```bash
cd applications/konflux-lab/components/hello-api
pip install -r requirements.txt
python src/app.py
curl -s http://127.0.0.1:8080/ | jq .
```

## Related docs

- [konflux-lab learning path](../../docs/konflux-lab-learning-path.md)
- [Konflux visual guide](../../docs/konflux-visual-guide.md)
