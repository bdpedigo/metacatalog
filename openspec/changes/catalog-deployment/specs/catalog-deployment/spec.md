## ADDED Requirements

### Requirement: Helm chart for catalog service
The system SHALL have a Helm chart in `cave-helm-charts/charts/catalog/` providing a Kubernetes Deployment (with cloudsql-proxy sidecar), Service, Ingress (path `/catalog`), ConfigMap, Secrets, and HPA following existing CAVE chart conventions.

#### Scenario: Deploying the catalog service
- **WHEN** an operator runs `helmfile apply` with catalog values configured
- **THEN** the catalog service SHALL be deployed to the GKE cluster with correct environment variables, resource limits, ingress routing at `/catalog`, and a cloudsql-proxy sidecar connected to the shared Cloud SQL instance

#### Scenario: Rolling update with zero downtime
- **WHEN** a new catalog image is deployed via Helm upgrade
- **THEN** the system SHALL perform a rolling update with readiness probes ensuring zero downtime

#### Scenario: Database migrations on deploy
- **WHEN** the catalog pod starts
- **THEN** the entrypoint script SHALL run `alembic upgrade head` before starting uvicorn, ensuring the schema is always up to date

### Requirement: Cloud SQL database on shared instance
The Terraform `local_infrastructure` module SHALL create a `cave_catalog` database on the existing Cloud SQL instance used by MaterializationEngine and AnnotationEngine.

#### Scenario: Provisioning catalog database
- **WHEN** an operator applies the Terraform module
- **THEN** a `cave_catalog` database SHALL exist on the shared Cloud SQL instance, accessible via the existing cloudsql service account

### Requirement: Service account with per-bucket IAM for credential vending
The Terraform `local_kubernetes` module SHALL provision a GCP service account for the catalog with `roles/storage.objectViewer` on each bucket listed in `catalog_managed_buckets`. The SA key SHALL be stored in Secret Manager following the existing CAVE pattern.

#### Scenario: Catalog pod can generate downscoped tokens
- **WHEN** the catalog pod runs with its SA key mounted
- **THEN** the catalog service SHALL be able to generate Credential Access Boundary tokens (via self-downscoping) for managed GCS URIs without needing `serviceAccountTokenCreator`

#### Scenario: Adding a new managed bucket
- **WHEN** an operator adds a bucket to `catalog_managed_buckets` and applies Terraform
- **THEN** the catalog SA SHALL receive `objectViewer` on that bucket, enabling credential vending for assets stored there

### Requirement: AFIS integration
The catalog service URL SHALL be registered in AnnotationFrameworkInfoService's datastack configuration as `catalog_url` so CAVEclient can auto-discover the endpoint.

#### Scenario: CAVEclient discovers catalog URL
- **WHEN** a CAVEclient instance connects to a datastack that has `catalog_url` configured in AFIS
- **THEN** the client SHALL auto-configure `CatalogClient` with that URL

#### Scenario: Graceful degradation when catalog is not configured
- **WHEN** a datastack does not have `catalog_url` in AFIS
- **THEN** CAVEclient SHALL raise a clear error when the user tries to access `client.catalog`

### Requirement: Datastack configuration
The catalog Helm chart SHALL accept a `datastacks` list in values (rendered as the `DATASTACKS` environment variable), mirroring the materializationengine pattern. The Terraform template SHALL inject the appropriate datastack name(s) for the deployment.

#### Scenario: Catalog knows its datastacks
- **WHEN** the catalog is deployed with `datastacks: ["minnie65_phase3"]`
- **THEN** the catalog service SHALL only serve requests for the configured datastacks

### Requirement: Deployment documentation
The catalog repository SHALL include deployment documentation covering: required environment variables, IAM roles, managed bucket onboarding, and Helmfile values example.

#### Scenario: New operator deploys catalog
- **WHEN** an operator follows the deployment documentation
- **THEN** they SHALL be able to deploy the catalog to a new CAVE environment without additional guidance
