resource "aws_eks_cluster" "main" {
  name     = "${local.name}-eks"
  version  = var.cluster_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    # Control-plane ENIs in all four subnets; nodes only in the private ones.
    subnet_ids              = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = var.api_allowed_cidrs
  }

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true # whoever runs apply can use kubectl
  }

  enabled_cluster_log_types = ["api", "audit"]

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name}-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.private[*].id

  instance_types = var.node_instance_types
  capacity_type  = "ON_DEMAND"
  disk_size      = var.node_disk_size

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    workload = "gearloop"
  }

  # Nodes must not be created before their role can pull images and run the CNI,
  # and must be gone before the policies are detached on destroy.
  depends_on = [
    aws_iam_role_policy_attachment.node,
    aws_route_table_association.private,
  ]

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size] # let the autoscaler own it
  }
}
