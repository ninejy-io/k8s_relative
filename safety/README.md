#### 集群安全机制说明
---
###### Kubernetes 作为一个分布式集群的管理工具, 保证集群的安全性是一个重要的任务. API Server 是集群内部各个组件通信的中介, 也是外部控制的入口. 所以 Kubernets 的安全机制基本就是围绕 API Server 来设计的. Kubernetes 使用了认证 (Authentication)、 鉴权 (Authorization)、 准入控制 (Admission Control) 三部来保证 API Server 的安全
