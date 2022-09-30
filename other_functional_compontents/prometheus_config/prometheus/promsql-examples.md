# promsql examples

## node_exporter-1.3.1.linux-amd64

### 函数 `increase`, `rate` 都针对 `Counter` 类型的数据使用

#### `increase()` 一段时间内的增量

#### `rate()` 一段时间内单位时间的增量

- CPU 使用率

```bash
(1-(sum(increase(node_cpu_seconds_total{mode="idle"}[1m])) by (instance) / sum(increase(node_cpu_seconds_total[1m])) by (instance))) * 100
```

- 网卡进流量

```bash
rate(node_network_receive_bytes_total{device=~"enp.*"}[1m])
```

- 网卡出流量

```bash
rate(node_network_transmit_bytes_total{device=~"enp.*"}[1m])
```

- 内存空闲最多的一台机器 (`topk` 函数针对 `Gauge` 类型数据的使用)

```bash
topk(1,node_memory_MemFree_bytes)
```

- 网卡进流量最多的一台机器 (`topk` 函数针对 `Counter` 类型数据的使用)

```bash
topk(1,rate(node_network_receive_bytes_total{device=~"enp.*"}[1m]))
```

- 空闲内存大于 2G 的机器数量

```bash
count(node_memory_MemFree_bytes > 2048000000)
```
