#### 使用 Helm 部署 dashboard
---
###### kubenetes-dashboard.yaml
```yaml
image:
  repository: k8s.gcr.io/kubernetes-dashboard-amd64
  tag: v1.10.1
ingress:
  enabled: true
  hosts:
  - dashboard.ninejy.io
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
  tls:
  - secretName: ninejy-io-tls-secret
    hosts:
    - dashboard.ninejy.io
rbac:
  clusterAdminRole: true
```

```bash
helm install stable/kubernetes-dashboard \
-n kubernetes-dashboard \
--namespace kube-system \
-f kubernetes-dashboard.yaml
```

```bash
kubectl eidt svc my-release-kubernetes-dashboard
# type ClusterIP 改为 NodePort, 或者使用 ingress

kubectl -n kube-system get secret | grep kubernetes-dashboard-token

kubectl -n kube-system describe secret ${secretName}
```
