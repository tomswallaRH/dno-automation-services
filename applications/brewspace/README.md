# brewspace

`brewspace` is a minimal microservices-style learning application for Konflux.

It intentionally contains two components:

- `api`: a Flask service that exposes `GET /health`
- `frontend`: a static web UI served by NGINX that calls the API

Use this app to understand Konflux concepts in a realistic but small setup:

- Application and Component boundaries
- Build execution and image outputs
- Snapshot creation and usage
- Integration test wiring
- Pipeline orchestration in Konflux

## Layout

- `components/api/`: Flask API component
- `components/frontend/`: static frontend component
- `integration/`: integration test scenario examples
- `pipelines/`: learning-focused Konflux pipeline definition
- `architecture.md`: service and CI/CD architecture
- `konflux-learning-guide.md`: concept walkthrough and workflow
- `../../docs/learning-labs/`: hands-on Konflux labs (Jenkins → Konflux mindset)

## Deploy on OpenShift

Konflux tenant namespaces (for example `sfathii-tenant`) are usually reserved for Application and Component metadata and PipelineRuns — they often **cannot** host arbitrary Deployments. Use a **development namespace** where `oc auth can-i create deployments.apps` is `yes`, or ask an admin to apply the manifests.

1. Build **both** images in Konflux (push pipelines produce Quay references).
2. Point Kustomize at real tags or digests (replace placeholder `latest`):

```bash
cd applications/brewspace/deploy/openshift
kustomize edit set image brewspace-api=quay.io/redhat-user-workloads/<tenant>/<component>@sha256:<digest>
kustomize edit set image brewspace-frontend=quay.io/redhat-user-workloads/<tenant>/<component>@sha256:<digest>
oc apply -k . -n <your-namespace>
```

3. Open the **frontend** Route URL (`brewspace-frontend`). The UI loads `/health` via NGINX proxy to `brewspace-api` (same namespace). Optional Route `brewspace-api` exposes the API directly (for debugging).

Pull secrets: your namespace must be allowed to pull from `quay.io/redhat-user-workloads` (Konflux often links workload namespaces automatically; tenant namespaces may differ.)
