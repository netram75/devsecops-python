#!/usr/bin/env bash
# Drive traffic through the Ingress so the HPA scales the backend and Grafana has data.
#   WORKERS=16 DURATION=240 scripts/load-test.sh
# Mostly reads, plus a few reservation attempts that the rules refuse (409/422),
# so the "rule rejections" panel has something to show.
set -uo pipefail
BASE=${BASE:-http://127.0.0.1}
HOST=${HOST_HEADER:-gearloop.local}
WORKERS=${WORKERS:-16}
DURATION=${DURATION:-240}
NS=${NS:-gearloop}

worker() {
  local end=$((SECONDS + DURATION)) n=0
  while [ $SECONDS -lt $end ]; do
    for path in /api/stats /api/assets /api/loans /api/activity /api/info; do
      curl -s -o /dev/null -H "Host: $HOST" "$BASE$path"
    done
    n=$((n + 1))
    if [ $((n % 10)) -eq 0 ]; then
      # overlapping reservation on whatever asset 1 is: refused by the API
      curl -s -o /dev/null -H "Host: $HOST" -H 'Content-Type: application/json' -X POST "$BASE/api/loans" \
        -d '{"asset_id":1,"borrower_name":"Load Test","borrower_roll":"24LT00001","borrower_email":"lt@campus.example","start_date":"2000-01-01","due_date":"2000-01-02"}'
    fi
  done
}

echo "load: $WORKERS workers x ${DURATION}s against $BASE (Host: $HOST)"
for _ in $(seq "$WORKERS"); do worker & done

# sample the HPA while the load runs, and for 2 minutes after it stops
end=$((SECONDS + DURATION + 120))
while [ $SECONDS -lt $end ]; do
  printf '%s  ' "$(date +%T)"
  kubectl -n "$NS" get hpa gearloop-backend --no-headers \
    -o custom-columns=TARGETS:.status.currentMetrics[0].resource.current.averageUtilization,REPLICAS:.status.currentReplicas,DESIRED:.status.desiredReplicas \
    | awk '{printf "cpu=%s%%  replicas=%s  desired=%s\n", $1, $2, $3}'
  sleep 15
done
wait
