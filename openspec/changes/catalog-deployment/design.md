## Context

The catalog service runs locally with `docker compose` and `uvicorn` for development. It needs production deployment infrastructure on the existing CAVE GKE cluster. Existing CAVE services (AnnotationEngine, MaterializationEngine, PyChunkedGraph, etc.) follow a common pattern: Helm charts in `cave-helm-charts`, Terraform modules in `terraform-google-cave`, and service URL registration in AnnotationFrameworkInfoService (AFIS).

The relevant infrastructure repos are:
- `cave-helm-charts` — Helm chart definitions for all CAVE services
- `terraform-google-cave` — Terraform modules split into `local_infrastructure` (Cloud SQL, VPC, Redis, buckets), `local_cluster` (GKE, node pools), and `local_kubernetes` (service accounts, IAM, Helm value templates)
- `AnnotationFrameworkInfoService` (AFIS) — central service discovery for CAVEclient

## Goals / Non-Goals

**Goals:**
- Deploy the catalog service to the existing CAVE GKE cluster following established patterns
- Provision a `cave_catalog` database on the existing shared Cloud SQL instance
- Configure IAM for credential vending (per-bucket `storage.objectViewer`)
- Register the catalog URL in AFIS so CAVEclient can auto-discover it
- Document all required environment variables, IAM roles, and deployment steps

**Non-Goals:**
- Multi-region or HA deployment (single region, matching existing CAVE infra)
- Custom autoscaling policies (basic HPA is sufficient for this lightweight API)
- S3/AWS infrastructure (deferred with S3 credential backend)
- Workload Identity migration (follow existing SA key pattern for now)

## Decisions

### 1. Shared Cloud SQL instance, separate database

**Decision**: The catalog gets a new `cave_catalog` database on the existing Cloud SQL instance (shared with MaterializationEngine/AnnotationEngine). No dedicated instance.

**Alternatives considered**:
- Own Cloud SQL instance — operational isolation but adds ~$10/month cost and operational overhead for a service with a trivially simple schema.
- Per-datastack databases (matching ME/AE pattern) — unnecessary complexity for a single-table schema.

**Rationale**: The catalog has minimal DB load (single table, low write throughput). Sharing the existing instance avoids cost and reduces moving parts. The existing `cloudsql` service account and proxy sidecar pattern can be reused directly. A `google_sql_database` resource is all that's needed in terraform.

### 2. Helm chart in cave-helm-charts

**Decision**: Add a `catalog/` chart to `cave-helm-charts/charts/` following the existing chart structure: Deployment (with cloudsql-proxy sidecar), Service, Ingress, ConfigMap, Secrets. Ingress path: `/catalog`. The chart accepts a `datastacks` list (mirroring the materializationengine pattern).

**Chart structure:**
```
charts/catalog/
  Chart.yaml
  values.yaml
  templates/
    deployment.yaml      # catalog container + cloudsql-proxy sidecar
    service.yaml         # NodePort → 80
    ingress.yaml         # path: /catalog
    configmap.yaml       # DATABASE_URL, AUTH_SERVICE_URL, MAT_ENGINE_URL, DATASTACKS, etc.
    secret.yaml          # google-secret.json, cave-secret.json
    cloudsql_secret.yaml # cloudsql proxy credentials
    hpa.yaml             # basic HPA (1-3 replicas)
```

**Rationale**: Consistency with existing deployment patterns. Helmfile manages releases. No KEDA needed (lightweight API, not queue-driven). No uwsgi-exporter sidecar (uvicorn, not uwsgi).

### 3. Service account with SA key (existing pattern)

**Decision**: Create a dedicated GCP service account (`catalog-{prefix}-{workspace}`) with a JSON key stored in Secret Manager. Mount as `google-secret.json` following the same pattern as all other CAVE services.

**Alternatives considered**:
- Workload Identity (no key files) — cleaner, but no existing CAVE service uses this pattern yet. Would be a divergence that adds deployment complexity for operators unfamiliar with WI. Defer to a future migration that moves all services to WI simultaneously.

**Rationale**: Consistency with existing CAVE services. The credential vending flow (`google.auth.default()` → CAB downscope) works identically whether the underlying credential comes from a key file or Workload Identity.

### 4. Per-bucket IAM for credential vending

**Decision**: The catalog SA gets `roles/storage.objectViewer` on specific managed buckets (not project-wide). Terraform takes a `catalog_managed_buckets` variable listing the buckets.

**How credential vending works:**
1. Catalog SA has `objectViewer` on each managed bucket
2. When a user requests access to an asset, the catalog uses `google.auth.downscoped.Credentials` (Credential Access Boundaries) to mint a short-lived token scoped to just that asset's GCS prefix
3. This is **self-downscoping** via the STS API — the SA narrows its own permissions. No `serviceAccountTokenCreator` role is needed.
4. The vended token expires in 1 hour. Clients should cache it.

**Registration policy:** If a user registers an asset pointing to a bucket the catalog SA can read, `managed=True` and credential vending is available. If the bucket is public, `managed=False` and no vending is needed. If the bucket is private and the SA can't read it, registration is rejected.

**Rationale**: Per-bucket IAM follows the least-privilege principle. The `catalog_managed_buckets` list would typically include the materialization dump bucket. New managed buckets require a terraform apply.

### 5. AFIS integration for service discovery

**Decision**: Add a `catalog_url` field to the AFIS datastack configuration. CAVEclient reads this to auto-configure `CatalogClient`.

**Alternatives considered**:
- Hardcoded URL in CAVEclient — breaks across deployments.
- DNS-based discovery — not how other CAVE services work.

**Rationale**: Follows the same pattern as `mat_engine_url`, `pycg_url`, etc. in AFIS.

### 6. Service-to-service communication via global server

**Decision**: All inter-service URLs are derived from `cluster.globalServer` in the Helm values:
- `AUTH_SERVICE_URL` = `{{ .Values.cluster.globalServer }}/auth`
- `MAT_ENGINE_URL` = `{{ .Values.cluster.globalServer }}/materialize`
- `CAVECLIENT_SERVER_ADDRESS` = `{{ .Values.cluster.globalServer }}`

No additional service-specific URL configuration needed. CAVEclient auto-discovers endpoints via the info service at the global server.

**Rationale**: Matches how other charts derive `AUTH_URI`, `INFO_URL`, etc. The catalog's `mat_proxy.py` uses CAVEclient which handles service discovery. Direct httpx calls in `validation.py` use `MAT_ENGINE_URL` for efficiency.

### 7. Database migrations via entrypoint script

**Decision**: The catalog Docker image uses an entrypoint script that:
1. Runs `alembic upgrade head`
2. Starts `uvicorn`

The catalog's Alembic setup is already fully async — `env.py` uses `async_engine_from_config` with `asyncpg` and wraps the migration run in `asyncio.run()`. No sync database driver is needed. The same `DATABASE_URL` (with `postgresql+asyncpg://`) is used by both the app and Alembic.

**Alternatives considered**:
- Init container — adds complexity, harder to debug, requires a separate image or command override.
- Manual migration step — error-prone, easy to forget during deploys.
- Kubernetes Job — overkill for a single lightweight migration.

**Rationale**: Simplest approach. Alembic's migration lock handles concurrent runs safely when multiple replicas start simultaneously. The catalog's migrations are fast (single table).

### 8. Datastack configuration

**Decision**: The catalog accepts a `DATASTACKS` environment variable (comma-separated or JSON list), configured via Helm values. This mirrors the materializationengine chart's `datastacks` list. Terraform renders this into `catalog.defaults.yaml`.

**Rationale**: Follows the ME pattern. Each local deployment serves one or more datastacks. The terraform template injects the appropriate datastack name(s) for that environment.

### 9. Release pipeline: github-actions[bot] + PAT + tag-based Cloud Build

**Decision**: Use the same release pattern as MaterializationEngine — `github-actions[bot]` identity with a `HELM_CHART_UPDATE_TOKEN` PAT for cross-repo pushes. The full release flow:

1. Developer triggers `release.yml` via manual dispatch (selects major/minor/patch, optional dry-run)
2. `bump-my-version` bumps the version in `pyproject.toml` via `[tool.bumpversion]`, commits, and creates a `v{version}` tag
3. Workflow pushes the commit + tag to `main` with `git push --follow-tags`
4. Workflow creates a GitHub Release
5. A separate `update-chart` job checks out `cave-helm-charts` using `HELM_CHART_UPDATE_TOKEN`, updates `charts/catalog/Chart.yaml`, and pushes
6. GCP Cloud Build triggers on the `v*` tag, builds the Docker image, and pushes to GCR + Docker Hub (`caveconnectome/cave-catalog`)

**Setup required** (one-time):
- Ensure `HELM_CHART_UPDATE_TOKEN` PAT is available as a repo secret on `cave-catalog` (reuse existing org secret from ME)
- Set up GCP Cloud Build trigger for `v*` tags

**Rationale**: Exact same pattern as MaterializationEngine. No GitHub App needed, no branch protection bypass complexity. The `HELM_CHART_UPDATE_TOKEN` PAT already exists for ME and can be reused. Commits are attributed to `github-actions[bot]`.

### 10. Docker image and registry

**Decision**: The catalog image is published to both GCR (`gcr.io/$PROJECT/cave-catalog:$TAG`) and Docker Hub (`caveconnectome/cave-catalog:$TAG`), matching the MaterializationEngine pattern. Cloud Build handles the build on tag push.

**Dockerfile changes for production:**
- Change listen port from 8000 to 80 (matching other CAVE services)
- Add an `entrypoint.sh` that runs migrations then starts uvicorn
- Cloud Build config (`cloudbuild.yaml`) follows ME's pattern

**Rationale**: Dual registry matches existing CAVE convention. The helm charts default to `docker.io/caveconnectome` as the registry.

### 11. Version management with bump-my-version

**Decision**: Use `bump-my-version` to manage versions. Version is tracked in `pyproject.toml` (`version` field). The tool is configured in `[tool.bumpversion]` in `pyproject.toml` and included as a dev dependency.

**Rationale**: Modern successor to `bumpversion`. Single source of truth for the version. Config lives in `pyproject.toml` alongside everything else.

## Risks / Trade-offs

- **[Shared Cloud SQL]** → Couples catalog availability to the shared instance's health. Acceptable given the catalog's minimal DB requirements and the operational cost of running a separate instance.
- **[AFIS schema change]** → Adding `catalog_url` is additive and non-breaking, but requires coordinating the AFIS deployment with the catalog deployment.
- **[Per-bucket IAM maintenance]** → Adding new managed buckets requires a terraform apply to update `catalog_managed_buckets`. This is intentional (explicit > implicit) but adds a step when onboarding new data.
- **[Migration on startup]** → If a migration fails, the pod will crash-loop. This is actually desirable — it surfaces the problem immediately rather than running with a stale schema.
- **[STS latency]** → Credential vending adds ~100-500ms per token exchange. Clients must cache the 1-hour tokens. This is inherent to the CAB approach and well-documented.
