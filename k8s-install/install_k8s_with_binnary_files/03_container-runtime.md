# 三、安装容器运行时

## docker 安装

### 3.1 安装 docker

```bash
yum remove docker docker-common docker-selinux docker-engine
yum install -y yum-utils device-mapper-persistent-data lvm2
wget -O /etc/yum.repos.d/docker-ce.repo https://repo.huaweicloud.com/docker-ce/linux/centos/docker-ce.repo
sed -i 's+download.docker.com+repo.huaweicloud.com/docker-ce+' /etc/yum.repos.d/docker-ce.repo
yum makecache fast
yum install docker-ce -y

mkdir -p /etc/docker/ /data/docker
# vim /etc/docker/daemon.json
{
    "graph": "/data/docker",
    "storage-driver": "overlay2",
    "insecure-registries": ["registry.access.redhat.com","quay.io","harbor.ninejy.com"],
    "registry-mirrors": ["https://q2gr04ke.mirror.aliyuncs.com"],
    "bip": "172.7.21.1/24",
    "exec-opts": ["native.cgroupdriver=systemd"],
    "live-restore": true
}

systemctl enable docker && systemctl restart docker
```
