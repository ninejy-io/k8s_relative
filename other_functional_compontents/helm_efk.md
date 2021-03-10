#### 添加 Google incubator 仓库
---
```bash
helm repo add incubator http://storage.googleapis.com/kubernetes-charts-incubator
```

#### 部署 Elasticsearch
---
```bash
kubectl create namespace efk
helm fetch incubator/elasticsearch
helm install --name els1 --namespace=efk -f values.yaml
kubectl run cirror-$RANDOM --rm -it --image=cirros -- /bin/sh
  curl $elasticsearch:9200/_cat/nodes
```

#### 部署 Fluented
---
```bash
helm fetch stable/fluentd-elasticsearch
vim values.yaml  # 修改其中 Elasticsearch 访问地址
helm install --name flu1 --namespace=efk -f values.yaml
```

#### 部署 kibana
---
```bash
helm fetch stable/kibana --version 0.14.8
vim values.yaml  # 修改其中 Elasticsearch 访问地址
helm install --name kib1 --namespace=efk -f values.yaml
```
