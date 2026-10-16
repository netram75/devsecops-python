variable "region" {
  description = "AWS region for every resource"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for resources and tags"
  type        = string
  default     = "gearloop"
}

variable "environment" {
  description = "Environment name used in resource names and tags"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "One public subnet per AZ (load balancers, NAT gateway)"
  type        = list(string)
  default     = ["10.42.0.0/20", "10.42.16.0/20"]

  validation {
    condition     = length(var.public_subnet_cidrs) >= 2
    error_message = "EKS needs subnets in at least two availability zones."
  }
}

variable "private_subnet_cidrs" {
  description = "One private subnet per AZ (worker nodes)"
  type        = list(string)
  default     = ["10.42.128.0/20", "10.42.144.0/20"]

  validation {
    condition     = length(var.private_subnet_cidrs) >= 2
    error_message = "EKS needs subnets in at least two availability zones."
  }
}

variable "enable_nat_gateway" {
  description = "Create a NAT gateway so private nodes can pull images (costs ~$0.06/h)"
  type        = bool
  default     = true
}

variable "cluster_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.35"
}

variable "api_allowed_cidrs" {
  description = "CIDRs allowed to reach the public EKS API endpoint (set to your IP/32)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  description = "Instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}

variable "node_disk_size" {
  description = "Root volume size (GiB) for worker nodes"
  type        = number
  default     = 20
}
