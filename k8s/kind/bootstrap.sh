#!/usr/bin/env bash
# Build the whole local platform on kind:
#   cluster (1 control-plane + 2 workers) -> ingress-nginx -> metrics-server
#   -> kube-prometheus-stack -> Argo CD -> GearLoop namespaces + DB secrets
# Usage: k8s/kind/bootstrap.sh            (idempotent; re-run to repair)
set -euo pipefail
cd "$(dirname "$0")/../.."

CLUSTER=${CLUSTER:-gearloop}
# Docker Desktop forwards host ports to a dual-stack container's IPv6 address,
# but kind's hostPort rules are IPv4 only, so 127.0.0.1:80 was reset. An
# IPv4-only network for the nodes avoids that.
NETWORK=${NETWORK:-kind-ipv4}
INGRESS_NGINX=controller-v1.15.1
KPS_VERSION=92.8.0
ARGOCD_VERSION=10.10.5

step() { printf '\n==> %s\n' "$*"; }

step "docker network $NETWORK (IPv4 only)"
docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK" --subnet 172.30.0.0/16

step "kind cluster $CLUSTER"
if ! kind get clusters | grep -qx "$CLUSTER"; then
  KIND_EXPERIMENTAL_DOCKER_NETWORK=$NETWORK kind create cluster --name "$CLUSTER" \
    --config k8s/kind/kind-cluster.yaml --wait 180s
fi
kubectl config use-context "kind-$CLUSTER"

step "ingress-nginx $INGRESS_NGINX"
kubectl apply -f "https://raw.githubusercontent.com/kubernetes/ingress-nginx/$INGRESS_NGINX/deploy/static/provider/kind/deploy.yaml"
kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=300s

step "helm repositories"
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null 2>&1 || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
helm repo update >/dev/null

step "metrics-server (HPA needs it; kind kubelets use self-signed certs)"
helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system \
  --set 'args={--kubelet-insecure-tls}' --wait

step "namespaces (Pod Security: restricted)"
kubectl apply -f k8s/namespace.yaml
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

step "secrets (generated here, never stored in Git)"
if ! kubectl -n monitoring get secret grafana-admin >/dev/null 2>&1; then
  kubectl -n monitoring create secret generic grafana-admin \
    --from-literal=admin-user=admin --from-literal=admin-password="$(openssl rand -hex 12)"
fi
if ! kubectl -n gearloop get secret gearloop-db >/dev/null 2>&1; then
  pw=$(openssl rand -hex 16)
  for ns in gearloop gearloop-staging; do
    kubectl -n "$ns" create secret generic gearloop-db --from-literal=db-password="$pw"
  done
fi

step "kube-prometheus-stack $KPS_VERSION"
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack --version "$KPS_VERSION" \
  -n monitoring -f monitoring/kube-prometheus-stack-values.yaml --wait --timeout 15m

step "Argo CD $ARGOCD_VERSION"
helm upgrade --install argocd argo/argo-cd --version "$ARGOCD_VERSION" \
  -n argocd --create-namespace -f gitops/argocd-values.yaml --wait --timeout 10m

step "Argo CD application (GitOps for the gearloop namespace)"
kubectl apply -f gitops/argocd-application.yaml

cat <<MSG

Done. Add to /etc/hosts:  127.0.0.1 gearloop.local staging.gearloop.local argocd.gearloop.local grafana.gearloop.local prometheus.gearloop.local
  Grafana admin password:  kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
  Argo CD admin password:  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
MSG
