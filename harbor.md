### harbor部署

#### 1.安装docker-compose
```shell
curl -L https://github.com/docker/compose/releases/download/1.23.0-rc3/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

#### 2.下载harbor离线安装包
```shell
wget https://storage.googleapis.com/harbor-releases/harbor-offline-installer-v1.6.1.tgz
tar zxf harbor-offline-installer-v1.6.1.tgz
```

#### 3.准备ca证书
###### 可以购买域名，然后申请免费的域名证书 https://freessl.org/
###### 如果不购买证书，也可以自己手动生成证书
```bash
openssl genrsa -des3 -out server.key 2048
# 输入密码 123456
openssl req -new -key server.key -out server.csr
# 密码: 123456 
# Country: CN
# State: SH
# Locality: SH
# Organization Name: ninejy
# Organization Unit Name: ninejy
# Common Name: ninejy.io
# Email Address: admin@ninejy.io
cp server.key server.key.io
openssl rsa -in server.key.io -out server.key
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
```
#### 4.安装harbor
###### 进入harbor目录修改配置文件以下几项
```shell
# cd harbor; vim harbor.cfg
hostname = harbor.dog128.cn
ui_url_protocol = https
ssl_cert = /data/cert/dog128.pem
ssl_cert_key = /data/cert/dog128.key
harbor_admin_password = asdf2018
```
###### 执行install.sh脚本
```shell
./install.sh
```
###### 查看容器 / 停止 / 启动
```shell
docker-compose ps
docker-compose down
docker-compose up -d
```

#### 5.测试访问
###### 浏览器访问 (需绑定hosts 用户名密码:<admin/asdf2018>)
https://harbor.dog128.cn

###### 登录镜像仓库/打标签/推送镜像到仓库/拉取镜像
```shell
docker login harbor.dog128.cn
docker tag harbor.dog128.cn/jy90/busybox
docker push harbor.dog128.cn/jy90/busybox
docker pull harbor.dog128.cn/jy90/busybox
```

#### 6.k8s使用harbor
###### 创建secret
```shell
kubectl create secret docker-registry my-secret --docker-server=harbor.dog128.cn --docker-username=admin --docker-password=asdf2018
```
###### 往harbor私有镜像仓库里推送一个httpd的镜像
```shell
docker pull httpd
docker tag httpd harbor.dog128.cn/jy90/httpd
docker login harbor.dog128.cn
docker push harbor.dog128.cn/jy90/httpd
```
###### 定义一个创建pod的yaml文件
```shell
# vim test-httpd-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-httpd-pod
spec:
  containers:
  - image: harbor.dog128.cn/jy90/httpd:latest
    name: test-httpd-pod
  imagePullSecrets:
  - name: my-secret

 # kubectl create -f test-httpd-pod.yaml
 # kubectl get pod
 # kubectl describe pod test-httpd-pod
```