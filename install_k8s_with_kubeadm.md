## kubeadm 部署安装k8s集群
---
### 基础设置
#### 设置主机名及Host文件的相互解析
```bash
hostnamectl set-hostname k8s-master01  # 192.168.0.61
hostnamectl set-hostname k8s-node01  # 192.168.0.62
hostnamectl set-hostname k8s-node02  # 192.168.0.63

# vim /etc/hosts
192.168.0.61  k8s-master01
192.168.0.62  k8s-node01
192.168.0.63  k8s-node02
```
#### 安装依赖包
```bash
yum install -y conntrack ntpdate ntp ipvsadm ipset jq iptables curl sysstat libseccomp wget vim net-tools git
```
#### 设置防火墙为iptables并设置空规则
```bash
systemctl stop firewalld && systemctl disable firewalld
yum install -y iptables-services && systemctl start iptables && systemctl enable iptables && iptables -F && service iptables save
```
#### 关闭Selinux
```bash
swapoff -a && sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
setenforce 0 && sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config
```
#### 调整内核参数, 对于k8s
```bash
cat > /etc/sysctl.d/kubernetes.conf << EOF
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
net.ipv4.tcp_tw_recycle = 0
net.ipv6.conf.all.disable_ipv6 = 1
net.netfilter.nf_conntrack_max = 2310720
vm.swappiness = 0  # 禁止使用 swap 空间, 只有当系统 OOM 时才允许使用它
vm.overcommit_memory = 1  # 不检查物理内存是否够用
vm.panic_on_oom = 0  # 开启 OOM
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 1048576
fs.file-max = 52706963
fs.nr_open = 52706963
EOF
modprobe br_netfilter
sysctl -p /etc/sysctl.d/kubernetes.conf
```
#### 调整系统时区
```bash
# 设置系统时区
timedatectl set-timezone Asia/Shanghai
# 将当前的 UTC 时间写入硬件时钟
timedatectl set-local-rtc 0
# 重启依赖系统时间的服务
systemctl restart rsyslog
systemctl restart crond
```
#### 关闭不用的系统服务
```bash
systemctl stop postfix && systemctl disable postfix
```
#### 设置 rsyslogd 和 systemd journald
```bash
mkdir /var/log/journal  # 持久化保存日志的目录
mkdir /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/99-prophet.conf << EOF
[Journal]
# 持久化保存到磁盘
Storage=persistent

# 压缩历史日志
Compress=yes

SyncintervalSec=5m
RateLimitInterval=30s
RateLimitBrust=1000

# 最大占用空间 10G
SystemMaxUse=10G

# 单个日志文件最大 200M
SystemMaxFileSize=200M

# 日志保存时间 2 周
MaxRetentionSec=2week

# 不将日志转发到 syslog
ForwardToSyslog=no
EOF
systemctl restart systemd-journald
```
#### 升级系统内核为 4.4
Centos7.x系统自带的3.10.x内核存在一些bug, 导致运行的docker, kubernetes不稳定, 例如:
rpm -Uvh http://www.elrepo.org/elrepo-release-7.0-3.el7.elrepo.noarch.rpm
```bash
rpm -Uvh http://www.elrepo.org/elrepo-release-7.0-3.el7.elrepo.noarch.rpm
# 安装完成后检查 /boot/grub2/grub.cfg 中对应内核 menuenty 中是否包含 initrd16 配置, 如果没有, 再安装一次
yum --enablerepo=elrepo-kernel install -y kernel-lt
# 设置开机从新内核启动
grub2-set-default "CentOS Linux (4.4.182-1.el7.elrepo.x86_64) 7 (Core)" && reboot
```
---
#### kube-proxy 开启ipvs的前置条件
```bash
# modprobe br_netfilter
cat > /etc/sysconfig/modules/ipvs.modules << EOF
#!/bin/bash
modprobe -- ip_vs
modprobe -- ip_vs_rr
modprobe -- ip_vs_wrr
modprobe -- ip_vs_sh
modprobe -- nf_conntrack_ipv4
EOF
chmod 755 /etc/sysconfig/modules/ipvs.modules
bash /etc/sysconfig/modules/ipvs.modules && lsmod | grep -e ip_vs -e nf_conntrack_ipv4
```
#### 安装 docker 软件
```bash
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
yum update -y && yum install -y docker-ce

# 创建 /etc/docker 目录
mkdir /etc/docker

# 配置 daemon
cat > /etc/docker/daemon.json << EOF
{
    "exec-opts": ["native.cgroupdriver=systemd"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m"
    },
    "insecure-registries": ["https://harbor.ninejy.io"]
}
EOF
mkdir -p /etc/systemd/system/docker.service.d

# 重启docker服务
systemctl daemon-reload && systemctl restart docker && systemctl enable docker
```
#### 下载组件镜像
```bash
# download-image.sh
#!/bin/bash

aliyun_images=(kube-apiserver-amd64:v1.15.1 kube-controller-manager-amd64:v1.15.1 kube-scheduler-amd64:v1.15.1 kube-proxy-amd64:v1.15.1 pause-amd64:3.1 etcd-amd64:3.3.10 coredns:1.3.1)

for image in ${aliyun_images[@]}
do
    docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/$image
    docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/$image k8s.gcr.io/${image/-amd64/}
    docker rmi registry.cn-hangzhou.aliyuncs.com/google_containers/$image
done
```
#### 安装 kubeadm (主从配置)
```bash
cat > /etc/yum.repos.d/kubernetes.repo << EOF
[kubernetes]
name=Kubernetes
baseurl=http://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=0
repo_gpgcheck=0
gpgkey=http://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg
http://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
EOF
yum install -y kubeadm-1.15.1 kubectl-1.15.1 kubelet-1.15.1
systemctl enable kubelet.service
```
#### 初始化主节点
```bash
kubeadm config print init-defaults > kubeadm-config.yaml
# 修改并添加一些字段, 最终文件内容如下
###
apiVersion: kubeadm.k8s.io/v1beta2
bootstrapTokens:
- groups:
  - system:bootstrappers:kubeadm:default-node-token
  token: abcdef.0123456789abcdef
  ttl: 24h0m0s
  usages:
  - signing
  - authentication
kind: InitConfiguration
localAPIEndpoint:
  advertiseAddress: 192.168.0.61
  bindPort: 6443
nodeRegistration:
  criSocket: /var/run/dockershim.sock
  name: k8s-master01
  taints:
  - effect: NoSchedule
    key: node-role.kubernetes.io/master
---
apiServer:
  timeoutForControlPlane: 4m0s
apiVersion: kubeadm.k8s.io/v1beta2
certificatesDir: /etc/kubernetes/pki
clusterName: kubernetes
controllerManager: {}
dns:
  type: CoreDNS
etcd:
  local:
    dataDir: /var/lib/etcd
imageRepository: k8s.gcr.io
kind: ClusterConfiguration
kubernetesVersion: v1.15.1
networking:
  dnsDomain: cluster.local
  podSubnet: 10.244.0.0/16
  serviceSubnet: 10.96.0.0/12
scheduler: {}
---
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
featureGates:
  SupportIPVSProxyMode: true
mode: ipvs
###

kubeadm init --config=kubeadm-config.yaml --experimental-upload-certs | tee kubeadm-init.log
```
#### 加入主节点以及其余工作节点
```bash
执行安装日志中的加入命令即可
```
#### 部署网络
```bash
kubectl apply -f https://github.com/coreos/flannel/blob/master/Documentation/kube-flannel-old.yaml
```
#### 简单使用
```bash
kubectl run nginx-deployment --image=harbor.ninejy.io/myapp:v1 --port=80 --replicas=1
kubectl get deployment
kubectl get rs
kubectl get pod -o wide
curl ${pod_ip}
kubectl delete pod ${pod_name}
kubectl get pod -o wide
kubectl scale --replicas=3 deployment/nginx-deployment
kubectl get pod -o wide
kubectl expose deployment nginx-deployment --port=30000 --target-port=80
curl ${CLUSTER_IP}:30000  # 默认 svc type 为 CLSUTER-IP
kubectl edit svc nginx-deployment  # 修改 svc type 为 NodePort
curl ${node}:${hostPort}

kubectl explain pod

kubectl describe pod ${pod_name}

kubectl logs -f ${pod_name} [-c ${container_name}]

kubectl exec ${pod_name} [-c ${container_name}] -it -- /bin/sh
```
