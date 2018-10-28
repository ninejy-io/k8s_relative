###### 1.下载MySQL/PHP/nginx镜像
```shell
docker pull daocloud.io/library/mysql:5.7
docker pull richarvey/nginx-php-fpm
git clone https://git.coding.net/aminglinux/k8s_discuz.git
cd k8s_discuz/dz_web_dockerfile/
docker build -t nginx-php .
```
###### 2.将下载的镜像push到harbor私有镜像仓库
```shell
docker tag daocloud.io/library/mysql:5.7 harbor.dog128.cn/jy90/mysql:5.7
docker push harbor.dog128.cn/jy90/mysql:5.7
docker tag nginx-php harbor.dog128.cn/jy90/nginx-php
docker push harbor.dog128.cn/jy90/nginx-php
```
###### 3.搭建NFS服务
```shell
apt-get install -y nfs-kernel-server

# vim /etc/exports
/data/k8s/ 192.168.1.0/24(sync,rw,no_roo_squash)

systemctl start nfs-server
systemctl enable nfs-server

mkdir -p /data/k8s/discuz/{db,web}
```
###### 4.搭建MySQL服务
- 创建secret (设定MySQL的root密码)
```shell
kubectl create secret generic mysql-pass --from-literal=password=DzPasswd1
```
- 创建 mysql pv
```shell
cd ../../k8s_discuz/mysql/
# 修改 mysql-pv.yaml 中server地址为自己的实际nfs-server地址(我这里是: 192.168.1.202)
kubectl create -f mysql-pv.yaml
```
- 创建 mysql pvc
```shell
kubectl create -f mysql-pvc.yaml
```
- 创建 mysql deployment
```shell
# 修改 mysql-dp.yaml 中image地址为自己实际的harbor仓库地址(我这里是: harbor.dog128.cn/jy90/mysql:5.7)
kubectl create -f mysql-dp.yaml
```
- 创建 mysql service
```shell
kubectl create -f mysql-svc.yaml
```
###### 5.搭建nginx+php-fpm服务
- 创建 web pv
```shell
cd ../nginx_php/
# 修改 web-pv.yaml 中server地址为自己的实际nfs-server地址(我这里是: 192.168.1.202)
kubectl create -f web-pv.yaml
```
- 创建 web pvc
```shell
kubectl create -f web-pvc.yaml
```
- 创建 web deployment
```shell
# 修改 web-dp.yaml 中image地址为自己实际的harbor仓库地址(我这里是: harbor.dog128.cn/jy90/nginx-php)
kubectl create -f web-dp.yaml
```
- 创建 web service
```shell
kubectl create -f web-svc.yaml
```
###### 6.安装discuz
- 下载discuz代码到NFS服务器
```shell
cd /tmp/
git clone https://gitee.com/ComsenzDiscuz/DiscuzX.git
cd /data/k8s/discuz/web/
mv /tmp/DiscuzX/upload/* .
chown -R 100 data uc_server/data/ uc_client/data/ config/
```
- 设置MySQL普通用户
```shell
kubectl get svc  # 查看MySQL service的IP地址 (我这里是: 10.96.75.127)
mysql -h10.96.75.127 -uroot -pDzPasswd1
> create database dz;
> grant all on dz.* to 'dz'@'%' identified by 'dz-passwd-123';
```
- 设置nginx代理
```shell
# cat /etc/nginx/conf.d/dz.conf
server {
    listen 80;
    server_name dz.dog128.cn;
    index index.html index.php;

    location / {
        proxy_pass http://10.96.222.181:80;
    }
}
```
