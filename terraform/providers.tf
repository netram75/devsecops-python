# Credentials come from the environment (AWS_PROFILE or AWS_ACCESS_KEY_ID/...),
# never from this repository.
provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

locals {
  name = "${var.project}-${var.environment}"
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = "github.com/netram75/devsecops-python"
  }
}
