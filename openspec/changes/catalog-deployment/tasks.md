## 1. Helm Chart (`cave-helm-charts/charts/catalog/`)

- [x] 1.1 Create `Chart.yaml` with chart metadata (name: catalog, apiVersion: v2)
- [x] 1.2 Create `values.yaml` with `catalog:` block (tag, datastacks, secretFiles, authEnabled, logLevel, resources, replicas), `cloudsql:` block (sqlInstanceName, googleSecret, username, password, database, port), and standard `cluster:` block
- [x] 1.3 Create `templates/deployment.yaml`: catalog container (uvicorn on port 80, env from ConfigMap, volume mounts for secrets, readiness/liveness probes on /health) + cloudsql-proxy sidecar
- [x] 1.4 Create `templates/configmap.yaml`: renders DATABASE_URL, AUTH_SERVICE_URL, MAT_ENGINE_URL, CAVECLIENT_SERVER_ADDRESS, DATASTACKS, LOG_LEVEL (all derived from values)
- [x] 1.5 Create `templates/secret.yaml`: google-secret.json and cave-secret.json from `catalog.secretFiles`
- [x] 1.6 Create `templates/cloudsql_secret.yaml`: cloudsql proxy credentials
- [x] 1.7 Create `templates/service.yaml`: NodePort service on port 80
- [x] 1.8 Create `templates/ingress.yaml`: nginx ingress, path `/catalog`, shared host
- [x] 1.9 Create `templates/hpa.yaml`: basic HPA (1-3 replicas, 75% CPU target)

## 2. Terraform: Cloud SQL Database (`local_infrastructure`)

- [x] 2.1 Add `google_sql_database` resource for `cave_catalog` on the existing Cloud SQL instance in `postgres.tf`

## 3. Terraform: Service Account & IAM (`local_kubernetes`)

- [x] 3.1 Add `google_service_account` for catalog (`catalog-{prefix}-{workspace}`)
- [x] 3.2 Add per-bucket `google_storage_bucket_iam_member` with `roles/storage.objectViewer` for each bucket in `catalog_managed_buckets` variable
- [x] 3.3 Add SA key + Secret Manager secret (following existing pattern)
- [x] 3.4 Add `catalog_managed_buckets` variable to module variables

## 4. Terraform: Helm Values Template (`local_kubernetes`)

- [x] 4.1 Create `templates/catalog.tpl` rendering catalog.defaults.yaml (secretFiles with `ref+gcpsecrets://` refs, datastacks, sql instance name)
- [x] 4.2 Add `local_file` resource in `helm_templates.tf` for `catalog.defaults.yaml`
- [x] 4.3 Add catalog release entry to `templates/helmfile.tpl`

## 5. AFIS Integration

- [x] 5.1 Add `catalog_url` field to the AFIS datastack configuration schema
- [x] 5.2 Ensure CAVEclient reads `catalog_url` from info service and passes it to `CatalogClient` initialization
- [x] 5.3 Verify graceful error handling when `catalog_url` is not configured for a datastack

## 6. Catalog Docker Image

- [x] 6.1 Add `entrypoint.sh` to catalog repo: runs `uv run alembic upgrade head` then `exec uv run uvicorn cave_catalog.app:create_app --factory --host 0.0.0.0 --port 80`
- [x] 6.2 Update Dockerfile: change `EXPOSE` from 8000 to 80, copy `entrypoint.sh`, set `CMD ["./entrypoint.sh"]`
- [x] 6.3 Add `cloudbuild.yaml` to catalog repo (following ME pattern): build image, push to GCR (`gcr.io/$PROJECT/cave-catalog:$TAG`) and Docker Hub (`caveconnectome/cave-catalog:$TAG`)

## 7. Release Workflow & Version Management (catalog repo)

- [x] 7.1 Add `bump-my-version` to dev dependencies and `[tool.bumpversion]` config in `pyproject.toml`
- [x] 7.2 Create `.github/workflows/release.yml` (matching ME pattern):
  - Trigger: `workflow_dispatch` with `part` input (major/minor/patch) and `dry-run` toggle
  - `bump` job: checkout, `uv sync --frozen --dev`, `uv run bump-my-version bump $part`, `git push --follow-tags`, create GitHub Release
  - `update-chart` job: checkout `cave-helm-charts` via `HELM_CHART_UPDATE_TOKEN`, update `charts/catalog/Chart.yaml`, push
- [ ] 7.3 Ensure `HELM_CHART_UPDATE_TOKEN` PAT is available as a repo secret on `cave-catalog` (reuse existing org secret from ME)
- [ ] 7.4 Set up GCP Cloud Build trigger on the catalog repo for `v*` tags (requires GCP project admin)

## 8. Documentation

- [x] 9.1 Write deployment documentation: prerequisites, environment variables table, IAM roles needed, Helmfile values example
- [x] 9.2 Document the managed bucket onboarding procedure (terraform variable update + apply)
- [x] 9.3 Document the release procedure: how to trigger a release, what happens automatically, how to verify
