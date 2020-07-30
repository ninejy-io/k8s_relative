#### securityContext

###### 容器是否以特权模式运行

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp1
spec:
  volumes:
  - name: test
    emptyDir: {}
  containers:
  - name: test1
    image: busybox:1.28
    command:
    - /bin/sh
    - -c
    - sleep 3600
    volumeMounts:
    - name: test
      mountPath: /data/test
    securityContext:
      privileged: false  # true 特权模式, false 非特权模式
```

###### 限制容器内启动进程的用户(跟镜像里定义的 USER 也有关系). spec 下的会覆盖 containers 下的定义

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp3
spec:
  securityContext:
    runAsUser: 1001
  volumes:
  - name: test
    emptyDir: {}
  containers:
  - name: test1
    image: busybox:1.28
    command:
    - /bin/sh
    - -c
    - sleep 3600
    volumeMounts:
    - name: test
      mountPath: /data/test
    securityContext:
      privileged: false
      runAsUser: 1000
```

###### 限定 Pod 内文件所属组

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp4
spec:
  securityContext:
    fsGroup: 2000
  volumes:
  - name: test
    emptyDir: {}
  containers:
  - name: test1
    image: busybox:1.28
    command:
    - /bin/sh
    - -c
    - sleep 3600
    volumeMounts:
    - name: test
      mountPath: /data/test
    securityContext:
      privileged: false
```
