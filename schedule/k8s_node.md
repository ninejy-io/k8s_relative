#### 指定调度节点
---
###### 1. pod.spec.nodeName 将 Pod 直接调度到指定的 Node 节点上, 会跳过 Scheduler 的调度策略, 该匹配规则是强制匹配
```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: myweb
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: myweb
    spec:
      nodeName: k8s-node01
      containers:
      - name: myweb
        image: harbor.ninejy.io/library/myapp:v1
        ports:
        - containerPort: 80
```

###### 2. pod.spec.nodeSelector 通过 kubernetes 的 label-selector 机制选择节点, 由调度器调度策略匹配 label, 而后调度 Pod 到 目标节点, 该匹配规则属于强制约束
```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: myweb2
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: myweb2
    spec:
      nodeSelector:
        disk: ssd
      containers:
      - name: myweb2
        image: harbor.ninejy.io/library/myapp:v1
        ports:
        - containerPort: 80
```
