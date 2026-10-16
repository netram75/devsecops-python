#!/usr/bin/env bash
# Run the real Terraform code against the moto AWS emulator (no AWS account, no cost).
#   terraform/emulator/run.sh plan|apply|destroy|all
# Port 5050, because macOS AirPlay already listens on 5000.
set -euo pipefail
cd "$(dirname "$0")/.."

MOTO_IMAGE=motoserver/moto:5.1.22
CONTAINER=gearloop-moto
export AWS_ACCESS_KEY_ID=moto AWS_SECRET_ACCESS_KEY=moto AWS_DEFAULT_REGION=ap-south-1
unset AWS_PROFILE

start_moto() {
  if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    # Moto does not preload AWS managed IAM policies unless asked to.
    docker run -d --name "$CONTAINER" -p 127.0.0.1:5050:5000 \
      -e MOTO_IAM_LOAD_MANAGED_POLICIES=true "$MOTO_IMAGE" >/dev/null
    for _ in $(seq 1 30); do curl -sf http://127.0.0.1:5050/moto-api/ >/dev/null && break; sleep 1; done
  fi
  cp emulator/moto_override.tf.example moto_override.tf
}

case "${1:-all}" in
  plan)    start_moto; terraform init -input=false; terraform plan -out=tfplan ;;
  apply)   start_moto; terraform apply -input=false tfplan ;;
  destroy) start_moto; terraform destroy -auto-approve ;;
  all)     start_moto; terraform init -input=false; terraform plan -out=tfplan
           terraform apply -input=false tfplan; terraform destroy -auto-approve ;;
  stop)    docker rm -f "$CONTAINER"; rm -f moto_override.tf ;;
  *)       echo "usage: $0 plan|apply|destroy|all|stop"; exit 2 ;;
esac
