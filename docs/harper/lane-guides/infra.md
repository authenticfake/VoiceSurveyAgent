## Lane Guide — infra

### Tools

- tests: Infrastructure tests using tools like pytest with moto or localstack, or Kubernetes integration tests where feasible.
- lint: YAML linters and policy-as-code tools such as kube-score or kube-linter for manifests.
- types: Not strongly typed, but configuration schemas validated via JSON Schema or similar.
- security: Trivy for image scanning, kube-bench or equivalent for cluster security baselines.
- build: Terraform or Helm not fully specified here; minimal manifests or charts for API, workers, scheduler.

### CLI Examples

- Local:
  - Use kind or minikube to run local Kubernetes clusters for testing manifests.
  - Apply manifests: `kubectl apply -f k8s/`
- Containerized:
  - Run infra checks in Docker images that contain kubectl, helm, and scanning tools.

### Default Gate Policy

- min coverage: configuration linting and validation executed on all manifests.
- max criticals: no critical security issues from cluster or image scans.
- required checks: manifest validation, image scan, and basic deployment smoke test for non-production clusters.

### Enterprise Runner Notes

- SonarQube: not typically applied to infra code; rely on specialized tools and audits.
- Jenkins or GitHub Actions: pipelines for deploying to EKS should run after application CI succeeds.
- Artifacts: store rendered manifests, Helm charts, and scan reports for audit trails.

### TECH_CONSTRAINTS integration

- air-gap: EKS clusters operate in private subnets with controlled egress; infra tooling must respect network segmentation.
- registries: cluster pulls images from internal registries; image references in manifests should use internal registry URLs.
- secrets: Kubernetes Secrets populated from AWS Secrets Manager via integration controllers or CI processes.