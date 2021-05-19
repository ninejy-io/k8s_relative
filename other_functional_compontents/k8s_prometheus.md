#### 组件说明

---

- 1. MetricServer: 是 kubernetes 集群资源使用情况的聚合器, 收集数据给 kubernetes 集群内部使用, 如: kubelet, scheduler等
- 2. PrometheusOperator: 是一个系统监测和警报工具箱, 用来存储监控数据
- 3. NodeExporter: 用于各 node 的股眼见度量指标状态数据
- 4. KubeStateMetrics: 收集 kubernetes 集群内部资源对象数据, 制定告警规则
- 5. Prometheus: 采用 pull 方式收集 apiserver、scheduler、controller-manager、kubelet 组件数据, 通过 http 协议传输
- 6. Grafana: 是可视化数据统计和监控平台

#### 构建步骤

---

```bash
git clone https://github.com/coreos/kube-prometheus.git
cd kube-prometheus/manifests
```

###### 修改 grafana-service.yaml 文件, 使用 NodePort 方式访问 grafana

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    app: grafana
  name: grafana
  namespace: monitoring
spec:
  type: NodePort  # add this line
  ports:
  - name: http
    port: 3000
    targetPort: http
    nodePort: 30100  # add this line
  selector:
    app: grafana
```

###### 修改 prometheus-service.yaml, 该为 NodePort 方式

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    prometheus: k8s
  name: prometheus-k8s
  namespace: monitoring
spec:
  type: NodePort  # add this line
  ports:
  - name: web
    port: 9090
    targetPort: web
    nodePort: 30200  # add this line
  selector:
    app: prometheus
    prometheus: k8s
  sessionAffinity: ClientIP
```

###### 修改 alertmanager-service.yaml, 使用 NodePort 方式

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    alertmanager: main
  name: alertmanager-main
  namespace: monitoring
spec:
  type: NodePort  # add this line
  ports:
  - name: web
    port: 9093
    targetPort: web
    nodePort: 30300  # add this line
  selector:
    alertmanager: main
    app: alertmanager
  sessionAffinity: ClientIP
```

###### 创建 prometheus、node-exporter、alertmanager、grafana 等

```bash
kubectl create -f manifests/setup
until kubectl get servicemonitors --all-namespaces ; do date; sleep 1; echo ""; done
kubectl create -f manifests/
```

#### Horizontal Pod Autoscaling

---

###### Horizontal Pod Autoscaling 可以根据 CPU 利用率自动伸缩一个 Replication Contoller、Deployment 或者 Replica Set 中的 Pod 数量

<!-- 为了演示 Horizontal Pod Autoscaling, 我们将使用一个基于 php-apache 镜像的定制 Docker 镜像. 在[这里](https://k8smeetup.github.io/docs/user-guide/horizontal-pod-autoscaling/image/Dockerfile) 你可以查看完整的 Dockerfile 定义. 镜像包括一个 [index.php](https://k8smeetup.github.io/docs/user-guide/horizontal-pod-autoscaling/image/index.php) 页面, 其中包括了一些可以运行 CPU 密集计算任务的代码 -->

###### 自制镜像

```bash
# Dockerfile
FROM php:5-apache
ADD index.php /var/www/html/index.php
RUN chmod a+rx index.php

# index.php
<?php
$x = 0.0001;
for ($i = 0; $i <= 1000000; $i++) {
    $x += sqrt($x);
}
echo "OK!";
?>

docker build -t harbor.ninejy.io/library/hpa-example .
docker push harbor.ninejy.io/library/hpa-example
```

###### 创建 Deployment 和 Service

```bash
kubectl run php-apache --image=harbor.ninejy.io/library/hpa-example --requests=cpu=200m --expose --port=80
```

###### 创建 HPA 控制器 - 相关的算法详情请参阅[这篇文档]()

```bash
kubectl autoscale deployment php-apache --cpu-percent=50 --min=1 --max=10
```

###### 增加负载, 查看负载节点数目

```bash
kubectl run -i --tty load-generator --image=busybox /bin/sh
$ while true; do wget -q -O- http://php-apache.default.svc.cluster.local; done
```

#### 资源限制 - Pod

---

###### Kubernetes 对资源的限制实际上是通过 cgroup 来控制的, cgroup 是容器的一组用来控制内核如何运行进程的相关属性集合. 针对内存、CPU 和各种设备都有对应的 cgroup
###### 默认情况下, Pod 运行没有 CPU 和内存的限额. 这意味着系统中的任何 Pod 将能够像执行该 Pod 所在的节点一样, 消耗足够多的 CPU 和内存. 一般会针对某些应用的 pod 资源进行资源限制, 这个资源限制是通过 resources 的 requests 和 limits 来实现

```yaml
spec:
  containers:
  - image: xxx
    imagePullPolicy: Always
    name: auth
    ports:
    - containerPort: 8080
      protocol: TCP
    resources:
      limits:
        cpu: "4"
        memory: 2Gi
      requests:
        cpu: 250m
        memory: 250Mi
```

###### requests 要分配的资源, limits 为最高请求的资源值. 可以简单理解为初始值和最大值

#### 资源限制 - 命名空间

---

- 1. 计算资源配额

  ```yaml
  apiVersion: v1
  kind: ResourceQuota
  metadata:
    name: compute-resources
    namespace: spark-cluster
  spec:
    hard:
      pods: "20"
      requests.cpu: "20"
      requests.memory: 100Gi
      limits.cpu: "40"
      limits.memory: 200Gi
  ```

- 2. 配置对象数量配额限制

  ```yaml
  apiVersion: v1
  kind: ResourceQuota
  metadata:
    name: object-counts
    namespace: spark-cluster
  spec:
    hard:
      configmaps: "10"
      persistentvolumeclaims: "4"
      replicationcontrollers: "20"
      secrets: "10"
      services: "10"
      services.loadbalancers: "2"
  ```

- 3. 配置 CPU 和内存 LimitRange

  ```yaml
  apiVersion: v1
  kind: LimitRange
  metadata:
    name: cpu-mem-limit-range
  spec:
    limits:
    - default:
        cou: 5
        memory: 50Gi
    - defaultRequest:
        cpu: 1
        memory: 1Gi
      type: Container
  ```

  - `default` 即 limit 的值
  - `defaultRequest` 即 request 的值
