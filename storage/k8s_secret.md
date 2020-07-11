#### Secret 存在意义
---
###### Secret 解决了密码、token、秘钥等敏感数据的配置问题, 而不需要把这些敏感数据暴露到镜像或者 Pod Spec 中. Secret 可以以 Volume 或者环境变量的方式使用
###### Secret 有三种类型
  - ServiceAccount: 用来访问 Kubernetes API, 由 Kubernetes 自动创建, 并且会自动挂载到 Pod 的`/run/secrets/kubernetes.io/serviceaccount`目录中
  - Opaque: base64 编码格式的 Secret, 用来存储密码、秘钥等
  - kubernetes.io/dockerconfigjson: 用来存储私有 docker registry 的认证信息

#### ServiceAccount
---
```bash
kubectl run nginx --image nginx
kubectl get pods
kubectl exec nginx-7bb7cd8db5-zw29p ls /run/secrets/kubernetes.io/serviceaccount
```

#### Opaque Secret
---
  - 1.创建说明
     Opaque 类型的数据是一个 map 类型, 要求 value 是 base64 编码的格式
     ```bash
     echo -n "admin" | base64
     # YWRtaW4=
     echo -n "123456" | base64
     # MTIzNDU2
     ```
     secrets.yaml
     ```yaml
     apiVersion: v1
     kind: Secret
     metadata:
       name: mysecret
     type: Opaque
     data:
       username: YWRtaW4=
       password: MTIzNDU2
     ```
  - 2.使用方式
    - a.将 Secret 挂载到 Volume 中
      ```yaml
      apiVersion: v1
      kind: Pod
      metadata:
        name: secret-test
        labels:
          name: secret-test
      spec:
        volumes:
        - name: secrets
          secret:
            secretName: mysecret
        containers:
        - name: db
          image: harbor.ninejy.io/library/myapp:v1
          volumeMounts:
          - name: secrets
            mountPath: "/etc/secrets"
            readOnly: true
      ```
    - b.将 Secret 导入到环境变量中
      ```yaml
      apiVersion: extensions/v1beta1
      kind: Deployment
      metadata:
        name: pod-deployment
      spec:
        replicas: 2
        template:
          metadata:
            labels:
              app: pod-deployment
          spec:
            containers:
            - name: pod-1
              image: harbor.ninejy.io/library/myapp:v1
              ports:
              - containerPort: 80
              env:
              - name: TEST_USER
                valueFrom:
                  secretKeyRef:
                    name: mysecret
                    key: username
              - name: TEST_PASSWORD
                valueFrom:
                  secretKeyRef:
                    name: mysecret
                    key: password
      ```

#### kubernetes.io/dockerconfigjson
---
###### 使用 kubectl 创建 docker registry 认证的 secret
```bash
kubectl create secret docker-registry myregistrykey --docker-server=DOCKER_REGISTRY_SERVER --docker-username=DOCKER_USER --docker-password=DOCKER_PASSWORD --docker-email=DOCKER_EMAIL
```
###### 在创建 Pod 的时候, 通过`imagePullSecrets`来引用刚创建的`myregistrykey`
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: foo
spec:
  containers:
  - name: foo
    image: harbor.ninejy.io/test/myapp:v3
  imagePullSecrets:
  - name: myregistrykey
```
