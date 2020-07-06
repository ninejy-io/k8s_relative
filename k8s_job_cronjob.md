#### Job
---
###### 特殊说明
  - spec.template 格式同 Pod
  - RestartPolicy 仅支持 Never 或 OnFailure
  - 单个 Pod 时, 默认 Pod 成功运行后 Job 即结束
  - `.spec.completions`标志 Job 结束需要成功运行的 Pod 个数, 默认为1
  - `.spec.parallelism`标志并行运行的 Pod 的个数, 默认为1
  - `.spec.activeDeadlineSeconds`标志失败 Pod 的重试最大时间, 超过这个时间不会继续重试

###### Example
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  template:
    metadata:
      name: pi
    spec:
      containers:
      - name: pi
        image: perl
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
```
<!-- 查看日志, 可以显示出打印的 2000 位 n 值 -->

#### CronJob
---
###### CronJob Spec
  - `.spec.schedule`: 调度, 必需字段, 指定任务运行周期, 格式同 Cron
  - `.spec.JobTemplate`: Job 模板, 必需字段, 指定需要运行的任务, 格式同 Job
  - `.spec.startingDeadlineSeconds`: 启动 Job 的期限 (秒级别), 该字段是可选的. 如果因为任何原因而错过了被调度的时间, 那么错过执行时间的 Job 将被认为是失败的. 如果没有指定, 则没有期限
  - `.spec.concurrencyPolicy`: 并发策略, 该字段也是可选的. 它指定了如何处理被 CronJob 创建的 Job 的并发执行. 只允许指定下面策略中的一种:
    - `Allow`(默认): 允许并发运行 Job
    - `Forbid`: 禁止并发运行, 如果前一个还没有完成, 则直接跳过下一个
    - `Replace`: 取消当前正在运行的 Job, 用一个新的来替换
  注意: 当前策略只能应用于同一个 CronJob 创建的 Job. 如果存在多个 CronJob, 他们创建的 Job 之间总是允许并发运行.
  - `.spec.suspend`: 挂起, 该字段也是可选的. 如果设置为`true`, 后续所有执行都会被挂起. 它对已经开始执行的 Job 不起作用. 默认值为`false`.
  - `.spec.successfulJobHistoryLimit`和`.spec.failedJobHistoryLimit`: 历史限制, 是可选字段. 它们指定了可以保留多少完成和失败的 Job. 默认情况下, 它们分别设置为`3`和`1`. 设置限制为`0`, 相关类型的 Job 完成后不会被保留.

###### Example
```yaml
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: hello
spec:
  schedule: "*/1 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox
            args:
              - /bin/sh
              - -c
              - date; echo Hello from the kubernetes cluster
          restartPolicy: OnFailure
```
```bash
kubectl get crontab
kubectl get job
```

###### CronJob 本身的一些限制
** 创建 Job 操作应该是幂等的 **