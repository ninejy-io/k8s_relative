##### promethus server
```shell
wget https://github.com/prometheus/prometheus/releases/download/v2.12.0/prometheus-2.12.0.linux-amd64.tar.gz
tar -zxvf prometheus-2.12.0.linux-amd64.tar.gz

cd prometheus-2.12.0.linux-amd64

# 检查配置
./promtool check config promethus.yml

# 启动
./prometheus &

# 重启
kill -HUP PID

http://localhost:9090
```
---
##### node_exporter
```shell
wget https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-0.18.1.linux-amd64.tar.gz
tar -zxvf node_exporter-0.18.1.linux-amd64.tar.gz

# prometheus-2.12.0.linux-amd64/promethus.yml scrape_configs 段 添加以下内容:
  - job_name: 'node_exporter'
    static_configs:
    - targets: ['localhost:9100']

cd node_exporter-0.18.1.linux-amd64
./node_exporter &

http://localhost:9100/metrics
```
---
##### pushgateway
```shell
wget https://github.com/prometheus/pushgateway/releases/download/v0.9.1/pushgateway-0.9.1.linux-amd64.tar.gz
tar -zxvf pushgateway-0.9.1.linux-amd64.tar.gz

# prometheus-2.12.0.linux-amd64/promethus.yml scrape_configs 段 添加以下内容:
  - job_name: 'pushgateway'
    static_configs:
    - targets: ['192.168.1.11:9091']

cd pushgateway-0.9.1.linux-amd64
./pushgateway &

http://localhost:9091/metrics

# push metric
echo "some_metric 3.14" | curl --data-binary @- http://localhost:9091/metrics/job/some_job
echo 'some_metric{label="val1"} 42' | curl --data-binary @- http://localhost:9091/metrics/job/some_job/instance/some_instance

# delete all metrics in the group identified by {job="some_job",instance="some_instance"}
curl -X DELETE http://localhost:9091/metrics/job/some_job/instance/some_instance

# delete all metrics in the group identified by {job="some_job"}
curl -X DELETE http://localhost:9091/metrics/job/some_job

# delete all metrics in all groups (requires to enable the admin api--web.enable-admin-api)
curl -X PUT http://localhost:9091/api/v1/admin/wipe
```
---
##### alertmanager
```shell
wget https://github.com/prometheus/alertmanager/releases/download/v0.19.0/alertmanager-0.19.0.linux-amd64.tar.gz
tar -zxvf alertmanager-0.19.0.linux-amd64.tar.gz

# prometheus-2.12.0.linux-amd64/promethus.yml 添加以下内容:
###
alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - localhost:9093

rule_files:
  - "node_rules.yml"
###

# 添加文件 prometheus-2.12.0.linux-amd64/node_rules.yml
###
groups:
- name: example
  rules:
  - alert: InstanceDown
    expr: up == 0
    for: 2m
    labels:
      severity: page
    annotations:
      summary: "Instance {{ $labels.instance }} down"
      description: "{{ $labels.instance }} of job {{ $labels.job }} has been down for more than 2 minutes."
###

# alertmanager-0.19.0.linux-amd64/alertmanager.yml 配置邮件告警通知
###
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.163.com:25'
  smtp_from: 'xxx@163.com'
  smtp_auth_username: 'xxx@163.com'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'x-mails'
receivers:
- name: 'x-mails'
  email_configs:
  - send_resolved: true
    to: 'xxx@163.com'
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
###

cd alertmanager-0.19.0.linux-amd64
./alertmanager &

http://localhost:9093/
```
---
##### grafana
```shell
wget https://dl.grafana.com/oss/release/grafana-6.3.5.linux-amd64.tar.gz
tar -zxvf grafana-6.3.5.linux-amd64.tar.gz

cd grafana-6.3.5.linux-amd64
./grafana-server &

http://localhost:3000/
```
