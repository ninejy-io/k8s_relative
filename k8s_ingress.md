#### 安装 Ingress (NodePort方式)
---
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/baremetal/deploy.yaml
```

#### Ingress HTTP 代理访问
---
###### deployment / Service / Ingress yaml 文件
```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: nginx-dm
spec:
  replicas: 2
  template:
    metadata:
      labels:
        name: nginx
    spec:
      containers:
      - name: nginx
        image: harbor.ninejy.io/myapp:v1
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
  selector:
    name: nginx
---
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: nginx-test
spec:
  rules:
  - host: www1.ninejy.io
    http:
      paths:
      - path: /
        backend:
          serviceName: nginx-svc
          servicePort: 80
```

#### Ingress HTTPS 代理访问
---
###### 创建证书, 以及 cert 存储方式
```bash
openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -subj "/CN=ngixnsvc/O=nginxsvc"
kubectl create secret tls tls-secret --key tls.key --cert tls.crt
```
###### deployment / Service / Ingress yaml 文件
```yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: nginx-https-test
spec:
  tls:
  - hosts:
    - www2.ninejy.io
    secretName: tls-secret
  rules:
  - host: www2.ninejy.io
    http:
      paths:
      - path: /
        backend:
          serviceName: nginx-svc
          servicePort: 80
```

#### nginx 进行 BasicAuth
---
```bash
yum install -y httpd-tools
htpasswd -c auth foo
kubectl create secret generic basic-auth --from-file=auth
```
```yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: nginx-with-auth
  annotations:
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: basic-auth
    nginx.ingress.kubernetes.io/auth-realm: 'Authentication Required - foo'
spec:
  rules:
  - host: www3.ninejy.io
    http:
      paths:
      - path: /
        backend:
          serviceName: nginx-svc
          servicePort: 80
```

#### nginx 进行重写
---

名称|描述|值
--- | --- | --- | ---
nignx.ingress.kubernetes.io/rewrite-target|必须 重定向流量的目标URL|串
nignx.ingress.kubernetes.io/ssl-redirect|指示位置是否仅可访问ssl(当Ingress包含证书时默认为true)|布尔
nignx.ingress.kubernetes.io/force-ssl-redirect|即使ingress未启用tls, 也强制重定向到HTTPS|布尔
nignx.ingress.kubernetes.io/app-root|定义Controller必须重定向的应用程序根,如果它在'/'上下文中|串
nignx.ingress.kubernetes.io/use-regex|指示 Ingress 上定义的路径是否使用正则表达式|布尔


```yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: nginx-rewrite
  annotations:
    nignx.ingress.kubernetes.io/rewrite-target: http://www1.ninejy.io:30817/
spec:
  rules:
  - host: www4.ninejy.io
    http:
      paths:
      - path: /
        backend:
          serviceName: nginx-svc
          servicePort: 80
```
