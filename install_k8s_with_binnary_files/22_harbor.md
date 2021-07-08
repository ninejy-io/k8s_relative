# harbor

## 安装配置 harbor

### 1.1 安装配置 harbor

```bash
wget https://github.com/goharbor/harbor/releases/download/v2.3.0/harbor-offline-installer-v2.3.0.tgz

tar zxf harbor-offline-installer-v2.3.0.tgz -C /opt/
mv /opt/harbor /opt/harbor-v2.3.0
ln -s /opt/harbor-v2.3.0 /opt/harbor

cd /opt/harbor
cp harbor.yml.tmpl harbor.yml
mkdir -p /data/harbor/{data,logs}

# 修改配置文件
# vim /opt/harbor/harbor.yml
hostname: harbor.ninejy.com
http:
  port: 8080
harbor_admin_password: Harbor12345
data_volume: /data/harbor/data
log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200M
    location: /data/harbor/logs
# 由于没有证书, 所以 https 相关的注释掉
#https:
  #port: 443
  #certificate: /your/certificate/path
  #private_key: /your/private/key/path

# 安装 docker-compose
yum install docker-compose -y

# 安装 harbor
./install.sh

docker ps

yum install nginx -y
# rpm -qa nginx
# nginx-1.20.1-2.el7.x86_64

# vim /etc/nginx/conf.d/harbor.ninejy.com.conf
server {
    listen       80;
    server_name  harbor.ninejy.com;

    client_max_body_size  1000m;

    location / {
        proxy_pass http://127.0.0.1:8080;
    }
}

nginx -t
systemctl start nginx
systemctl enable nginx

# vim /var/named/ninejy.com.zone
harbor  A  192.168.0.202

systemctl restart named

dig -t A harbor.ninejy.com +short

# 浏览器打开以下地址
http://harbor.ninejy.com/
# admin/Harbor12345
# 新建一个 public 的项目 public

# 存储镜像到 harbor 仓库中
docker pull nginx:1.20.1
docker tag nginx:1.20.1 harbor.ninejy.com/public/nginx:1.20.1
docker login harbor.ninejy.com
# admin/Harbor12345
docker push harbor.ninejy.com/public/nginx:1.20.1
```
