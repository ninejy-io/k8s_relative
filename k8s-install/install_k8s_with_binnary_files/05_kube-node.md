# k8s node

## k8s 运算节点安装

### 5.1 创建 kube node 相关目录

```bash
mkdir -p /var/lib/kubelet /var/lib/kube-proxy /etc/cni/net.d
```

### 5.2 准备 kubelet 证书签名请求
<!-- 注意: 以下步骤每个节点都是 IP 不一样 -->

```bash
# 每个节点准备自己的签名请求
# vim /root/certs/192.168.0.203-kubelet-csr.json
{
    "CN": "system:node:192.168.0.203",
    "hosts": [
        "127.0.0.1",
        "192.168.0.203"
    ],
    "key": {
        "algo": "rsa",
        "size": 2048
    },
    "names": [
        {
            "C": "CN",
            "ST": "Shanghai",
            "L": "XS",
            "O": "system:nodes",
            "OU": "System"
        }
    ]
}
```

### 5.3 创建 kubelet 证书与私钥

```bash
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes 192.168.0.203-kubelet-csr.json | cfssljson -bare 192.168.0.203-kubelet

# 拷贝证书文件到指定节点指定目录下
scp 192.168.0.203-kubelet-key.pem 192.168.0.203:/etc/kubernetes/ssl/kubelet-key.pem
scp 192.168.0.203-kubelet.pem 192.168.0.203:/etc/kubernetes/ssl/kubelet.pem

scp 192.168.0.204-kubelet-key.pem 192.168.0.204:/etc/kubernetes/ssl/kubelet-key.pem
scp 192.168.0.204-kubelet.pem 192.168.0.204:/etc/kubernetes/ssl/kubelet.pem

scp 192.168.0.205-kubelet-key.pem 192.168.0.205:/etc/kubernetes/ssl/kubelet-key.pem
scp 192.168.0.205-kubelet.pem 192.168.0.205:/etc/kubernetes/ssl/kubelet.pem
```

### 5.4 创建 kubelet 访问 kube-apiserver 的凭据

```bash
# 设置集群参数
kubectl config set-cluster kubernetes \
    --certificate-authority=/etc/kubernetes/ssl/ca.pem \
    --embed-certs=true \
    --server=https://192.168.0.200:8443 \
    --kubeconfig=/etc/kubernetes/kubelet.kubeconfig
# 设置客户端认证参数
kubectl config set-credentials system:node:192.168.0.203 \
    --client-certificate=/etc/kubernetes/ssl/kubelet.pem \
    --embed-certs=true \
    --client-key=/etc/kubernetes/ssl/kubelet-key.pem \
    --kubeconfig=/etc/kubernetes/kubelet.kubeconfig
# 设置上下文参数
kubectl config set-context default \
    --cluster=kubernetes \
    --user=system:node:192.168.0.203 \
    --kubeconfig=/etc/kubernetes/kubelet.kubeconfig
# 选择默认上下文
kubectl config use-context default \
    --kubeconfig=/etc/kubernetes/kubelet.kubeconfig
```

### 5.5 创建 kubelet 配置文件

```bash
mkdir -p /etc/kubernetes/kubelet
# vim /etc/kubernetes/kubelet/config.yaml
kind: KubeletConfiguration
apiVersion: kubelet.config.k8s.io/v1beta1
address: 192.168.0.203
authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 2m0s
    enabled: true
  x509:
    clientCAFile: /etc/kubernetes/ssl/ca.pem
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 5m0s
    cacheUnauthorizedTTL: 30s
cgroupDriver: systemd
cgroupsPerQOS: true
clusterDNS:
- 10.68.0.10
clusterDomain: cluster.local
configMapAndSecretChangeDetectionStrategy: Watch
containerLogMaxFiles: 3 
containerLogMaxSize: 10Mi
enforceNodeAllocatable:
- pods
- kube-reserved
eventBurst: 10
eventRecordQPS: 5
evictionHard:
  imagefs.available: 15%
  memory.available: 300Mi
  nodefs.available: 10%
  nodefs.inodesFree: 5%
evictionPressureTransitionPeriod: 5m0s
failSwapOn: true
fileCheckFrequency: 40s
hairpinMode: hairpin-veth 
healthzBindAddress: 192.168.0.203
healthzPort: 10248
httpCheckFrequency: 40s
imageGCHighThresholdPercent: 85
imageGCLowThresholdPercent: 80
imageMinimumGCAge: 2m0s
kubeReservedCgroup: /podruntime.slice
kubeReserved:
  memory: 400Mi
kubeAPIBurst: 100
kubeAPIQPS: 50
makeIPTablesUtilChains: true
maxOpenFiles: 1000000
maxPods: 110
nodeLeaseDurationSeconds: 40
nodeStatusReportFrequency: 1m0s
nodeStatusUpdateFrequency: 10s
oomScoreAdj: -999
podPidsLimit: -1
port: 10250
# disable readOnlyPort 
readOnlyPort: 0
resolvConf: /etc/resolv.conf
runtimeRequestTimeout: 2m0s
serializeImagePulls: true
streamingConnectionIdleTimeout: 4h0m0s
syncFrequency: 1m0s
tlsCertFile: /etc/kubernetes/ssl/kubelet.pem
tlsPrivateKeyFile: /etc/kubernetes/ssl/kubelet-key.pem
```

### 5.6 准备 cni 配置文件

```bash
mkdir -p /etc/cni/net.d

# vim /etc/cni/net.d/10-default.conf
{
    "name": "mynet",
    "cniVersion": "0.7.1",
    "type": "bridge",
    "bridge": "mynet0",
    "isDefaultGateway": true,
    "ipMasq": true,
    "hairpinMode": true,
    "ipam": {
        "type": "host-local",
        "subnet": "172.20.0.0/24"
    }
}

scp /etc/cni/net.d/10-default.conf 192.168.0.204:/etc/cni/net.d/10-default.conf
scp /etc/cni/net.d/10-default.conf 192.168.0.205:/etc/cni/net.d/10-default.conf
```

### 5.7 准备 kubelet systemd service 文件

```bash
# vim /etc/systemd/system/kubelet.service
[Unit]
Description=Kubernetes Kubelet
Documentation=https://github.com/GoogleCloudPlatform/kubernetes

[Service]
WorkingDirectory=/etc/kubernetes/kubelet

ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/cpu/podruntime.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/cpuacct/podruntime.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/cpuset/podruntime.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/memory/podruntime.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/pids/podruntime.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/systemd/podruntime.slice

ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/cpu/system.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/cpuacct/system.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/cpuset/system.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/memory/system.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/pids/system.slice
ExecStartPre=/bin/mkdir -p /sys/fs/cgroup/systemd/system.slice

ExecStart=/usr/local/bin/kubelet \
  --config=/etc/kubernetes/kubelet/config.yaml \
  --cni-bin-dir=/usr/local/bin \
  --cni-conf-dir=/etc/cni/net.d \
  --hostname-override=192.168.0.203 \
  --image-pull-progress-deadline=5m \
  --kubeconfig=/etc/kubernetes/kubelet.kubeconfig \
  --network-plugin=cni \
  --pod-infra-container-image=easzlab/pause-amd64:3.4.1 \
  --root-dir=/etc/kubernetes/kubelet \
  --v=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

# 启动 kubelet 服务
systemctl enable kubelet
systemctl start kubelet
```

### 5.8 准备 kube-proxy 配置文件

```bash
mkdir /etc/kubernetes/kube-proxy

# vim /etc/kubernetes/kube-proxy/kube-proxy-config.yaml
kind: KubeProxyConfiguration
apiVersion: kubeproxy.config.k8s.io/v1alpha1
bindAddress: 192.168.0.203
clientConnection:
  kubeconfig: "/etc/kubernetes/kube-proxy.kubeconfig"
clusterCIDR: "172.20.0.0/24"
conntrack:
  maxPerCore: 32768
  min: 131072
  tcpCloseWaitTimeout: 1h0m0s
  tcpEstablishedTimeout: 24h0m0s
healthzBindAddress: 192.168.0.203:10256
hostnameOverride: 192.168.0.203
metricsBindAddress: 192.168.0.203:10249
mode: ipvs
```

### 5.9 准备 kube-proxy systemd service 文件

```bash
# vim /etc/systemd/system/kube-proxy.service
[Unit]
Description=Kubernetes Kube-Proxy Server
Documentation=https://github.com/GoogleCloudPlatform/kubernetes
After=network.target

[Service]
# kube-proxy 根据 --cluster-cidr 判断集群内部和外部流量，指定 --cluster-cidr 或 --masquerade-all 选项后，kube-proxy 会对访问 Service IP 的请求做 SNAT
WorkingDirectory=/etc/kubernetes/kube-proxy
ExecStart=/usr/local/bin/kube-proxy \
  --config=/etc/kubernetes/kube-proxy/kube-proxy-config.yaml
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target

# 启动 kube-proxy 服务
systemctl enable kube-proxy
systemctl start kube-proxy
```

### 5.10 设置 node 标签

```bash
kubectl label node 192.168.0.205 kubernetes.io/role=node --overwrite
```
