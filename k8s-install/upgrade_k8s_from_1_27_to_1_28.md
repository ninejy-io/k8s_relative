# Upgrade kubernetes from 1.27 to 1.28 (The cluster installed by kubeadm)

## Determine which version to upgrade to

```bash
apt update
apt-cache madison kubeadm

# Upgrading control plane nodes
# Upgrade kubeadm
apt-mark unhold kubeadm && \
apt-get update && apt-get install -y kubeadm='1.28.2-00' && \
apt-mark hold kubeadm

# Verify that the download works and has the expected version
kubeadm version

# Verify the upgrade plan
kubeadm upgrade plan

# 网络不通的情况下提前拉取镜像
kubeadm config images list

export registry_mirror="registry.cn-hangzhou.aliyuncs.com/google_containers"
crictl pull ${registry_mirror}/kube-apiserver:v1.28.2
crictl pull ${registry_mirror}/kube-controller-manager:v1.28.2
crictl pull ${registry_mirror}/kube-scheduler:v1.28.2
crictl pull ${registry_mirror}/kube-proxy:v1.28.2
crictl pull ${registry_mirror}/pause:3.9
crictl pull ${registry_mirror}/etcd:3.5.9-0
crictl pull ${registry_mirror}/coredns:v1.10.1

ctr --namespace=k8s.io image tag ${registry_mirror}/kube-apiserver:v1.28.2 registry.k8s.io/kube-apiserver:v1.28.2
ctr --namespace=k8s.io image tag ${registry_mirror}/kube-controller-manager:v1.28.2 registry.k8s.io/kube-controller-manager:v1.28.2
ctr --namespace=k8s.io image tag ${registry_mirror}/kube-scheduler:v1.28.2 registry.k8s.io/kube-scheduler:v1.28.2
ctr --namespace=k8s.io image tag ${registry_mirror}/kube-proxy:v1.28.2 registry.k8s.io/kube-proxy:v1.28.2
ctr --namespace=k8s.io image tag ${registry_mirror}/pause:3.9 registry.k8s.io/pause:3.9
ctr --namespace=k8s.io image tag ${registry_mirror}/etcd:3.5.9-0 registry.k8s.io/etcd:3.5.9-0
ctr --namespace=k8s.io image tag ${registry_mirror}/coredns:v1.10.1 registry.k8s.io/coredns/coredns:v1.10.1

# Choose a version to upgrade to, and run the appropriate command
kubeadm upgrade apply v1.28.2

# Manually upgrade your CNI provider plugin
# https://v1-28.docs.kubernetes.io/docs/concepts/cluster-administration/addons/

# For the other control plane nodes
kubeadm upgrade node # 多个主节点的情况下, 更新其他主节点的命令


# Prepare the node for maintenance by marking it unschedulable and evicting the workloads
kubectl drain <node-to-drain> --ignore-daemonsets

# Upgrade kubelet and kubectl
apt-mark unhold kubelet kubectl && \
apt-get update && apt-get install -y kubelet='1.28.2-00' kubectl='1.28.2-00' && \
apt-mark hold kubelet kubectl

# Restart the kubelet
systemctl daemon-reload && systemctl restart kubelet

# Bring the node back online by marking it schedulable
kubectl uncordon <node-to-uncordon>


# Upgrade worker nodes
# 1. Upgrade kubeadm

# 2. Execute `kubeadm upgrade node`
kubeadm upgrade node

# 3. Upgrade kubelet
```
