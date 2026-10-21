# dno-automation-services

Konflux automation manifests and Pipelines-as-Code templates for this repository.

## Repository layout

| Path | Purpose |
|------|---------|
| `.tekton/` | PaC `PipelineRun` templates for push and pull request builds. |
| `applications/` | Application-level manifests and supporting resources. |
| `applications/konflux-lab/` | Minimal Konflux learning app (start here). See [learning path](docs/konflux-lab-learning-path.md). |
| `applications/echo-lab/` | Second from-scratch Konflux learning app (one Application, one Flask Component). See [echo-lab README](applications/echo-lab/README.md). |
| `Containerfile` | Default container build definition used by PaC templates. |
