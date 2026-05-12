## Why

The catalog service runs locally but has no production deployment path. It needs a Helm chart, Terraform infrastructure (Cloud SQL database, IAM), integration with AnnotationFrameworkInfoService for datastack URL discovery, and deployment documentation so it can be rolled out to the CAVE GKE cluster alongside existing services.

## What Changes

- Create a Helm chart for the catalog service (Deployment with cloudsql-proxy sidecar, Service, Ingress, ConfigMap, Secrets, HPA) following existing cave-helm-charts patterns.
- Add Terraform resources to `local_kubernetes` for the catalog service account, per-bucket IAM bindings, SA key in Secret Manager, and a Helm values template. Add a `cave_catalog` database to the existing Cloud SQL instance in `local_infrastructure`.
- Register the catalog service URL in AnnotationFrameworkInfoService's datastack configuration so CAVEclient can auto-discover the endpoint.
- Write deployment documentation covering environment variables, required IAM roles, and Helmfile values.

## Capabilities

### New Capabilities

- `catalog-deployment`: Helm chart, Terraform infrastructure, AFIS integration, and deployment documentation for production rollout of the catalog service.

### Modified Capabilities

<!-- None — deployment is infrastructure-only. -->

## Impact

- `submodules/cave-helm-charts/charts/` — new `catalog/` chart directory
- `submodules/terraform-google-cave/modules/local_infrastructure/` — new `cave_catalog` database on existing Cloud SQL instance
- `submodules/terraform-google-cave/modules/local_kubernetes/` — new service account, IAM, Helm values template, helmfile entry
- `submodules/AnnotationFrameworkInfoService/` — add `catalog_url` to datastack config schema
- Documentation: deployment guide in catalog repo
