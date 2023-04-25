# Install kubernetes 1.27 on ubuntu 18.04

- 主机准备

  | 角色       | 主机名         | IP             |
  | ---------- | -------------- | -------------- |
  | k8s-master | k8s-127-100-38 | 192.168.100.38 |
  | k8s-worker | k8s-127-100-39 | 192.168.100.39 |

  ```bash
  # 设置主机名
  hostnamectl set-hostname k8s-127-100-38
  hostnamectl set-hostname k8s-127-100-39
  
  # /etc/hosts 配置主机名IP映射
  192.168.100.38 k8s-127-100-38
  192.168.100.39 k8s-127-100-39
  ```

- 安装基础包

  ```bash
  apt-get update -y && apt-get install -y ipvsadm conntrack socat apt-transport-https ca-certificates curl software-properties-common libseccomp-dev
  ```

- 关闭防火墙、关闭swap

  ```bash
  systemctl stop ufw && systemctl disable ufw && systemctl status ufw
  swapoff -a && sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
  ```

- 设置内核参数

  ```bash
  # 加载 br_netfilter 模块
  lsmod | grep br_netfilter
  modprobe br_netfilter
  
  # cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
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

- 安装 containerd

  ```bash
  wget https://github.com/containerd/containerd/releases/download/v1.7.0/cri-containerd-1.7.0-linux-amd64.tar.gz
  
  tar xf cri-containerd-1.7.0-linux-amd64.tar.gz -C /
  mkdir -p /etc/containerd
  containerd config default > /etc/containerd/config.toml
  
  # pasue 镜像版本改成 3.9
  # sandbox_image = "registry.k8s.io/pause:3.9"
  
  # 设置 containerd 开机启动
  systemctl enable containerd
  # containerd
  ```

- 安装 kubeadm / kubelet / kubectl

  ```bash
  apt-get update && apt-get install -y apt-transport-https
  curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | apt-key add - 
  cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
  deb https://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
  EOF
  apt-get update
  apt-cache madison kubeadm
  apt-get install -y kubelet=1.27.1-00 kubeadm=1.27.1-00 kubectl=1.27.1-00
  
  # 设置 kubelet --cgroup-driver=systemd
  echo 'KUBELET_EXTRA_ARGS="--cgroup-driver=systemd"' > /etc/default/kubelet
  
  # 设置 kubelet 开机启动
  systemctl enable kubelet.service
  ```

- 使用 kubeadm 初始化 k8s 集群

  ```bash
  # 查看需要的镜像
  kubeadm config images list
  
  # 拉取镜像
  kubeadm config images pull  # 网络不通的话需要国内镜像仓库手动下载
  
  export registry_mirror="registry.cn-hangzhou.aliyuncs.com/google_containers"
  crictl pull ${registry_mirror}/kube-apiserver:v1.27.1 
  crictl pull ${registry_mirror}/kube-controller-manager:v1.27.1
  crictl pull ${registry_mirror}/kube-scheduler:v1.27.1
  crictl pull ${registry_mirror}/kube-proxy:v1.27.1
  crictl pull ${registry_mirror}/pause:3.9
  crictl pull ${registry_mirror}/etcd:3.5.7-0
  crictl pull ${registry_mirror}/coredns:v1.10.1
  
  ctr --namespace=k8s.io image tag ${registry_mirror}/kube-apiserver:v1.27.1 registry.k8s.io/kube-apiserver:v1.27.1
  ctr --namespace=k8s.io image tag ${registry_mirror}/kube-controller-manager:v1.27.1 registry.k8s.io/kube-controller-manager:v1.27.1
  ctr --namespace=k8s.io image tag ${registry_mirror}/kube-scheduler:v1.27.1 registry.k8s.io/kube-scheduler:v1.27.1
  ctr --namespace=k8s.io image tag ${registry_mirror}/kube-proxy:v1.27.1 registry.k8s.io/kube-proxy:v1.27.1
  ctr --namespace=k8s.io image tag ${registry_mirror}/pause:3.9 registry.k8s.io/pause:3.9
  ctr --namespace=k8s.io image tag ${registry_mirror}/etcd:3.5.7-0 registry.k8s.io/etcd:3.5.7-0
  ctr --namespace=k8s.io image tag ${registry_mirror}/coredns:v1.10.1 registry.k8s.io/coredns/coredns:v1.10.1
  
  # 初始化 k8s 集群
  kubeadm init --kubernetes-version=v1.27.1 --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=192.168.100.38 --cri-socket unix:///var/run/containerd/containerd.sock
  
  # 加入 worker 节点，命令从下面输出中复制 kubeadm join xxx
  
  # 如果有问题需要重新初始化要先执行 kubeadm reset
  ```

  ```bash
  # 以下为输出内容
  [init] Using Kubernetes version: v1.27.1
  [preflight] Running pre-flight checks
  [preflight] Pulling images required for setting up a Kubernetes cluster
  [preflight] This might take a minute or two, depending on the speed of your internet connection
  [preflight] You can also perform this action in beforehand using 'kubeadm config images pull'
  W0424 17:35:37.236084   31069 images.go:80] could not find officially supported version of etcd for Kubernetes v1.27.1, falling back to the nearest etcd version (3.5.7-0)
  [certs] Using certificateDir folder "/etc/kubernetes/pki"
  [certs] Generating "ca" certificate and key
  [certs] Generating "apiserver" certificate and key
  [certs] apiserver serving cert is signed for DNS names [k8s-127-100-38 kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local] and IPs [10.96.0.1 192.168.100.38]
  [certs] Generating "apiserver-kubelet-client" certificate and key
  [certs] Generating "front-proxy-ca" certificate and key
  [certs] Generating "front-proxy-client" certificate and key
  [certs] Generating "etcd/ca" certificate and key
  [certs] Generating "etcd/server" certificate and key
  [certs] etcd/server serving cert is signed for DNS names [k8s-127-100-38 localhost] and IPs [192.168.100.38 127.0.0.1 ::1]
  [certs] Generating "etcd/peer" certificate and key
  [certs] etcd/peer serving cert is signed for DNS names [k8s-127-100-38 localhost] and IPs [192.168.100.38 127.0.0.1 ::1]
  [certs] Generating "etcd/healthcheck-client" certificate and key
  [certs] Generating "apiserver-etcd-client" certificate and key
  [certs] Generating "sa" key and public key
  [kubeconfig] Using kubeconfig folder "/etc/kubernetes"
  [kubeconfig] Writing "admin.conf" kubeconfig file
  [kubeconfig] Writing "kubelet.conf" kubeconfig file
  [kubeconfig] Writing "controller-manager.conf" kubeconfig file
  [kubeconfig] Writing "scheduler.conf" kubeconfig file
  [kubelet-start] Writing kubelet environment file with flags to file "/var/lib/kubelet/kubeadm-flags.env"
  [kubelet-start] Writing kubelet configuration to file "/var/lib/kubelet/config.yaml"
  [kubelet-start] Starting the kubelet
  [control-plane] Using manifest folder "/etc/kubernetes/manifests"
  [control-plane] Creating static Pod manifest for "kube-apiserver"
  [control-plane] Creating static Pod manifest for "kube-controller-manager"
  [control-plane] Creating static Pod manifest for "kube-scheduler"
  [etcd] Creating static Pod manifest for local etcd in "/etc/kubernetes/manifests"
  W0424 17:35:59.473567   31069 images.go:80] could not find officially supported version of etcd for Kubernetes v1.27.1, falling back to the nearest etcd version (3.5.7-0)
  [wait-control-plane] Waiting for the kubelet to boot up the control plane as static Pods from directory "/etc/kubernetes/manifests". This can take up to 4m0s
  [apiclient] All control plane components are healthy after 21.504414 seconds
  [upload-config] Storing the configuration used in ConfigMap "kubeadm-config" in the "kube-system" Namespace
  [kubelet] Creating a ConfigMap "kubelet-config" in namespace kube-system with the configuration for the kubelets in the cluster
  [upload-certs] Skipping phase. Please see --upload-certs
  [mark-control-plane] Marking the node k8s-127-100-38 as control-plane by adding the labels: [node-role.kubernetes.io/control-plane node.kubernetes.io/exclude-from-external-load-balancers]
  [mark-control-plane] Marking the node k8s-127-100-38 as control-plane by adding the taints [node-role.kubernetes.io/control-plane:NoSchedule]
  [bootstrap-token] Using token: 7m63w8.j3ogpypf7z1dekq2
  [bootstrap-token] Configuring bootstrap tokens, cluster-info ConfigMap, RBAC Roles
  [bootstrap-token] Configured RBAC rules to allow Node Bootstrap tokens to get nodes
  [bootstrap-token] Configured RBAC rules to allow Node Bootstrap tokens to post CSRs in order for nodes to get long term certificate credentials
  [bootstrap-token] Configured RBAC rules to allow the csrapprover controller automatically approve CSRs from a Node Bootstrap Token
  [bootstrap-token] Configured RBAC rules to allow certificate rotation for all node client certificates in the cluster
  [bootstrap-token] Creating the "cluster-info" ConfigMap in the "kube-public" namespace
  [kubelet-finalize] Updating "/etc/kubernetes/kubelet.conf" to point to a rotatable kubelet client certificate and key
  [addons] Applied essential addon: CoreDNS
  [addons] Applied essential addon: kube-proxy
  
  Your Kubernetes control-plane has initialized successfully!
  
  To start using your cluster, you need to run the following as a regular user:
  
    mkdir -p $HOME/.kube
    sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
  
  Alternatively, if you are the root user, you can run:
  
    export KUBECONFIG=/etc/kubernetes/admin.conf
  
  You should now deploy a pod network to the cluster.
  Run "kubectl apply -f [podnetwork].yaml" with one of the options listed at:
    https://kubernetes.io/docs/concepts/cluster-administration/addons/
  
  Then you can join any number of worker nodes by running the following on each as root:
  
  kubeadm join 192.168.100.38:6443 --token 7m63w8.j3ogpypf7z1dekq2 \
          --discovery-token-ca-cert-hash sha256:ba8ff856fa19dcc807cf4458ff6942e99988267043c8f1665469e827d04cea41
  ```

- 安装网络插件

  ```bash
  kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
  ```
