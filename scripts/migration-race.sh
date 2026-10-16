#!/usr/bin/env bash
# Create an empty database, start 3 parallel migration pods, show who migrated.
set -euo pipefail
NS=${NS:-gearloop}
IMAGE=$(kubectl -n "$NS" get deploy gearloop-backend -o jsonpath='{.spec.template.spec.containers[0].image}')
kubectl -n "$NS" delete job migration-race --ignore-not-found --wait
kubectl -n "$NS" exec gearloop-postgres-0 -- sh -c \
  'dropdb -U "$POSTGRES_USER" --if-exists gearloop_race && createdb -U "$POSTGRES_USER" gearloop_race'
sed "s#BACKEND_IMAGE#$IMAGE#" "$(dirname "$0")/../k8s/jobs/migration-race.yaml" | kubectl -n "$NS" apply -f -
kubectl -n "$NS" wait --for=condition=complete job/migration-race --timeout=180s
for pod in $(kubectl -n "$NS" get pods -l app=migration-race -o name); do
  echo "--- $pod"
  kubectl -n "$NS" logs "$pod"
done
echo "pods that ran migration 0001: $(kubectl -n "$NS" logs -l app=migration-race --tail=-1 | grep -c 'Running upgrade  -> 0001')"
