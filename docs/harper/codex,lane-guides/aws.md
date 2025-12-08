## Lane Guide — aws

### Tools

- tests: Use AWS SDK stubs or local emulators where possible, such as localstack for SQS and S3.
- lint: Policy-as-code for IAM and security groups using tools like Checkov or AWS Config rules.
- types: Infrastructure definitions documented and, if using CDK later, typed via TypeScript or Python.
- security: AWS security best-practices checks, including IAM least privilege and encrypted storage for RDS and Redis.
- build: Not a build lane itself, but ensures AWS resources such as RDS, SQS, and EKS are configured to support the application.

### CLI Examples

- Local:
  - AWS CLI commands to inspect resources: `aws sqs list-queues`, `aws rds describe-db-instances`.
  - Use `aws eks update-kubeconfig` to interact with EKS clusters.
- Containerized:
  - Run AWS CLI in containers with IAM roles or credentials injected securely.

### Default Gate Policy

- min coverage: resource configuration must be reviewed for environments before promoting to higher stages.
- max criticals: no critical AWS security findings from internal audit tools.
- required checks: encryption at rest, network access controls, IAM policies, and logging to CloudWatch enabled for core services.

### Enterprise Runner Notes

- SonarQube: not applicable to AWS resource configuration; rely on AWS-native tools and third-party scanners.
- Jenkins or GitHub Actions: pipelines may include AWS CloudFormation or CDK deploy steps.
- Artifacts: CloudFormation templates, CDK synth outputs, and configuration documents stored in version control or artifact repositories.

### TECH_CONSTRAINTS integration

- air-gap: enforce private networking for databases and caches; only necessary endpoints are allowed via controlled egress.
- registries: ECR or internal registry must be used for container images running on EKS.
- secrets: use AWS Secrets Manager as specified to store and rotate credentials; applications access secrets via IAM roles.