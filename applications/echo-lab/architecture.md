# echo-lab architecture

Minimal Konflux learning application: one Python API, one component, one deployable unit.

## Runtime

| Object | Purpose |
|--------|---------|
| `echo-api` Deployment | Runs the Flask container on port 8080 |
| `echo-api` Service | Cluster DNS `echo-api:8080` |
| `echo-api` Route | Public HTTPS URL for Lab 7 |

## HTTP contract

| Endpoint | Response |
|----------|----------|
| `GET /` | `{"status":"ok","application":"echo-lab"}` |
| `GET /health` | `{"status":"ok","service":"echo-api"}` |
| `GET /echo?msg=hello` | `{"echo":"hello"}` |

## Konflux model

```mermaid
flowchart LR
    App["Application<br/>echo-lab"] --> Comp["Component<br/>echo-api"]
    Comp --> PR["PipelineRun<br/>build"]
    PR --> TR["TaskRuns<br/>clone, buildah, scan..."]
    TR --> Img["Image digest<br/>Quay"]
    Img --> Snap["Snapshot"]
    Snap --> ITS["IntegrationTestScenario<br/>verify-echo-api"]
    ITS --> ITR["Integration PipelineRun"]
    Snap --> Dep["OpenShift Deployment"]
    Dep --> Route["Route"]
```

| Konflux concept | This repo |
|-----------------|-----------|
| Application | `echo-lab` — product boundary |
| Component | `echo-api` — buildable unit under `components/echo-api/` |
| PipelineRun | `.tekton/echo-lab-echo-api-*.yaml` (build on push/PR) |
| TaskRun | Child runs of the build PipelineRun (`git-clone`, `buildah`, …) |
| Snapshot | Immutable record of `echo-api` image digest after build |
| IntegrationTestScenario | `integration/verify-echo-api.yaml` |
| OpenShift Deployment | `deploy/openshift/echo-api.yaml` |
| Route | `deploy/openshift/route.yaml` |

## Build and deploy flow

1. Push code under `components/echo-api/`.
2. Pipeline-as-Code creates a build `PipelineRun`.
3. Tekton tasks build and push `echo-api` to Quay.
4. Konflux creates a `Snapshot` with the image digest.
5. Integration Service runs `echo-lab-verify-echo-api` against the Snapshot.
6. You deploy the digest to a dev namespace and open the Route.

## Intentional omissions

No frontend, database, auth, GitOps, or multi-component coordination — only the Konflux primitives you need to learn.
