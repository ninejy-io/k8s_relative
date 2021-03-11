#### RC
```yaml
apiVersion: extensions/v1beta1
kind: ReplicaSet
metadata:
  name: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      tier: frontend
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      containers:
      - name: myapp-frontend
        image: harbor.ninejy.io/library/myapp:v1
        env:
        - name: GET_HOSTS_FROM
          value: dns
        ports:
        - containerPort: 80
```
```bash
kubectl get pod --show-labels
kubectl label pod ${pod_name} ${new_label} --overwrite
# kubectl label pod frontend-5tdq7 tier=frontend1 --overwrite
# kubectl get pod --show-labels
kubectl delete rs --all
kubectl get pod --show-labels
```
---
#### Deployment
```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: myapp-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp-container
        image: harbor.ninejy.io/library/myapp:v1
        ports:
        - containerPort: 80
```
```bash
kubectl apply -f deployment.yaml --record
# --record 参数可以记录命令, 我们可以很方便的查看每次 revision 的变化
kubectl get deployment
kubectl get rs
kubectl get pod
```
###### 扩容
```bash
kubectl scale deployment myapp-deployment --replicas=10
```
###### 如果集群支持 horizontal pod autoscaling 的话, 还可以
```bash
kubectl autoscale deployment myapp-deployment --mix=10 --max=15 --cpu-percent=80
```
###### 更新镜像
```bash
kubectl set image deployment/myapp-deployment myapp-container=harbor.ninejy.io/library/myapp:v2
```
###### 回滚
```bash
kubectl rollout undo deployment/myapp-deployment
```
#### Deployment 更新策略
---
###### Deployment 可以保证在升级时只有一定数量的 Pod 是 down 的. 默认的, 它会确保至少有比期望的Pod数量少一个是up状态(最多一个不可用)
###### Deployment 同时也可以确保只创建出只超过期望数量的一定数量的Pod. 默认的, 它会确保最多比期望的Pod数量多一个的Pod是up状态的(最多一个surge)
** 未来的k8s版本中, 将从1-1变成25%-25% **

#### Rollover (多个rollout并行)
---
###### 假如你创建了一个有5个`nginx:1.7.9`replica的 Deployment, 但是当还只有3个`nginx:1.7.9`的replica创建出来的时候你就开始更新含有5个`nginx:1.9.1`replica 的 Deployment. 在这种情况下, Deployment 会立即杀掉已创建的3个`nginx:1.7.9`的 Pod, 并开始创建`nginx:1.9.1`的 Pod. 它不会等到所有的5个`nginx:1.7.9`的 Pod 都创建完成后才开始改变航道

#### 回退 Deployment
---
<!-- 只要 Deployment 的 rollout 被触发就会创建一个 revision. 也就是说当且仅当 Deployment 的 Pod template (如`.spec.template`) 被更改, 例如更新template中的label和容器镜像时, 就会创建出一个新的 revision. 其他的更新, 比如扩容 Deployment 不会创建 revision 因此我们可以很方便的手动或者自动扩容. 这意味着当你回退到历史 revision 时, 只有 Deployment 中的 Pod template 部分才会回退 -->
```bash
kubectl set image deployment/nginx-deployment nginx=nginx:1.9.1
kubectl rollout status deployment/nginx-deployment
kubectl get pod
kubectl rollout history deployment/nginx-deployment
kubectl rollout undo deployment/nginx-deployment
kubectl rollout undo deployment/nginx-deployment --to-revision=2  # 可以使用 --to-revision 参数指定某个历史版本
kubectl rollout pause deployment/nginx-deployment  # 暂停 deployment 的更新
```
###### 可以使用`kubectl rollout status`命令查看 Deployment 是否完成. 如果 rollout 成功完成, `kubectl rollout status`将返回一个0值的 Exit Code.

#### 清理 Policy
---
###### 可以通过设置 `.spec.revisionHistoryLimit`项来指定 deployment 最多保留多少 revision 历史记录. 默认的会保留所有的 revision. 如果将该项设置为0, Deployment 就不允许回退了
