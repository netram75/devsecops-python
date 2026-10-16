# Troubleshooting labs

Three deliberately broken Deployments in the `gearloop-labs` namespace, each diagnosed
and fixed with kubectl only.

```bash
kubectl apply -f troubleshooting/namespace.yaml
kubectl apply -f troubleshooting/lab1-broken-image.yaml -f troubleshooting/lab2-broken-service.yaml -f troubleshooting/lab3-broken-probe.yaml
```

| Lab | Symptom | Diagnose | Root cause | Fix |
|---|---|---|---|---|
| 1 | `ImagePullBackOff` | `kubectl -n gearloop-labs describe pod -l app=lab1-web` → *Failed to pull image ... not found* | tag typo `1.31-alpnie` | `kubectl -n gearloop-labs set image deploy/lab1-web web=nginxinc/nginx-unprivileged:1.31-alpine` |
| 2 | pods `1/1 Running`, but the Service answers nothing | `kubectl -n gearloop-labs get endpointslices -l kubernetes.io/service-name=lab2-web` → no endpoints | selector `app: lab2-wbe` matches no pod | `kubectl -n gearloop-labs patch svc lab2-web -p '{"spec":{"selector":{"app":"lab2-web"}}}'` |
| 3 | pods `Running` but `0/1` Ready | `kubectl -n gearloop-labs describe pod -l app=lab3-web` → *Readiness probe failed: connection refused* on :80 | probe port 80, container listens on 8080 | `kubectl -n gearloop-labs patch deploy lab3-web --type=json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/port","value":8080}]'` |

Clean up: `kubectl delete namespace gearloop-labs`.
