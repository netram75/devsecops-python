# Terraform: AWS VPC + EKS for GearLoop

Plain resources (no community modules), so every object is visible in the code.

| File | What it creates |
|---|---|
| `network.tf` | VPC `10.42.0.0/16` (DNS hostnames on), 2 public + 2 private subnets in 2 AZs, internet gateway, 1 NAT gateway + EIP, public/private route tables and associations. Subnets carry the `kubernetes.io/role/elb` / `internal-elb` tags so AWS load balancers land in the right tier. |
| `iam.tf` | EKS cluster role (`AmazonEKSClusterPolicy`) and node role (worker, CNI, ECR read-only). |
| `eks.tf` | `aws_eks_cluster` (1.35, public + private endpoint, API restricted by `api_allowed_cidrs`, creator gets admin) and a managed node group (2 x t3.medium in the private subnets, min 1 / max 3). |
| `outputs.tf` | VPC/subnet IDs, cluster name/endpoint, the `aws eks update-kubeconfig` command. |

22 resources in total. `terraform.tfvars.example` documents every input; the real
`terraform.tfvars`, state files and plans are git-ignored. Credentials only ever come
from the environment (`AWS_PROFILE` or `AWS_ACCESS_KEY_ID`).

## Real AWS

```bash
cp terraform.tfvars.example terraform.tfvars   # put your IP in api_allowed_cidrs
AWS_PROFILE=personal terraform init
AWS_PROFILE=personal terraform plan -out=tfplan
AWS_PROFILE=personal terraform apply tfplan   # ~15 min, about $0.20/h while it runs
aws eks update-kubeconfig --region ap-south-1 --name gearloop-prod-eks --profile personal
AWS_PROFILE=personal terraform destroy -auto-approve
```

## Emulator (what this submission ran)

No personal AWS account was available, so the same code was run against the
[moto](https://github.com/getmoto/moto) AWS emulator:

```bash
terraform/emulator/run.sh plan      # starts moto on 127.0.0.1:5050 and plans
terraform/emulator/run.sh apply
terraform/emulator/run.sh destroy
terraform/emulator/run.sh stop
```

`run.sh` copies `emulator/moto_override.tf.example` to `moto_override.tf`, which
Terraform merges over `providers.tf` (fake credentials + local endpoints). The
`*_override.tf` pattern is git-ignored, so the committed code is the real-AWS code.

Known emulator differences: moto returns no real nodes (so there is no
`kubectl get nodes`), and its DescribeNodegroup reports an SSH `remote_access`
block and version 1.19 that the code never set, so a second `plan` on moto wants
to replace the node group. Neither happens on AWS.
