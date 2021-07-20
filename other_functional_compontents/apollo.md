# Apollo

## 1) Deploy apollo on k8s

### 1.1 准备数据库

```bash
create database ApolloConfigDB default charset utf8mb4;
create database ApolloPortalDB default charset utf8mb4;

grant all on ApolloConfigDB.* to apollo@'%' identified by 'apollo1234';
grant all on ApolloPortalDB.* to apollo@'%' identified by 'apollo1234';

git clone https://github.com/ctripcorp/apollo.git
cd apollo && git checkout v1.8.2 && cd scripts/sql/

mysql -h192.168.0.11 -uapollo -papollo1234 ApolloPortalDB < apolloportaldb.sql
mysql -h192.168.0.11 -uapollo -papollo1234 ApolloConfigDB < apolloconfigdb.sql

# 如果不是全新部署的Apollo配置中心，比如已经使用了一段时间，这时在Apollo配置中心已经创建了不少项目以及namespace等，那么在新环境中的ApolloConfigDB中需要从其它正常运行的环境中导入必要的项目数据。
# 主要涉及ApolloConfigDB的下面4张表，下面同时附上需要导入的数据查询语句：
# App
## 导入全部的App
## 如：insert into 新环境的ApolloConfigDB.App select * from 其它环境的ApolloConfigDB.App where IsDeleted = 0;
# AppNamespace
## 导入全部的AppNamespace
## 如：insert into 新环境的ApolloConfigDB.AppNamespace select * from 其它环境的ApolloConfigDB.AppNamespace where IsDeleted = 0;
# Cluster
## 导入默认的default集群
## 如：insert into 新环境的ApolloConfigDB.Cluster select * from 其它环境的ApolloConfigDB.Cluster where Name = 'default' and IsDeleted = 0;
# Namespace
## 导入默认的default集群中的namespace
## 如：insert into 新环境的ApolloConfigDB.Namespace select * from 其它环境的ApolloConfigDB.Namespace where ClusterName = 'default' and IsDeleted = 0;

# 调整服务端配置
## apollo.portal.envs 和 eureka.service.url
## select `Id`, `Key`, `Value`, `Comment` from `ApolloConfigDB`.`ServerConfig`;
## update `ApolloConfigDB`.`ServerConfig` set Value = 'http://apollo-service-apollo-configservice:8080/eureka/' where Id = 1;
```

### 1.2 创建命名空间

```bash
kubectl create namespace apollo
```

### 1.3 添加 Apollo Helm Chart 仓库

```bash
helm repo add apollo https://www.apolloconfig.com/charts
helm search repo apollo
```

### 1.4 部署 apollo-configservice 和 apollo-adminservice

```yaml
# vim apollo-service-values.yaml
configdb:
  host: 192.168.0.11
  userName: apollo
  password: apollo1234
  service:
    enabled: true
configService:
  replicaCount: 1
adminService:
  replicaCount: 1
#configService:
#  service:
#    type: NodePort
#adminService:
#  service:
#    type: NodePort
```

```bash
helm install apollo-service -n apollo apollo/apollo-service

# http://apollo-service-apollo-configservice.apollo:8080
# http://apollo-service-apollo-adminservice.apollo:8090
```

### 1.5 部署 apollo-portal

```yaml
# apollo-portal-values.yaml
portaldb:
  host: 192.168.0.11
  userName: apollo
  password: apollo1234
  service:
    service: true
config:
  envs: "dev"
  metaServers:
    dev: http://apollo-service-apollo-configservice:8080
replicaCount: 1
service:
  type: NodePort
```

```bash
helm install apollo-portal -n apollo apollo/apollo-portal
```

### 1.6 更新配置

```bash
helm upgrade apollo-service -n apollo -f apollo-service-values.yaml apollo/apollo-service
```

### 1.7 查看 apollo-portal nodePort

```bash
kubectl -n apollo get svc
```

## 2) 卸载 Apollo

### 2.1 卸载 apollo-configservice 和 apollo-adminservice

```bash
helm uninstall -n apollo apollo-service
```

### 2.2 卸载 apollo-portal

```bash
helm uninstall -n apollo apollo-portal
```
