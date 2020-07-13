#### 节点亲和性
---
###### pod.spec.nodeAffinity
- preferredDuringSchedulingIgnoredDuringExecution 软策略
- requiredDuringSchedulingIgnoredDuringExecution 硬策略

###### requiredDuringSchedulingIgnoredDuringExecution
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: affinity
  labels:
    app: node-affinity-pod
spec:
  containers:
  - name: with-node-affinity
    image: harbor.ninejy.io/library/myapp:v1
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/hostname
            operator: NotIn
            values:
            - k8s-node02
```
###### preferredDuringSchedulingIgnoredDuringExecution
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: affinity
  labels:
    app: node-affinity-pod
spec:
  containers:
  - name: with-node-affinity
    image: harbor.ninejy.io/library/myapp:v1
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: kubernetes.io/hostname
            operator: In
            values:
            - k8s-node02
```
###### 合体
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: affinity
  labels:
    app: node-affinity-pod
spec:
  containers:
  - name: with-node-affinity
    image: harbor.ninejy.io/library/myapp:v1
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/hostname
            operator: NotIn
            values:
            - k8s-node02
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: kubernetes.io/hostname
            operator: In
            values:
            - k8s-node03
```

###### 键值运算关系
- In: lable 的值在某个列表中
- NotIn: label 的值不在某个列表中
- Gt: label 的值大于某个值
- Lt: label 的值小于某个值
- Exists: 某个 label 存在
- DoesNotExist: 某个 label 不存在

<!-- 如果 `nodeSelectorTerms` 下面有多个选项的话, 满足任何一个条件就可以了; 如果 `matchExpressions` y有多个选项的话, 则必须同时满足这些条件才能正常调度 Pod -->

#### Pod 亲和性
---
###### pod.spec.affinity.podAffinity/podAntiAffinity
- preferredDuringSchedulingIgnoredDuringExecution: 软策略
- requiredDuringSchedulingIgnoredDuringExecution: 硬策略

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-3
  labels:
    app: pod-3
spec:
  containers:
  - name: pod-3
    image: harbor.ninejy.io/library/myapp:v1
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - pod-1
        topologyKey: kubernetes.io/hostname
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - pod-2
          topologyKey: kubernetes.io/hostname
```

###### 亲和性/反亲和性调度策略比较如下:
---
调度策略|匹配标签|操作符|拓扑域支持|调度目标
---|---|---|---|---
nodeAffinity|主机|In, NotIn, Exists, DoesNotExist, Gt, Lt|否|指定主机
podAffinity|Pod|In, NotIn, Exists, DoesNotExist|是|Pod 与指定 Pod 同一拓扑域
podAntiAffinity|Pod|In, NotIn, Exists, DoesNotExist|是|Pod 与指定 Pod 不在同一拓扑域
