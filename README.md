# dno-automation-services

Konflux automation manifests and Pipelines-as-Code templates for this repository.

## Repository layout

| Path | Purpose |
|------|---------|
| `.tekton/` | PaC `PipelineRun` templates for push and pull request builds. |
| `applications/` | Application-level manifests and supporting resources. |
| `applications/konflux-lab/` | Minimal Konflux learning app (start here). See [learning path](docs/konflux-lab-learning-path.md). |
| `Containerfile` | Default container build definition used by PaC templates. |
