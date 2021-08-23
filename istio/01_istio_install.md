# Istio

## Istio 基础

### 1.1 安装

```bash
# 安装 istio 客户端
wget https://github.com/istio/istio/releases/download/1.11.0/istio-1.11.0-linux-amd64.tar.gz
tar xf istio-1.11.0-linux-amd64.tar.gz
cp istio-1.11.0/bin/istioctl /usr/local/bin/
cp istio-1.11.0/tools/istioctl.bash ~/.istioctl.bash
source ~/.istioctl.bash

# 查看版本
istioctl version --remote=false
# 1.11.0

# 列出 istio 支持的 profile
istioctl profile list

istioctl profile dump demo > demo.yaml

# 安装 istio 服务端
istioctl install --set profile=demo

# 查看安装了哪些东西
kubectl -n istio-system get all

# 修改入口网关的服务类型
kubectl patch svc -n istio-system istio-ingressgateway -p '{"spec":{"type":"NodePort"}}'
```

### 1.2 卸载

```bash
istioctl manifest generate --set profile=demo | kubectl delete -f -

kubectl delete namespace istio-system
```

### 1.3 istioctl analyze

```bash
# Analyze istio configuration and print validation messages
istioctl analyze --help
istioctl analyze

istioctl analyze -n ninejy
```

### 1.4 istio 注入演示

```yaml
# ninejy-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ninejy
  labels:
    app: ninejy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ninejy
  template:
    metadata:
      labels:
        app: ninejy
    spec:
      containers:
      - name: nginx
        image: nginx:1.18-alpine
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
```

```bash
kubectl create ns ninejy

kubectl apply -f ninejy-deployment.yaml -n ninejy
kubectl get pods -n ninejy

# Deployment 注入 istio (会多出来两个容器)
istioctl kube-inject -f ninejy-deployment.yaml | kubectl apply -f - -n ninejy
istioctl kube-inject -f ninejy-deployment.yaml > ninejy-deployment-inject.yaml

kubectl -n ninejy exec -it ninejy-79cff7896d-q98mm -c nginx -- ifconfig
kubectl -n ninejy exec -it ninejy-79cff7896d-q98mm -c istio-proxy -- ifconfig
kubectl -n ninejy exec -it ninejy-79cff7896d-q98mm -c nginx -- netstat -nltp

kubectl -n ninejy logs ninejy-79cff7896d-q98mm -c istio-init

kubectl -n ninejy exec -it ninejy-79cff7896d-q98mm -c istio-proxy -- ps -ef

# Deployment 未注入 istio
kubectl apply -f ninejy-deployment.yaml
kubectl get pods
kubectl exec -it ninejy-79cff7896d-gkdzd -- netstat -nltp

kubectl get ns ninejy --show-labels

# Service 注入 istio (不会有变化)
kubectl expose deployment -n ninejy ninejy

# Enabled for Istio injection
kubectl label namespace ninejy istio-injection=enabled

# Disabled for Istio injection
kubectl label namespace ninejy istio-injection=disabled
```
