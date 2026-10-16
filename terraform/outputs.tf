output "region" {
  value = var.region
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "availability_zones" {
  value = local.azs
}

output "nat_gateway_id" {
  value = try(aws_nat_gateway.main[0].id, null)
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "cluster_version" {
  value = aws_eks_cluster.main.version
}

output "node_group_status" {
  value = aws_eks_node_group.main.status
}

output "kubeconfig_command" {
  description = "Run this after apply to point kubectl at the cluster"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${aws_eks_cluster.main.name}"
}
