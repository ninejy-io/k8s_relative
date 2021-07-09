# 一、准备

## 准备五台虚拟机 (2C/4G/50G)

主机名 | IP | OS | 用途
-- | -- | -- | --
k8s-201.ninejy.io | 192.168.0.201 | Centos7.5 | bind9,ops
k8s-202.ninejy.io | 192.168.0.202 | Centos7.5 | harbor,nginx
k8s-203.ninejy.io | 192.168.0.203 | Centos7.5 | etcd,kube-master
k8s-204.ninejy.io | 192.168.0.204 | Centos7.5 | etcd,kube-master
k8s-205.ninejy.io | 192.168.0.205 | Centos7.5 | etcd,kube-node
|| VIP: 192.168.0.200 ||

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

### 1.3 配置 192.168.0.201 到其他节点免密登录

```bash
ssh-keygen

ssh-copy-id 192.168.0.202
ssh-copy-id 192.168.0.203
ssh-copy-id 192.168.0.204
ssh-copy-id 192.168.0.205
```

### 1.4 安装 epel-release 和替换基础源

```bash
# yum install -y epel-release
curl -o /etc/yum.repos.d/epel.repo https://mirrors.aliyun.com/repo/epel-7.repo
curl -o /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-7.repo
```

### 1.5 关闭 selinux 和 swap

```bash
# /etc/selinux/config
# SELINUX=disabled
setenforce 0
getenforce

swapoff -a && sysctl -w vm.swappiness=0

# 文件 /etc/fstab 中 swap 相关的注释掉
```

### 1.6 安装一些常用工具 / 卸载一些不必要的包

```bash
yum remove -y firewalld python-firewall firewalld-filesystem

yum install wget net-tools telnet tree nmap sysstat lrzsz dos2unix bind-utils -y

yum install -y bash-completion conntrack-tools ipset ipvsadm libseccomp nfs-utils psmisc rsync socat
```

### 1.7 优化日志相关的设置, 避免日志重复搜集, 浪费系统资源

```bash
# 禁止 rsyslog 获取 journald 日志1
# 注释掉 '$ModLoad imjournal' 这一行
# grep 'ModLoad imjournal' /etc/rsyslog.conf
# #$ModLoad imjournal # provides access to the systemd journal

# 禁止 rsyslog 获取 journald 日志2
# 注释掉 '$IMJournalStateFile' 这一行
# grep 'IMJournalStateFile' /etc/rsyslog.conf
# #$IMJournalStateFile imjournal.state

# 重启 rsyslog 服务
systemctl restart rsyslog
```

### 1.8 加载内核模块

```bash
# 加载内核模块
modprobe br_netfilter
modprobe ip_vs
modprobe ip_vs_rr
modprobe ip_vs_wrr
modprobe ip_vs_sh
modprobe nf_conntrack # 内核版本 >= 4.19
modprobe nf_conntrack_ipv4 # 内核版本 < 4.19

# 启用 systemd 自动加载模块服务
systemctl enable systemd-modules-load

# 增加内核模块开机加载配置
# vim /etc/modules-load.d/10-k8s-modules.conf
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack_ipv4 # 内核版本 < 4.19
nf_conntrack # 内核版本 >= 4.19
```

### 1.9 设置系统参数

```bash
# 消除docker info 警告WARNING: bridge-nf-call-ip[6]tables is disabled
# https://success.docker.com/article/ipvs-connection-timeout-issue 缩短keepalive_time超时时间为600s

# vim /etc/sysctl.d/95-k8s-sysctl.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-arptables = 1
net.ipv4.tcp_tw_recycle = 0 # 内核版本 < 4.12
net.ipv4.tcp_tw_reuse = 0
net.core.somaxconn = 32768
net.netfilter.nf_conntrack_max=1000000
vm.swappiness = 0
vm.max_map_count=655360
fs.file-max=6553600
net.ipv4.tcp_keepalive_time = 600  # PROXY_MODE = "ipvs"
net.ipv4.tcp_keepalive_intvl = 30  # PROXY_MODE = "ipvs"
net.ipv4.tcp_keepalive_probes = 10 # PROXY_MODE = "ipvs"

# 生效系统参数
sysctl -p /etc/sysctl.d/95-k8s-sysctl.conf
```

### 1.10 设置系统 ulimits

```bash
# 创建 systemd 配置目录
mkdir -p /etc/systemd/system.conf.d

# vim /etc/systemd/system.conf.d/30-k8s-ulimits.conf
[Manager]
DefaultLimitCORE=infinity
DefaultLimitNOFILE=100000
DefaultLimitNPROC=100000
```

### 1.11 把 SCTP 列入内核模块黑名单

```bash
# vim /etc/modprobe.d/sctp.conf
# put sctp into blacklist
install sctp /bin/true
```

### 1.12 下载需要的二进制文件

```bash
# 下载生成证书的工具
wget https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 -O /usr/local/bin/cfssl
wget https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64 -O /usr/local/bin/cfssljson
wget https://pkg.cfssl.org/R1.2/cfssl-certinfo_linux-amd64 -O /usr/local/bin/cfssl-certinfo
chmod +x /usr/local/bin/cfssl*

# 下载 k8s 组件
wget https://dl.k8s.io/v1.21.0/kubernetes-server-linux-amd64.tar.gz

tar zxf kubernetes-server-linux-amd64.tar.gz
scp kubernetes/server/bin/{kubectl,kube-apiserver,kube-controller-manager,kube-scheduler} 192.168.0.203:/usr/local/bin/
scp kubernetes/server/bin/{kubectl,kube-apiserver,kube-controller-manager,kube-scheduler} 192.168.0.204:/usr/local/bin/

scp kubernetes/server/bin/{kubelet,kube-proxy} 192.168.0.203:/usr/local/bin/
scp kubernetes/server/bin/{kubelet,kube-proxy} 192.168.0.204:/usr/local/bin/
scp kubernetes/server/bin/{kubelet,kube-proxy} 192.168.0.205:/usr/local/bin/

# 下载 etcd
wget https://github.com/etcd-io/etcd/releases/download/v3.4.16/etcd-v3.4.16-linux-amd64.tar.gz

tar zxf etcd-v3.4.16-linux-amd64.tar.gz

scp etcd-v3.4.16-linux-amd64/{etcd,etcdctl} 192.168.0.203:/usr/local/bin/
scp etcd-v3.4.16-linux-amd64/{etcd,etcdctl} 192.168.0.204:/usr/local/bin/
scp etcd-v3.4.16-linux-amd64/{etcd,etcdctl} 192.168.0.205:/usr/local/bin/

# 下载 cni 插件
wget https://github.com/containernetworking/plugins/releases/download/v0.9.1/cni-plugins-linux-amd64-v0.9.1.tgz

tar zxf cni-plugins-linux-amd64-v0.9.1.tgz

scp cni-plugins-linux-amd64-v0.9.1/{bridge,host-local,loopback,portmap,flannel} 192.168.0.203:/usr/local/bin/
scp cni-plugins-linux-amd64-v0.9.1/{bridge,host-local,loopback,portmap,flannel} 192.168.0.204:/usr/local/bin/
scp cni-plugins-linux-amd64-v0.9.1/{bridge,host-local,loopback,portmap,flannel} 192.168.0.205:/usr/local/bin/
```

### 1.13 准备 CA 配置文件和签名请求

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

### 1.14 生成 CA 证书和私钥

```bash
cfssl gencert -initca ca-csr.json | cfssljson -bare ca
```

### 1.15 创建配置文件: /root/.kube/config

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

### 1.16 创建配置文件: kube-controller-manager.kubeconfig

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

### 1.17 创建配置文件: kube-scheduler.kubeconfig

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

### 1.18 创建配置文件: kube-proxy.kubeconfig

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
