#### ConfigMap
---
###### ConfigMap 功能在 Kubernetes 1.2 版本中引入, 许多应用程序会从配置文件、命令行参数或者环境变量中读取配置信息. ConfigMap API 给我们提供了想容器注入配置信息的机制, ConfigMap 可以被用来保存单个属性, 也可以用来保存整个配置文件或者 JSON 二进制大对象

#### ConfigMap 的创建
---
- 1.使用目录创建
```bash
# conf/game.properties
enemies=aliens
lives=3
enemies.cheat=true
enemies.cheat.level=noGoodRotten
secret.code.passphrase=UUDDLRLRBABAS
secret.code.allowed=true
secret.code.lives=30

# conf/ui.properties
color.good=purple
color.bad=yellow
allow.textmode=true
how.nice.to.look=fairlyNice

kubectl create configmap game-config --from-file=conf
kubectl get cm game-config -o yaml
kubectl describe cm game-config
```
###### `--from-file`指定在目录下的所有文件都会被用在 ConfigMap 里面创建一个键值对, 键的名字就是文件名, 值就是文件内容

- 2.使用文件创建
###### 只要指定一个文件就可以从单个文件中创建 ConfigMap. `--from-file`可以使多次
```bash
kubectl create configmap game-config-2 --from-file=conf/game.properties
kubectl get configmap game-config-2 -o yaml
```

- 3.使用字面值创建
###### 使用字面值创建, 利用`--from-literal`参数传递配置信息, 该参数可以使用多次, 格式如下:
```bash
kubectl create configmap special-config --from-literal=special.how=very --from-literal=special.type=charm

kubectl get configmap special-config -o yaml
```

#### Pod 中使用 ConfigMap
---
- a.使用 ConfigMap 来替代环境变量
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: special-config
  namespace: default
data:
  special.how: very
  special.type: charm
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: env-config
  namespace: default
data:
  log_level: INFO
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dapi-test-pod
spec:
  containers:
  - name: test-container
    image: harbor.ninejy.io/library/myapp:v1
    command: ["/bin/sh", "-c", "env"]
    env:
    - name: SPECIAL_LEVEL_KEY
      valueFrom:
        configMapKeyRef:
          name: special-config
          key: special.how
    - name: SPECIAL_TYPE_KEY
      valueFrom:
        configMapKeyRef:
          name: special-config
          key: special.type
    envFrom:
    - configMapRef:
        name: env-config
  restartPolicy: Never
```
```bash
kubectl logs dapi-test-pod
```

- b.通过数据卷插件使用 ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: special-config
  namespace: default
data:
  special.how: very
  special.type: charm
```
###### 在数据卷中使用这个 ConfigMap, 有不同的选项. 最基本的就是将文件填入数据卷, 在这个文件中, 键就是文件名, 键值就是文件内容
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dapi-test-pod11
spec:
  containers:
  - name: test-container
    image: harbor.ninejy.io/library/myapp:v1
    command: ["/bin/sh", "-c", "cat /etc/config/special.how"]
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
    - name: config-volume
      configMap:
        name: special-config
  restartPolicy: Never
```
