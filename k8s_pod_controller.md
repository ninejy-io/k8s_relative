### 什么是控制器
###### kubernetes 中内建了很多 controller (控制器), 这相当于一个状态机, 用来控制 Pod 的具体状态和行为
&emsp;
### 控制器类型
---
- ReplicationController 和 ReplicaSet
- Deployment
- DaemonSet
- StatefulSet
- Job/CronJob
- Horizontal Pod Autoscaling
&emsp;
#### ReplicationController 和 ReplicaSet
---
###### ReplicationController (RC) 用来确保容器应用的副本数时钟保持在用户定义的副本数, 即如果有容器异常退出, 会自动创建新的 Pod 来替代, 如果异常多出来的容器也会自动回收
###### 在新版本的 Kubernetes 中建议使用 ReplicaSet 来取代 ReplicationController, ReplicaSet 跟 ReplicationController 没有本质的不同, 只是名字不一样, 并且 ReplicaSet 支持集合式的 selector
&emsp;
#### Deployment
---
###### Deployment 为 Pod 和 ReplicaSet 提供了一个声明式定义 (declarative) 方法, 用来替代以前的 ReplicationController 来方便的管理应用. 典型的应用场景包括:
  - 定义 Delpoyment 来创建 Pod 和 ReplicaSet
  - 滚动升级和回滚应用
  - 扩容和缩容
  - 暂停和继续 Deployment
&emsp;
#### DaemonSet
---
###### DeamonSet 确保全部 (或一些) Node 上运行一个 Pod 的副本. 当有 Node 加入集群时, 也会为他们新增一个 Pod. 当有 Node 从集群中移除时, 这些 Pod 也会被回收. 删除 DaemonSet 将会删除它撞见的所有 Pod
###### 使用 DaemonSet 的一些典型用法:
  - 运行集群存储 daemon, 例如在每个 Node 上运行 `glusterd` `ceph`
  - 在每个 Node 上运行日志收集 daemon, 例如 `fluentd` `logstash`
  - 在每个 Node 上运行监控 daemon, 例如 `Prometheus Node Exporter` `collected` `Datalog`代理, New Relic代理, 或 Ganglia `gmond`
&emsp;
#### Job
---
###### 负责批处理任务, 即仅执行一次的任务, 他保证批处理任务的一个或多个 Pod 成功结束
&emsp;
#### CronJob 在特定的时间循环创建 Job
---
###### CronJob 管理基于时间的 Job, 即:
  - 在给定的时间点只运行一次
  - 周期性的在给定时间点运行
###### 使用前提条件: ** 当前使用的 Kubernetes 集群, 版本 >= 1.8 (对CronJob). 对于先前的版本的集群, 版本 < 1.8, 启动 APIServer 时, 通过传递选项 `--runtime-config=batch/v2alpha1=true`可以开启 batch/v2alpha1 API **
###### 典型的用法如下所示:
  - 在给定的时间点调度 Job 运行
  - 创建周期性运行的 Job, 例如: 数据库备份、发送邮件
&emsp;
#### StatefulSet
---
###### StatefulSet 作为 Controller 为 Pod 提供唯一的标识. 它可以保证部署和 scale 的顺序
###### StatefulSet 是为了解决有状态服务的问题 (对应Deployment和ReplicaSet是为无状态服务而设计), 其应用场景包括:
  - 稳定的持久化存储, 即Pod重新调度后还是能访问到相同的持久化数据, 基于PVC来实现
  - 稳定发网络标志, 即Pod重新调度后其PodName和HostName不变, 基于Headless Service(即没有Cluster IP的Service)来实现
  - 有序部署, 有序扩展, 即Pod是有顺序的, 在部署或者扩展的时候要根据定义的顺序依次执行(即从0到N-1, 在下一个Pod运行之前所有之前的Pod必须都是Runnign和Ready状态), 基于init container来实现
  - 有序收缩, 有序删除(即从N-1到0)
&emsp;
#### Horizontal Pod Autoscaling
---
###### 应用的资源使用率通常有高峰和低谷的时候, 如何削峰填谷, 提高集群整体资源利用率, 让service中的Pod个数自动调整呢? 这就依赖于Horizontal Pod Autoscaling了, 顾名思义, 使Pod水平自动缩放
