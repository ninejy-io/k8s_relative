# 二、ETCD 安装

## ETCD 安装

### 2.1 创建基于根证书的 config 配置文件

```bash
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
```

```bash
# vim /root/certs/etcd-csr.json
{
    "CN": "etcd",
    "hosts": [
        "127.0.0.1",
        "192.168.0.201",
        "192.168.0.203",
        "192.168.0.204",
        "192.168.0.205"
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

### 2.2 生成 etcd 认证的证书

```bash
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes etcd-csr.json | cfssljson -bare etcd

# 拷贝根证书到录下
cp etcd-key.pem etcd.pem /etc/kubernetes/ssl/

scp /etc/kubernetes/ssl/{etcd-key.pem,etcd.pem} 192.168.0.204:/etc/kubernetes/ssl/
scp /etc/kubernetes/ssl/{etcd-key.pem,etcd.pem} 192.168.0.205:/etc/kubernetes/ssl/
```

### 2.3 下载并安装配置 etcd

```bash
# 创建 etcd 用户及目录
useradd -s /sbin/nologin -M etcd

mkdir /opt/src
cd /opt/src
wget https://github.com/etcd-io/etcd/releases/download/v3.4.16/etcd-v3.4.16-linux-amd64.tar.gz

tar zxf etcd-v3.4.16-linux-amd64.tar.gz -C /opt/

cd /opt/etcd-v3.4.16-linux-amd64

# 拷贝 etcd 可执行文件到 /usr/local/bin/ 目录下
cp etcd etcdctl /usr/local/bin/

scp /usr/local/bin/{etcd,etcdctl} 192.168.0.204:/usr/local/bin/
scp /usr/local/bin/{etcd,etcdctl} 192.168.0.205:/usr/local/bin/

# 创建 etcd 数据目录
mkdir -p /data/etcd
chown -R etcd:etcd /data/etcd

# systemd service 注意不同的节点修改 name 和 IP
# vim /etc/systemd/system/etcd.service
[Unit]
Description=Etcd Server
After=network.target
After=network-online.target
Wants=network-online.target
Documentation=https://github.com/coreos

[Service]
Type=notify
WorkingDirectory=/data/etcd
ExecStart=/usr/local/bin/etcd \
  --name=etcd-192.168.0.203 \
  --cert-file=/etc/kubernetes/ssl/etcd.pem \
  --key-file=/etc/kubernetes/ssl/etcd-key.pem \
  --peer-cert-file=/etc/kubernetes/ssl/etcd.pem \
  --peer-key-file=/etc/kubernetes/ssl/etcd-key.pem \
  --trusted-ca-file=/etc/kubernetes/ssl/ca.pem \
  --peer-trusted-ca-file=/etc/kubernetes/ssl/ca.pem \
  --initial-advertise-peer-urls=https://192.168.0.203:2380 \
  --listen-peer-urls=https://192.168.0.203:2380 \
  --listen-client-urls=https://192.168.0.203:2379,http://127.0.0.1:2379 \
  --advertise-client-urls=https://192.168.0.203:2379 \
  --initial-cluster-token=etcd-cluster-0 \
  --initial-cluster=etcd-192.168.0.203=https://192.168.0.203:2380,etcd-192.168.0.204=https://192.168.0.204:2380,etcd-192.168.0.205=https://192.168.0.205:2380 \
  --initial-cluster-state=new \
  --data-dir=/data/etcd \
  --wal-dir="" \
  --snapshot-count=50000 \
  --auto-compaction-retention=1 \
  --auto-compaction-mode=periodic \
  --max-request-bytes=10485760 \
  --quota-backend-bytes=8589934592
Restart=always
RestartSec=15
LimitNOFILE=65536
OOMScoreAdjust=-999

[Install]
WantedBy=multi-user.target

# 启动 etcd
systemctl start etcd
systemctl enable etcd

# 检查服务是否正常启动
/opt/etcd/etcdctl endpoint health
/opt/etcd/etcdctl member list
```
