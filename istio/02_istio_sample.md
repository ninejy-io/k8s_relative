# Istio

## istio sample

### 2.1 示例

- 创建 client deployment

```yaml
# ninejy-client.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: client
  labels:
    app: client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: client
  template:
    metadata:
      labels:
        app: client
    spec:
      containers:
      - name: busybox
        image: busybox
        imagePullPolicy: IfNotPresent
        command: [ "/bin/sh", "-c", "sleep 3600" ]
```

- 创建 httpd 和 tomcat deployment

```yaml
# ninejy-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: httpd
  labels:
    server: httpd
    app: web
spec:
  replicas: 1
  selector:
    matchLabels:
      server: httpd
      app: web
  template:
    metadata:
      name: httpd
      labels:
        server: httpd
        app: web
    spec:
      containers:
      - name: busybox
        image: busybox
        imagePullPolicy: IfNotPresent
        command: [ "/bin/sh", "-c", "echo 'hello httpd' > /var/www/index.html; httpd -f -p 8080 -h /var/www" ]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tomcat
  labels:
    server: tomcat
    app: web
spec:
  replicas: 1
  selector:
    matchLabels:
      server: tomcat
      app: web
  template:
    metadata:
      name: tomcat
      labels:
        server: tomcat
        app: web
    spec:
      containers:
      - name: tomcat
        image: docker.io/kubeguide/tomcat-app:v1
        imagePullPolicy: IfNotPresent
```

- 创建 service

```yaml
# ninejy-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: httpd-svc
spec:
  selector:
    server: httpd
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: tomcat-svc
spec:
  selector:
    server: tomcat
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
```

#### 进入 client pod 测试访问 httpd 和 tomcat svc

```bash
kubectl get pods
kubectl exec -it client-bcd749854-mchk4 -- sh
wget -q -O - http://httpd-svc:8080
wget -q -O - http://tomcat-svc:8080
wget -q -O - http://web-svc:8080
```

- 创建 virtualservice

```yaml
# ninejy-vs.yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: web-svc-vs
spec:
  hosts:
  - web-svc
  http:
  - route:
    - destination:
        host: httpd-svc
      weight: 80
    - destination:
        host: tomcat-svc
      weight: 20
```

#### 查看 virtualservice

```bash
kubectl get virtualservices
```

#### 注入 istio

```bash
istioctl kube-inject -f ninejy-client.yaml | kubectl apply -f -
istioctl kube-inject -f ninejy-deployment.yaml | kubectl apply -f -

kubectl get pods
```

#### 进入到 client pod 测试访问 web-svc

```bash
kubectl get pods
kubectl exec -it client-5dd7cdcc9b-44k4l -c busybox -- sh
wget -q -O - http://web-svc:8080

# 多次访问可以看到请求到 httpd 和 tomcat 的比例为 4:1
```

- 测试带有条件的 virtualservice

```yaml
# ninejy-vs-with-condition.yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: web-svc-vs
spec:
  hosts:
  - web-svc
  http:
  - match:
    - headers:
        end-user:
          exact: ninejy
    route:
    - destination:
        host: tomcat-svc
  - route:
    - destination:
        host: httpd-svc
```

```bash
kubectl delete -f ninejy-vs.yaml
kubectl apply -f ninejy-vs-with-condition.yaml

# 进到 client pod 中测试访问
kubectl get pods
kubectl exec -it client-5dd7cdcc9b-44k4l -- sh
wget -q -O - http://web-svc:8080 # 只会转发到 httpd-svc
wget -q -O - http://web-svc:8080 --header 'end-user: ninejy' # 只会转发到 tomcat-svc
```
