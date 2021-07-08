# 一、准备

## 准备五台虚拟机 (2C/4G/50G)

主机名 | IP | OS | 用途
-- | -- | --
k8s-201.ninejy.io | 192.168.0.201 | Centos7.5 | bind9,ops
k8s-202.ninejy.io | 192.168.0.202 | Centos7.5 | harbor,nginx
k8s-203.ninejy.io | 192.168.0.203 | Centos7.5 | etcd,kube-master
k8s-204.ninejy.io | 192.168.0.204 | Centos7.5 | etcd,kube-master
k8s-205.ninejy.io | 192.168.0.205 | Centos7.5 | etcd,kube-node

### 1.1 设置主机名

```bash
hostnamectl set-hostname k8s-201.ninejy.io
hostnamectl set-hostname k8s-202.ninejy.io
hostnamectl set-hostname k8s-203.ninejy.io
hostnamectl set-hostname k8s-204.ninejy.io
hostnamectl set-hostname k8s-205.ninejy.io
```

### 1.2 设置网络

```bash
# vim /etc/sysconfig/network-scripts/ifcfg-enp0s3
TYPE=Ethernet
BOOTPROTO=static
NAME=enp0s3
DEVICE=enp0s3
ONBOOT=yes
IPADDR=192.168.0.201
NETMASK=255.255.255.0
GATEWAY=192.168.0.1
DNS1=114.114.114.114

# 重启网络服务
systemctl restart network

# 其他几台同样的设置只需改下IP
```

### 1.3 安装 epel-release 和替换基础源

```bash
# yum install -y epel-release
curl -o /etc/yum.repos.d/epel.repo https://mirrors.aliyun.com/repo/epel-7.repo
curl -o /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-7.repo
```

### 1.4 关闭 selinux 和 firewalld

```bash
# /etc/selinux/config
# SELINUX=disabled
setenforce 0
getenforce

systemctl stop firewalld
```

### 1.5 安装一些常用工具

```bash
yum install wget net-tools telnet tree nmap sysstat lrzsz dos2unix bind-utils -y
```

### 1.6 下载生成证书的工具

```bash
wget https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 -O /usr/local/bin/cfssl
wget https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64 -O /usr/local/bin/cfssljson
wget https://pkg.cfssl.org/R1.2/cfssl-certinfo_linux-amd64 -O /usr/local/bin/cfssl-certinfo
chmod +x /usr/local/bin/cfssl*
```

### 1.7 准备 CA 配置文件和签名请求

```bash
mkdir -p /root/certs /etc/kubernetes
cd /root/certs
# vim /root/certs/ca-config.json
{
    "signing": {
        "default": {
            "expiry": "876000h"
        },
        "profiles": {
            "kubernetes": {
                "usages": [
                    "signing",
                    "key encipherment",
                    "server auth",
                    "client auth"
                ],
                "expiry": "876000h"
            }
        },
        "profiles": {
            "kcfg": {
                "usages": [
                    "signing",
                    "key encipherment",
                    "client auth"
                ],
                "expiry": "876000h"
            }
        }
    }
}

# vim /root/certs/ca-csr.json
{
    "CN": "kubernetes",
    "key": {
        "algo": "rsa",
        "size": 2048
    },
    "names": [
        {
            "C": "CN",
            "ST": "Shanghai",
            "L": "XS",
            "O": "k8s",
            "OU": "System"
        }
    ],
    "ca": {
        "expiry": "876000h"
    }
}
```

### 1.8 生成 CA 证书和私钥

```bash
cfssl gencert -initca ca-csr.json | cfssljson -bare ca
```

### 1.9 创建配置文件: /root/.kube/config

```bash
# 准备 kubectl 使用的 admin 证书签名请求
# vim /root/certs/admin-csr.json
{
    "CN": "admin",
    "hosts": [],
    "key": {
        "algo": "rsa",
        "size": 2048
    },
    "names": [
        {
            "C": "CN",
            "ST": "Shanghai",
            "L": "XS",
            "O": "system:masters",
            "OU": "System"
        }
    ]
}

# 创建 admin 证书与私钥
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes admin-csr.json | cfssljson -bare admin

# 创建 kubectl 访问 kube-apiserver 的凭据
# 设置集群参数
kubectl config set-cluster kubernetes \
    --certificate-authority=/etc/kubernetes/ssl/ca.pem \
    --embed-certs=true \
    --server=https://192.168.0.200:8443 \
    --kubeconfig=/etc/kubernetes/kubectl.kubeconfig
# 设置客户端认证参数
kubectl config set-credentials admin \
    --client-certificate=/etc/kubernetes/ssl/admin.pem \
    --embed-certs=true \
    --client-key=/etc/kubernetes/ssl/admin-key.pem \
    --kubeconfig=/etc/kubernetes/kubectl.kubeconfig
# 设置上下文参数
kubectl config set-context default \
    --cluster=kubernetes --user=admin \
    --kubeconfig=/etc/kubernetes/kubectl.kubeconfig
# 选择默认上下文
kubectl config use-context default \
    --kubeconfig=/etc/kubernetes/kubectl.kubeconfig

# 安装 kubeconfig
mkdir ~/.kube
cp /etc/kubernetes/kubectl.kubeconfig ~/.kube/config
```

### 1.10 创建配置文件: kube-controller-manager.kubeconfig

```bash
# 准备 kube-controller-manager 证书签名请求
# vim /root/certs/kube-controller-manager-csr.json
{
    "CN": "system:kube-controller-manager",
    "hosts": [],
    "key": {
        "algo": "rsa",
        "size": 2048
    },
    "names": [
        {
            "C": "CN",
            "ST": "Shanghai",
            "L": "XS",
            "O": "system:kube-controller-manager",
            "OU": "System"
        }
    ]
}

# 创建 kube-controller-manager 证书与私钥
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes kube-controller-manager-csr.json | cfssljson -bare kube-controller-manager

# 创建 kube-controller-manager 访问 kube-apiserver 的凭据
# # 设置集群参数
kubectl config set-cluster kubernetes \
    --certificate-authority=/etc/kubernetes/ssl/ca.pem \
    --embed-certs=true \
    --server=https://192.168.0.200:8443 \
    --kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig
# 设置认证参数
kubectl config set-credentials system:kube-controller-manager \
    --client-certificate=/etc/kubernetes/ssl/kube-controller-manager.pem \
    --client-key=/etc/kubernetes/ssl/kube-controller-manager-key.pem \
    --embed-certs=true \
    --kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig
# 设置上下文参数
kubectl config set-context default \
    --cluster=kubernetes \
    --user=system:kube-controller-manager \
    --kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig
# 选择默认上下文
kubectl config use-context default \
    --kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig
```

### 1.11 创建配置文件: kube-scheduler.kubeconfig

```bash
# 准备 kube-scheduler 证书签名请求
# vim /root/certs/kube-scheduler-csr.json
{
    "CN": "system:kube-scheduler",
    "hosts": [],
    "key": {
        "algo": "rsa",
        "size": 2048
    },
    "names": [
        {
            "C": "CN",
            "ST": "Shanghai",
            "L": "XS",
            "O": "system:kube-scheduler",
            "OU": "System"
        }
    ]
}

# 创建 kube-scheduler 证书与私钥
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes kube-scheduler-csr.json | cfssljson -bare kube-scheduler

# 创建 kube-scheduler 访问 kube-apiserver 的凭据
# 设置集群参数
kubectl config set-cluster kubernetes \
    --certificate-authority=/etc/kubernetes/ssl/ca.pem \
    --embed-certs=true \
    --server=https://192.168.0.200:8443 \
    --kubeconfig=/etc/kubernetes/kube-scheduler.kubeconfig
# 设置认证参数
kubectl config set-credentials system:kube-scheduler \
    --client-certificate=/etc/kubernetes/ssl/kube-scheduler.pem \
    --client-key=/etc/kubernetes/ssl/kube-scheduler-key.pem \
    --embed-certs=true \
    --kubeconfig=/etc/kubernetes/kube-scheduler.kubeconfig
# 设置上下文参数
kubectl config set-context default \
    --cluster=kubernetes \
    --user=system:kube-scheduler \
    --kubeconfig=/etc/kubernetes/kube-scheduler.kubeconfig
# 选择默认上下文
kubectl config use-context default \
    --kubeconfig=/etc/kubernetes/kube-scheduler.kubeconfig
```

### 1.12 创建配置文件: kube-proxy.kubeconfig

```bash
# 准备 kube-proxy 证书签名请求
# vim /root/certs/kube-proxy-csr.json
{
    "CN": "system:kube-proxy",
    "hosts": [],
    "key": {
        "algo": "rsa",
        "size": 2048
    },
    "names": [
        {
        "C": "CN",
        "ST": "Shanghai",
        "L": "XS",
        "O": "k8s",
        "OU": "System"
        }
    ]
}

# 创建 kube-proxy 证书与私钥
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes kube-proxy-csr.json | cfssljson -bare kube-proxy

# 创建 kube-proxy 访问 kube-apiserver 的凭据
# 设置集群参数
kubectl config set-cluster kubernetes \
    --certificate-authority=/etc/kubernetes/ssl/ca.pem \
    --embed-certs=true \
    --server=https://192.168.0.200:8443 \
    --kubeconfig=/etc/kubernetes/kube-proxy.kubeconfig
# 设置客户端认证参数
kubectl config set-credentials kube-proxy \
    --client-certificate=/etc/kubernetes/ssl/kube-proxy.pem \
    --client-key=/etc/kubernetes/ssl/kube-proxy-key.pem \
    --embed-certs=true \
    --kubeconfig=/etc/kubernetes/kube-proxy.kubeconfig
# 设置上下文参数
kubectl config set-context default \
    --cluster=kubernetes \
    --user=kube-proxy \
    --kubeconfig=/etc/kubernetes/kube-proxy.kubeconfig
# 择默认上下文
kubectl config use-context default \
    --kubeconfig=/etc/kubernetes/kube-proxy.kubeconfig
```
