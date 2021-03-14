---
## k8s 调度 GPU

#### 1. 首先得有一个可以运行的 k8s 集群. 集群部署参考[kubeadm安装k8s](https://www.cnblogs.com/ninejy/p/13996486.html)

#### 2. 准备 GPU 节点

- 2.1 安装驱动

```bash
apt-get install cuda-drivers-455 # 按需要安装对应的版本
```

- 2.2 安装 `nvidia-docker2`

<!-- Note that you need to install the nvidia-docker2 package and not the nvidia-container-toolkit. This is because the new --gpus options hasn't reached kubernetes yet -->

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2

## /etc/docker/daemon.json 文件中加入以下内容, 使默认的运行时是 nvidia
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "/usr/bin/nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}

## 重启 docker
sudo systemctl restart docker
```

- 2.3 在 k8s 集群中安装 `nvidia-device-plugin` 使集群支持 GPU

```bash
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.7.3/nvidia-device-plugin.yml

## 如果因为网络问题访问不到该文件, 可在浏览器打开 https://github.com/NVIDIA/k8s-device-plugin/blob/v0.7.3/nvidia-device-plugin.yml
## 文件内容拷贝到本地执行
```
`nvidia-device-plugin` 做三件事情
- Expose the number of GPUs on each nodes of your cluster
- Keep track of the health of your GPUs
- Run GPU enabled containers in your Kubernetes cluster.

###### 之后把节点加入 k8s 集群
###### 以上步骤成功完成之后, 运行以下命令
```bash
kubectl get pod --all-namespaces | grep nvidia
kubectl describe node 10.31.0.17
```


#### 3. 运行 GPU Jobs

```yaml
# cat nvidia-gpu-demo.yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
    - name: cuda-container
      image: nvidia/cuda:9.0-devel
      resources:
        limits:
          nvidia.com/gpu: 2 # requesting 2 GPUs
    - name: digits-container
      image: nvidia/digits:6.0
      resources:
        limits:
          nvidia.com/gpu: 2 # requesting 2 GPUs
```

```bash
kubectl apply -f nvidia-gpu-demo.yaml

kubectl exec -it xxx-76dd5bd849-hlmdr -- bash

# nvidia-smi
```


