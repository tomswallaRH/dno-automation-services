# Runtime Architecture Diagram

## Diagram

```mermaid
flowchart TB
    subgraph external["External clients"]
        browser["Browser / curl"]
    end

    subgraph ocp["OpenShift namespace (workload)"]
        subgraph routes["Routes (edge TLS)"]
            r_fe["Route brewspace-frontend"]
            r_api["Route brewspace-api<br/>(optional debug)"]
        end

        subgraph svc["Services"]
            s_fe["Service brewspace-frontend<br/>:8080"]
            s_api["Service brewspace-api<br/>:8080"]
        end

        subgraph pods["Pods"]
            subgraph pod_fe["Deployment brewspace-frontend"]
                fe_ctr["Container nginx<br/>static index.html<br/>proxy /health → api"]
            end
            subgraph pod_api["Deployment brewspace-api"]
                api_ctr["Container Flask<br/>GET /health"]
            end
        end
    end

    subgraph images["Container images (from Konflux builds)"]
        img_fe["brewspace-frontend<br/>@sha256:… from Quay"]
        img_api["brewspace-api<br/>@sha256:… from Quay"]
    end

    browser -->|"HTTPS"| r_fe
    browser -.->|"optional"| r_api
    r_fe --> s_fe --> fe_ctr
    r_api -.-> s_api --> api_ctr
    fe_ctr -->|"proxy_pass brewspace-api:8080"| s_api
    s_api --> api_ctr

    img_fe -.->|"image:"| pod_fe
    img_api -.->|"image:"| pod_api
```

## Explanation

At runtime, brewspace runs on OpenShift outside the Konflux tenant namespace. The **frontend** pod serves static HTML on `/` and proxies `/health` to the **API** service via NGINX (`nginx-default.conf`). The **API** pod runs Flask and exposes `GET /health`. **Services** provide cluster DNS (`brewspace-api`, `brewspace-frontend`). **Routes** expose the frontend (primary user entry) and optionally the API for debugging. Container images are the immutable digests built by Konflux and referenced in `kustomization.yaml`—not mutable `:latest` in production.

## How this appears in Konflux UI

Runtime resources are **not** managed inside Konflux UI:

- Konflux shows **built images** and digests on each Component.
- **Snapshots** prove which digests were tested together.
- Deployments, Routes, and Services appear in the **OpenShift console** (Topology, Workloads → Deployments).

To connect UI workflows: copy digest from Component build → `kustomize edit set image` → `oc apply -k applications/brewspace/deploy/openshift`.

## How this maps to Tekton resources

Runtime is **downstream of Tekton**, not Tekton itself:

| Runtime object | Relationship to Tekton |
|----------------|------------------------|
| `Deployment` / `Pod` | Runs image built by build `PipelineRun` (`output-image` param → Quay digest) |
| `Service` | Cluster networking; no Tekton object |
| `Route` | OpenShift ingress; no Tekton object |
| Image pull | Digest from `PipelineRun` results `IMAGE_DIGEST` / Snapshot component status |

Integration test `PipelineRun`s may curl `/health` against test fixtures; production health checks use Kubernetes `readinessProbe` / `livenessProbe` on `/health` (api) and `/` (frontend) in the Deployment manifests.

**Files in this repo:**

- `deploy/openshift/brewspace-api.yaml` — Deployment + Service
- `deploy/openshift/brewspace-frontend.yaml` — Deployment + Service
- `deploy/openshift/routes.yaml` — Routes to both Services
- `deploy/openshift/kustomization.yaml` — image name substitutions for digests
