# bind9

## 安装配置 bind9

### 1.1 安装配置 bind9

```bash
# 安装 bind 软件包
yum install bind -y
# rpm -qa bind

# 修配置文件
# vim /etc/named.conf
listen-on port 53 { 192.168.0.201; };
allow-query     { any; };
forwarders      { 114.114.114.114; };
dnssec-enable no;
dnssec-validation no;

# 配置检查
named-checkconf

# 区域配置文件
# vim /etc/named.rfc1912.zones
zone "ninejy.io" IN {
    type master;
    file "ninejy.io.zone";
    allow-update { 192.168.0.201; };
};

zone "ninejy.com" IN {
    type master;
    file "ninejy.com.zone";
    allow-update { 192.168.0.201; };
};

# 
# vim /var/named/ninejy.io.zone
$ORIGIN ninejy.io.
$TTL 600       ; 10 minutes
@       IN SOA  dns.ninejy.io. dnsadmin.ninejy.io. (
                    2021062301 ; serial
                    10800      ; refresh (3 hours)
                    900        ; retry   (15 minutes)
                    604800     ; expire  (1 week)
                    86400 )    ; minimum (1 day)
        NS      dns.ninejy.io.
$TTL 60 ; 1 minute
dns     A  192.168.0.201
k8s-201 A  192.168.0.201
k8s-202 A  192.168.0.202
k8s-203 A  192.168.0.203
k8s-204 A  192.168.0.204
k8s-205 A  192.168.0.205

# vim /var/named/ninejy.com.zone
$ORIGIN ninejy.com.
$TTL 600       ; 10 minutes
@       IN SOA  dns.ninejy.com. dnsadmin.ninejy.com. (
                    2021062301 ; serial
                    10800      ; refresh (3 hours)
                    900        ; retry   (15 minutes)
                    604800     ; expire  (1 week)
                    86400 )    ; minimum (1 day)
        NS      dns.ninejy.com.
$TTL 60 ; 1 minute
dns     A  192.168.0.201

# 启动 bind 服务
systemctl start named
# netstat -antp | grep 53

# 测试域名解析
dig -t A k8s-203.ninejy.io @192.168.0.201 +short

# 好了之后每台机器 dns 改成上面配置的服务器地址
```
