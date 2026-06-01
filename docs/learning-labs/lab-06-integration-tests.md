# Lab 06 — Integration Tests

## Objective

Understand **IntegrationTestScenario** resources `brewspace-verify-api` and `brewspace-verify-frontend`, observe them run against a **Snapshot**, and practice analyzing failures like a Konflux engineer (not by re-running an entire Jenkins pipeline blindly).

## Prerequisites

- [Lab 05](lab-05-understand-snapshots.md): Snapshot exists with component digests.
- Git manifests:
  - `applications/brewspace/integration/verify-api.yaml`
  - `applications/brewspace/integration/verify-frontend.yaml`
- Application `brewspace` in Konflux.

## Jenkins → Konflux framing

| Jenkins | Konflux integration |
|---------|---------------------|
| Downstream job `test-after-build` | Integration Service triggers PipelineRun from Snapshot |
| Tests use `latest` image | Tests use **digest from Snapshot** |
| Test logic in Jenkinsfile | `IntegrationTestScenario` + resolver pipeline in Git |
| Failed stage blocks deploy (maybe) | Failed scenario blocks snapshot acceptance / promotion |

---

## Scenarios in this repo

### verify-api (`brewspace-verify-api`)

| Field | Value |
|-------|-------|
| Kind | `IntegrationTestScenario` |
| Application | `brewspace` |
| Git resolver path | `applications/brewspace/integration/verify-api.yaml` |
| Param | `expected-status: ok` |
| Intent | Validate API health behavior from built API image |

### verify-frontend (`brewspace-verify-frontend`)

| Field | Value |
|-------|-------|
| Name | `brewspace-verify-frontend` |
| Param | `expected-text: API Status: OK` |
| Intent | Validate frontend can reach API (cross-component behavior) |

**Note:** Update `resolverRef.params.url` to your real Git remote when onboarding scenarios in a live cluster.

---

## Step-by-step instructions

### 1. Register integration scenarios

**UI:** Application **brewspace** → **Integration tests** → **Add test** → import from Git or paste scenario YAML.

**CLI:**

```bash
oc apply -f applications/brewspace/integration/verify-api.yaml -n <tenant-namespace>
oc apply -f applications/brewspace/integration/verify-frontend.yaml -n <tenant-namespace>
```

### 2. Run verify-api (observe)

After a new Snapshot is created:

1. UI: **Integration tests** → `brewspace-verify-api` → view runs linked to Snapshot.
2. CLI:

```bash
oc get integrationtestscenario -n $NS
oc get pipelinerun -n $NS -l appstudio.openshift.io/snapshot 2>/dev/null
# Or filter by integration labels your cluster uses:
oc get pipelinerun -n $NS | grep -i verify
```

3. Open integration PipelineRun logs; identify which image digest was deployed/tested.

### 3. Run verify-frontend (observe)

Repeat for `brewspace-verify-frontend`. Frontend test implies UI or HTTP check expecting **API Status: OK** (matches `index.html`).

### 4. Controlled failure — API (learning exercise)

Temporarily break API health in a **branch/PR** (do not merge to main unless you will revert):

```python
# app.py — lab exercise only
return jsonify({'status': 'broken', 'service': 'brewspace-api'}), 200
```

- Merge or build so Snapshot gets bad digest.
- Watch `brewspace-verify-api` fail.
- **Analyze:** which TaskRun failed? Assertion on `expected-status: ok`?

Revert after exercise.

### 5. Controlled failure — frontend (learning exercise)

Simulate frontend/API disconnect:

- Deploy frontend without API in test fixture, **or**
- Change `index.html` to show `API Status: FAIL` while API is healthy.

Observe `brewspace-verify-frontend` failure; determine if failure is **wiring** vs **build**.

### 6. Analyze failures (checklist)

| Step | Action |
|------|--------|
| 1 | Identify Snapshot ID under test |
| 2 | List component digests in Snapshot |
| 3 | Open integration PipelineRun → failed TaskRun |
| 4 | Read log: HTTP status, JSON body, missing service |
| 5 | Compare to unit behavior: `curl /health` on API image |
| 6 | Decide: bad **code**, bad **test**, or bad **scenario config** |
| 7 | Fix in Git; trigger new component build → new Snapshot → re-test |

### 7. Jenkins comparison write-up

Answer: “In Jenkins I would have caught this in stage X”—map X to Konflux **integration PipelineRun** and note you would not redeploy `:latest` without a new Snapshot.

---

## Expected Konflux UI view

| UI area | Expected |
|---------|----------|
| Integration tests list | `brewspace-verify-api`, `brewspace-verify-frontend` |
| Per Snapshot | Pass/fail badges per scenario |
| Pipeline run (integration) | Different label/type than `build` PipelineRuns |
| Scenario detail | Git resolver URL, pathInRepo, params |

### Expected UI screenshots

| # | Filename | Capture |
|---|----------|---------|
| 1 | `16-integration-scenarios.png` | Both scenarios registered |
| 2 | `17-verify-api-pass.png` | Green run on snapshot |
| 3 | `18-verify-api-fail.png` | Failed run with log snippet (from exercise) |

---

## Expected Tekton resources

| Resource | Type / notes |
|----------|----------------|
| `IntegrationTestScenario` | `brewspace-verify-api`, `brewspace-verify-frontend` |
| `PipelineRun` | Created by Integration Service; not the same as `brewspace-api-on-push` |
| Labels | Often reference application + snapshot name |
| `TaskRun` | Depends on scenario pipeline (cluster resolver) |

```bash
oc get integrationtestscenario -n $NS
oc describe integrationtestscenario brewspace-verify-api -n $NS
```

Build PipelineRuns (Lab 03) label `pipelines.appstudio.openshift.io/type: build`. Integration runs use integration-specific typing/labels per platform version.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Scenario never runs | Not bound to application / missing snapshot | Register scenario; wait for Snapshot |
| Always skipped | Scenario optional / context mismatch | Check `spec.contexts` |
| Wrong Git revision | `resolverRef` points to example-org | Update URL to your fork |
| Pass build, fail integration | Runtime wiring (frontend→api) | Review nginx proxy + test harness |
| Fail both scenarios | API digest broken | Fix `app.py`, rebuild api component |
| Stale pass | Old Snapshot | Confirm testing **latest** snapshot row |

---

## Quiz questions

1. What Konflux object triggers integration tests after builds?

2. **Short answer:** Why run `verify-frontend` if `verify-api` already passed?

3. Param `expected-status: ok` belongs to which scenario?

4. **Scenario:** Integration failed but manual `oc run` of the image works. Name two explanations.

5. **Compare:** Jenkins downstream job trigger vs Integration Service—what is the shared input artifact?

6. **True/false:** Integration tests should use Quay `:latest` tag for speed.  
   **Answer:** False

7. **Reflection:** Where is the “test definition” stored in Konflux vs your Jenkinsfile?

---

## Next lab

→ [Lab 07 — Release and Promotion](lab-07-release-and-promotion.md)
