# Jenkins

## Deploy jenkins in k8s

### 1.1 构建镜像

```bash
docker build -t harbor.ninejy.com/infra/jenkins:2.289.2 .

docker push harbor.ninejy.com/infra/jenkins:2.289.2
```

### 1.2 创建命名空间和 harbor secret

```bash
kubectl create namespace infra

kubectl create secret docker-registry harbor --docker-server=harbor.ninejy.com --docker-username=admin --docker-password=Harbor12345 -n infra
```

### 1.3 准备 jenkins 资源清单

[jenkins.yaml](./jenkins.yaml)

### 1.4 执行命令创建 jenkins

```bash
kubectl apply -f jenkins.yaml
```

### 1.5 配置 nginx 反向代理

#### 执行下面命令获取 jenkins service NodePort

```bash
kubectl get svc jenkins -n infra
```

[jenkins.ninejy.com.conf](./jenkins.ninejy.com.conf)
