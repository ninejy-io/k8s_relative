#### 修改 kubernetes 证书的有效期
---
##### 1.配置go语言环境
```bash
kubectl version  # 查看 k8s 版本及 go 语言版本
mkdir /data
cd /data
wget https://studygolang.com/dl/golang/go1.13.14.linux-amd64.tar.gz
tar zxf go1.13.14.linux-amd64.tar.gz -C /usr/local/

# 设置环境变量
vim /etc/profile
  export PATH=$PATH:/usr/local/go/bin
source /etc/profile
go version
```

##### 2.下载源码
```bash
cd /data && git clone https://github.com/kubernetes/kubernetes.git
cd kubernetes
git checkout -b remotes/origin/release-1.15.1 v1.15.1
```

##### 3.修改 kubeadm 源码包更新证书策略
```bash
vim staging/src/k8s.io/client-go/util/cert/cert.go  # kubeadm 1.14 版本之前
vim cmd/kubeadm/app/util/pkiutil/pki_helpers.go  # kubeadm 1.14 至今
  const duration10y = time.Hour * 24 * 365 * 10
  NotAfter: time.Now(duration10y).Add().UTC(),

make WHAT=cmd/kubeadm GOFLAGS=-v
```

##### 4.更新各节点证书
```bash
mv /usr/bin/kubeadm /usr/bin/kubeadm.old
cp /data/kubernetes/_output/bin/kubeadm /usr/bin/kubeadm
cp -r /etc/kubernetes/pki /etc/kubernetes/pki.old

kubeadm alpha certs renew all --config=/root/install-k8s/core/kubeadm-config.yaml

# 到 /etc/kubenetes/pki 目录下查验
cd /etc/kubenetes/pki
openssl x509 -in apiserver.crt -text -noout
# 或
openssl x509 -in /etc/kubernetes/ssl/kubelet.pem -noout -dates
```
