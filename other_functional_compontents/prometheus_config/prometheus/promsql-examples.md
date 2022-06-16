# promsql examples

## CPU 使用率

```bash
(1-(sum(increase(node_cpu_seconds_total{mode="idle"}[1m])) by (instance) / sum(increase(node_cpu_seconds_total[1m])) by (instance))) * 100
```
