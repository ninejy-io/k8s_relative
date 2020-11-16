```bash
Ubuntu 18.04
docker 19.03
kubeadm 1.18.2
```
#### 设置主机名和hosts

```bash
hostnamectl set-hostname k8s-master01
hostnamectl set-hostname k8s-node01

# cat /etc/hosts
192.168.0.3 k8s-master01
192.168.0.6 k8s-node01
```

#### 关闭 swap
```bash
swapoff -a && sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

#### 安装依赖包

```bash
apt-get update -y && apt-get install -y ipvsadm conntrack socat apt-transport-https ca-certificates curl software-properties-common
```

#### 配置内核参数

```bash
lsmod | grep br_netfilter
modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
net.ipv6.conf.all.disable_ipv6 = 1
net.netfilter.nf_conntrack_max = 2310720
vm.swappiness = 0
vm.overcommit_memory = 1
vm.panic_on_oom = 0
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 1048576
fs.file-max = 52706963
fs.nr_open = 52706963
EOF

sysctl -p /etc/sysctl.d/k8s.conf
```

#### Install docker

```bash
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable"
apt-get -y update
apt-cache madison docker-ce
apt-get install -y docker-ce=5:19.03.9~3-0~ubuntu-bionic
docker version
```

#### 配置加速源并配置docker的启动参数使用systemd

```bash
mkdir -p /etc/docker/
cat>/etc/docker/daemon.json<<EOF
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "registry-mirrors": [
      "https://fz5yth0r.mirror.aliyuncs.com",
      "https://dockerhub.mirrors.nwafu.edu.cn/",
      "https://mirror.ccs.tencentyun.com",
      "https://docker.mirrors.ustc.edu.cn/",
      "https://reg-mirror.qiniu.com",
      "http://hub-mirror.c.163.com/",
      "https://registry.docker-cn.com"
  ],
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF

mkdir -p /etc/systemd/system/docker.service.d
systemctl restart docker && systemctl enable docker.service
```

#### Install kubeadm / kubectl / kubelet

```bash
curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | apt-key add -

cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb https://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
EOF

apt-get -y update
apt-cache madison kubeadm
apt-get install -y kubeadm=1.18.2-00 kubelet=1.18.2-00 kubectl=1.18.2-00
systemctl enable kubelet.service
```

#### 下载镜像

```bash
# cat download_images.sh
#!/bin/bash

aliyun_images=(kube-apiserver-amd64:v1.18.2 kube-controller-manager-amd64:v1.18.2 kube-scheduler-amd64:v1.18.2 kube-proxy-amd64:v1.18.2 pause-amd64:3.2 etcd-amd64:3.4.3-0)

for image in ${aliyun_images[@]}
do
    docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/$image
    docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/$image k8s.gcr.io/${image/-amd64/}
    docker rmi registry.cn-hangzhou.aliyuncs.com/google_containers/$image
done

docker pull registry.cn-hangzhou.aliyuncs.com/google_containers/coredns:1.6.7
docker tag registry.cn-hangzhou.aliyuncs.com/google_containers/coredns:1.6.7 k8s.gcr.io/coredns:1.6.7

docker pull ninejy/flannel:v0.13.0
docker tag ninejy/flannel:v0.13.0 quay.io/coreos/flannel:v0.13.0
#

bash -x download_images.sh
```

<!-- 以上操作 master/node 节点均需执行 -->


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
  advertiseAddress: 192.168.0.3
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
kubernetesVersion: v1.18.2
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

kubeadm init --config=kubeadm-config.yaml --upload-certs | tee kubeadm-init.log
```

#### 设置 kubectl 到k8s集群的认证配置
```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

#### 加入其它(node)节点

```bash
# 到其他节点上执行上一步日志中的 `kubeadm join xxx` 命令即可
```

#### 部署网络

```bash
# https://github.com/coreos/flannel/blob/master/Documentation/kube-flannel.yml
# 下载该文件
kubectl apply -f kube-flannel.yaml
```

#### 查看集群节点和集群状态
```bash
kubectl get nodes
kubectl get cs
kubectl cluster-info
kubectl get pod --all-namespaces
```
