# StatefulSet

```yaml
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
  namespace: default
  labels:
    app: nginx
spec:
  podManagementPolicy: OrderedReady
  replicas: 3
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      app: nginx
  serviceName: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.18.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
          protocol: TCP
          name: web

---
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
    name: web
  type: ClusterIP
  # clusterIP: None # headless service
```

## headless service 可以访问指定的 pod

```bash
ping web-0.nginx.default.svc.cluster.local
ping web-1.nginx.default.svc.cluster.local
ping web-2.nginx.default.svc.cluster.local

dig web-0.nginx.default.svc.cluster.local
dig nginx.default.svc.cluster.local
```
