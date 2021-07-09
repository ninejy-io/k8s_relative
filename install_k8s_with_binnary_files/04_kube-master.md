# k8s master

## k8s 主控节点安装

### 4.1 创建 kubernetes 证书签名请求

```bash
# vim /root/certs/kubernetes-csr.json
{
    "CN": "kubernetes",
    "hosts": [
        "127.0.0.1",
        "10.68.0.1",
        "192.168.0.200",
        "192.168.0.203",
        "192.168.0.204",
        "192.168.0.205",
        "kubernetes",
        "kubernetes.default",
        "kubernetes.default.svc",
        "kubernetes.default.svc.cluster",
        "kubernetes.default.svc.cluster.local"
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
            "O": "k8s",
            "OU": "System"
        }
    ]
}
```

### 4.2 创建 kubernetes 证书和私钥

```bash
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes kubernetes-csr.json | cfssljson -bare kubernetes

# 拷贝证书到目录下
cp kubernetes-key.pem kubernetes.pem /etc/kubernetes/ssl/

scp /etc/kubernetes/ssl/{kubernetes-key.pem,kubernetes.pem} 192.168.0.204:/etc/kubernetes/ssl/
```

### 4.3 创建 aggregator proxy 证书签名请求

```bash
# vim /root/certs/aggregator-proxy-csr.json
{
    "CN": "aggregator",
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
```

### 4.4 创建 aggregator-proxy 证书和私钥

```bash
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes aggregator-proxy-csr.json | cfssljson -bare aggregator-proxy

# 拷贝证书到目录下
cp aggregator-proxy-key.pem aggregator-proxy.pem /etc/kubernetes/ssl/

scp /etc/kubernetes/ssl/{aggregator-proxy-key.pem,aggregator-proxy.pem} 192.168.0.204:/etc/kubernetes/ssl/
```

### 4.5 准备 kube-apiserver systemd service 文件

```bash
# vim /etc/systemd/system/kube-apiserver.service
[Unit]
Description=Kubernetes API Server
Documentation=https://github.com/GoogleCloudPlatform/kubernetes
After=network.target

[Service]
ExecStart=/usr/local/bin/kube-apiserver \
  --advertise-address=192.168.0.203 \
  --allow-privileged=true \
  --anonymous-auth=false \
  --api-audiences=api,istio-ca \
  --authorization-mode=Node,RBAC \
  --bind-address=127.0.0.1,192.168.0.203 \
  --client-ca-file=/etc/kubernetes/ssl/ca.pem \
  --endpoint-reconciler-type=lease \
  --etcd-cafile=/etc/kubernetes/ssl/ca.pem \
  --etcd-certfile=/etc/kubernetes/ssl/kubernetes.pem \
  --etcd-keyfile=/etc/kubernetes/ssl/kubernetes-key.pem \
  --etcd-servers=https://192.168.0.203:2379,https://192.168.0.204:2379,https://192.168.0.205:2379 \
  --kubelet-certificate-authority=/etc/kubernetes/ssl/ca.pem \
  --kubelet-client-certificate=/etc/kubernetes/ssl/kubernetes.pem \
  --kubelet-client-key=/etc/kubernetes/ssl/kubernetes-key.pem \
  --secure-port=6443 \
  --service-account-issuer=https://kubernetes.default.svc \
  --service-account-signing-key-file=/etc/kubernetes/ssl/ca-key.pem \
  --service-account-key-file=/etc/kubernetes/ssl/ca.pem \
  --service-cluster-ip-range=10.68.0.0/16 \
  --service-node-port-range=30000-39999 \
  --tls-cert-file=/etc/kubernetes/ssl/kubernetes.pem \
  --tls-private-key-file=/etc/kubernetes/ssl/kubernetes-key.pem \
  --requestheader-client-ca-file=/etc/kubernetes/ssl/ca.pem \
  --requestheader-allowed-names= \
  --requestheader-extra-headers-prefix=X-Remote-Extra- \
  --requestheader-group-headers=X-Remote-Group \
  --requestheader-username-headers=X-Remote-User \
  --proxy-client-cert-file=/etc/kubernetes/ssl/aggregator-proxy.pem \
  --proxy-client-key-file=/etc/kubernetes/ssl/aggregator-proxy-key.pem \
  --enable-aggregator-routing=true \
  --v=2
Restart=always
RestartSec=5
Type=notify
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target

# 203,204 节点都有相同的文件注意修改 IP
# 启动 kube-apiserver
systemctl start kube-apiserver
systemctl enable kube-apiserver
```

### 4.6 配置 kube-apiserver 负载均衡及高可用

```bash
# 192.168.0.203, 192.168.0.204
yum install nginx nginx-mod-stream.x86_64 -y
# rpm -qa nginx
# nginx-1.20.1-2.el7.x86_64

# nginx 配置文件
# vim /etc/nginx/nginx.conf
stream {
    upstream kube-apiserver {
        server 192.168.0.203:6443  max_fails=3 fail_timeout=30s;
        server 192.168.0.204:6443  max_fails=3 fail_timeout=30s;
    }
    server {
        listen 8443;
        proxy_connect_timeout 1s;
        proxy_timeout 600s;
        proxy_pass kube-apiserver;
    }
}

# 启动 nginx
nginx -t
systemctl start nginx
systemctl enable nginx

# 安装 keepalived, 配置高可用 VIP: 192.168.0.200
yum install keepalived -y
# rpm -qa keepalived
# keepalived-1.3.5-19.el7.x86_64

# 192.168.0.203 master
# vim /etc/keepalived/keepalived.conf
global_defs {
    router_id 192.168.0.203
}

vrrp_script chk_nginx {
    script "/etc/keepalived/check_port.sh 8443"
    interval 2
    weight -20
}

vrrp_instance VI_1 {
    state MASTER
    interface enp0s3
    virtual_router_id 51
    priority 100
    advert_int 1
    nopreempt

    authentication {
        auth_type PASS
        auth_pass 11111111
    }
    track_script {
        chk_nginx
    }
    virtual_ipaddress {
        192.168.0.200
    }
}

# 192.168.0.204 backup
# vim /etc/keepalived/keepalived.conf
global_defs {
    router_id 192.168.0.204
}

vrrp_script chk_nginx {
    script "/etc/keepalived/check_port.sh 8443"
    interval 2
    weight -20
}

vrrp_instance VI_1 {
    state BACKUP
    interface enp0s3
    virtual_router_id 51
    priority 90
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass 11111111
    }
    track_script {
        chk_nginx
    }
    virtual_ipaddress {
        192.168.0.200
    }
}

# vim /etc/keepalived/check_port.sh
#!/bin/bash
CHK_PORT=$1
if [ -n ${CHK_PORT} ]; then
    port_process_num=`ss -nlt | grep ${CHK_PORT} | wc -l`
    if [ ${port_process_num} -eq 0 ]; then
        echo "Port ${CHK_PORT} is not used."
        exit 1
    fi
else
    echo "Check port can be empty!"
fi

chmod +x /etc/keepalived/check_port.sh

# 启动 keepalived
systemctl start keepalived
systemctl enable keepalived
```

### 4.7 准备 kube-controller-manager systemd service 文件

```bash
# 192.168.0.204, 192.168.0.204 两个节点都有. 注意修改 IP
# vim /etc/systemd/system/kube-controller-manager.service
[Unit]
Description=Kubernetes Controller Manager
Documentation=https://github.com/GoogleCloudPlatform/kubernetes

[Service]
ExecStart=/usr/local/bin/kube-controller-manager \
  --bind-address=192.168.0.203 \
  --allocate-node-cidrs=true \
  --cluster-cidr=172.20.0.0/16 \
  --cluster-name=kubernetes \
  --cluster-signing-cert-file=/etc/kuernetes/ssl/ca.pem \
  --cluster-signing-key-file=/etc/kuernetes/ssl/ca-key.pem \
  --kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig \
  --leader-elect=true \
  --node-cidr-mask-size=24 \
  --root-ca-file=/etc/kuernetes/ssl/ca.pem \
  --service-account-private-key-file=/etc/kuernetes/ssl/ca-key.pem \
  --service-cluster-ip-range=10.68.0.0/16 \
  --use-service-account-credentials=true \
  --v=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

# 启动 kube-controller-manager
systemctl start kube-controller-manager
systemctl enable kube-controller-manager
```

### 4.8 创建 kube-scheduler 配置文件

```bash
# vim /etc/kubernetes/kube-scheduler-config.yaml
apiVersion: kubescheduler.config.k8s.io/v1beta1
kind: KubeSchedulerConfiguration
clientConnection:
    kubeconfig: "/etc/kubernetes/kube-scheduler.kubeconfig"
healthzBindAddress: 0.0.0.0:10251
leaderElection:
    leaderElect: true
metricsBindAddress: 0.0.0.0:10251

# 拷贝 kube-scheduler 配置文件文件到 192.168.0.204
scp /etc/kubernetes/kube-scheduler-config.yaml 192.168.0.204:/etc/kubernetes/kube-scheduler-config.yaml
```

### 4.9 准备 kube-scheduler systemd service 文件

```bash
# 192.168.0.204, 192.168.0.204 两个节点都有
# vim /etc/systemd/system/kube-scheduler.service
[Unit]
Description=Kubernetes Scheduler
Documentation=https://github.com/GoogleCloudPlatform/kubernetes

[Service]
ExecStart=/usr/local/bin/kube-scheduler \
  --config=/etc/kubernetes/kube-scheduler-config.yaml \
  --v=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

# 启动 kube-scheduler
systemctl start kube-scheduler
systemctl enable kube-scheduler
```

### 4.10 创建 user:kubernetes 角色绑定

```bash
kubectl create clusterrolebinding kubernetes-crb --clusterrole=cluster-admin --user=kubernetes
```
