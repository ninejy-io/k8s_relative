# 七、cluster-addon

## cluster-addon

### 7.1 准备 coredns 资源配置清单

```yaml
# mkdir -p cluster-addon/coredns
# vim cluster-addon/coredns/coredns.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: coredns
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:coredns
rules:
- apiGroups:
  - ""
  resources:
  - endpoints
  - services
  - pods
  - namespaces
  verbs:
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - nodes
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  annotations:
    rbac.authorization.kubernetes.io/autoupdate: "true"
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:coredns
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:coredns
subjects:
- kind: ServiceAccount
  name: coredns
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        reload
        loadbalance
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coredns
  namespace: kube-system
  labels:
    k8s-app: kube-dns
    kubernetes.io/name: "CoreDNS"
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  selector:
    matchLabels:
      k8s-app: kube-dns
  template:
    metadata:
      labels:
        k8s-app: kube-dns
    spec:
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      priorityClassName: system-cluster-critical
      serviceAccountName: coredns
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                  - key: k8s-app
                    operator: In
                    values: ["kube-dns"]
              topologyKey: kubernetes.io/hostname
      tolerations:
        - key: "CriticalAddonsOnly"
          operator: "Exists"
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: coredns
        image: coredns/coredns:1.8.0
        imagePullPolicy: IfNotPresent
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 70Mi
        args: [ "-conf", "/etc/coredns/Corefile" ]
        volumeMounts:
        - name: config-volume
          mountPath: /etc/coredns
          readOnly: true
        ports:
        - containerPort: 53
          name: dns
          protocol: UDP
        - containerPort: 53
          name: dns-tcp
          protocol: TCP
        - containerPort: 9153
          name: metrics
          protocol: TCP
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 60
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: 8181
            scheme: HTTP
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            add:
            - NET_BIND_SERVICE
            drop:
            - all
          readOnlyRootFilesystem: true
      dnsPolicy: Default
      volumes:
        - name: config-volume
          configMap:
            name: coredns
            items:
            - key: Corefile
              path: Corefile
---
apiVersion: v1
kind: Service
metadata:
  name: kube-dns
  namespace: kube-system
  annotations:
    prometheus.io/port: "9153"
    prometheus.io/scrape: "true"
  labels:
    k8s-app: kube-dns
    kubernetes.io/cluster-service: "true"
    kubernetes.io/name: "CoreDNS"
spec:
  selector:
    k8s-app: kube-dns
  clusterIP: 10.68.0.10
  ports:
  - name: dns
    port: 53
    protocol: UDP
  - name: dns-tcp
    port: 53
    protocol: TCP
  - name: metrics
    port: 9153
    protocol: TCP
```

### 7.2 安装 coredns

```bash
kubectl apply -f cluster-addon/coredns/coredns.yaml
```

### 7.3 准备 node-local-dns 资源配置清单

```yaml
# vim cluster-addon/coredns/nodelocaldns-ipvs.yaml

# Copyright 2018 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

apiVersion: v1
kind: ServiceAccount
metadata:
  name: node-local-dns
  namespace: kube-system
  labels:
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
---
apiVersion: v1
kind: Service
metadata:
  name: kube-dns-upstream
  namespace: kube-system
  labels:
    k8s-app: kube-dns
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
    kubernetes.io/name: "KubeDNSUpstream"
spec:
  ports:
  - name: dns
    port: 53
    protocol: UDP
    targetPort: 53
  - name: dns-tcp
    port: 53
    protocol: TCP
    targetPort: 53
  selector:
    k8s-app: kube-dns
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: node-local-dns
  namespace: kube-system
  labels:
    addonmanager.kubernetes.io/mode: Reconcile
data:
  Corefile: |
    cluster.local:53 {
        errors
        cache {
                success 9984 30
                denial 9984 5
        }
        reload
        loop
        bind 169.254.20.10
        forward . 10.68.0.10 {
                force_tcp
        }
        prometheus :9253
        health 169.254.20.10:8080
        }
    in-addr.arpa:53 {
        errors
        cache 30
        reload
        loop
        bind 169.254.20.10
        forward . 10.68.0.10 {
                force_tcp
        }
        prometheus :9253
        }
    ip6.arpa:53 {
        errors
        cache 30
        reload
        loop
        bind 169.254.20.10
        forward . 10.68.0.10 {
                force_tcp
        }
        prometheus :9253
        }
    .:53 {
        errors
        cache 30
        reload
        loop
        bind 169.254.20.10
        forward . __PILLAR__UPSTREAM__SERVERS__
        prometheus :9253
        }
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-local-dns
  namespace: kube-system
  labels:
    k8s-app: node-local-dns
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
spec:
  updateStrategy:
    rollingUpdate:
      maxUnavailable: 10%
  selector:
    matchLabels:
      k8s-app: node-local-dns
  template:
    metadata:
      labels:
        k8s-app: node-local-dns
      annotations:
        prometheus.io/port: "9253"
        prometheus.io/scrape: "true"
    spec:
      priorityClassName: system-node-critical
      serviceAccountName: node-local-dns
      hostNetwork: true
      dnsPolicy: Default  # Don't use cluster DNS.
      tolerations:
      - key: "CriticalAddonsOnly"
        operator: "Exists"
      - effect: "NoExecute"
        operator: "Exists"
      - effect: "NoSchedule"
        operator: "Exists"
      containers:
      - name: node-cache
        #image: k8s.gcr.io/dns/k8s-dns-node-cache:1.16.0
        image: easzlab/k8s-dns-node-cache:1.17.0
        resources:
          requests:
            cpu: 25m
            memory: 5Mi
        args: [ "-localip", "169.254.20.10", "-conf", "/etc/Corefile", "-upstreamsvc", "kube-dns-upstream" ]
        securityContext:
          privileged: true
        ports:
        - containerPort: 53
          name: dns
          protocol: UDP
        - containerPort: 53
          name: dns-tcp
          protocol: TCP
        - containerPort: 9253
          name: metrics
          protocol: TCP
        livenessProbe:
          httpGet:
            host: 169.254.20.10
            path: /health
            port: 8080
          initialDelaySeconds: 60
          timeoutSeconds: 5
        volumeMounts:
        - mountPath: /run/xtables.lock
          name: xtables-lock
          readOnly: false
        - name: config-volume
          mountPath: /etc/coredns
        - name: kube-dns-config
          mountPath: /etc/kube-dns
      volumes:
      - name: xtables-lock
        hostPath:
          path: /run/xtables.lock
          type: FileOrCreate
      - name: kube-dns-config
        configMap:
          name: kube-dns
          optional: true
      - name: config-volume
        configMap:
          name: node-local-dns
          items:
            - key: Corefile
              path: Corefile.base
---
# A headless service is a service with a service IP but instead of load-balancing it will return the IPs of our associated Pods.
# We use this to expose metrics to Prometheus.
apiVersion: v1
kind: Service
metadata:
  annotations:
    prometheus.io/port: "9253"
    prometheus.io/scrape: "true"
  labels:
    k8s-app: node-local-dns
  name: node-local-dns
  namespace: kube-system
spec:
  clusterIP: None
  ports:
    - name: metrics
      port: 9253
      targetPort: 9253
  selector:
    k8s-app: node-local-dns
```

### 7.4 安装 node-local-dns

```bash
kubectl apply -f cluster-addon/coredns/nodelocaldns-ipvs.yaml
```

### 7.5 准备 metrics-server 资源配置清单

```yaml
# mkdir cluster-addon/metrics-server
# vim cluster-addon/metrics-server/components.yaml
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: system:aggregated-metrics-reader
  labels:
    rbac.authorization.k8s.io/aggregate-to-view: "true"
    rbac.authorization.k8s.io/aggregate-to-edit: "true"
    rbac.authorization.k8s.io/aggregate-to-admin: "true"
rules:
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: metrics-server:system:auth-delegator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:auth-delegator
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: metrics-server-auth-reader
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: extension-apiserver-authentication-reader
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: kube-system
---
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1beta1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1beta1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: metrics-server
  namespace: kube-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-server
  namespace: kube-system
  labels:
    k8s-app: metrics-server
spec:
  selector:
    matchLabels:
      k8s-app: metrics-server
  template:
    metadata:
      name: metrics-server
      labels:
        k8s-app: metrics-server
    spec:
      serviceAccountName: metrics-server
      volumes:
      # mount in tmp so we can safely use from-scratch images and/or read-only containers
      - name: tmp-dir
        emptyDir: {}
      containers:
      - name: metrics-server
        #image: k8s.gcr.io/metrics-server-amd64:v0.3.6
        image: mirrorgooglecontainers/metrics-server-amd64:v0.3.6
        imagePullPolicy: IfNotPresent
        args:
          - --cert-dir=/tmp
          - --secure-port=4443
          - --kubelet-insecure-tls
        ports:
        - name: main-port
          containerPort: 4443
          protocol: TCP
        securityContext:
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
        volumeMounts:
        - name: tmp-dir
          mountPath: /tmp
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: "amd64"
---
apiVersion: v1
kind: Service
metadata:
  name: metrics-server
  namespace: kube-system
  labels:
    kubernetes.io/name: "Metrics-server"
    kubernetes.io/cluster-service: "true"
spec:
  selector:
    k8s-app: metrics-server
  ports:
  - port: 443
    protocol: TCP
    targetPort: main-port
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: system:metrics-server
rules:
- apiGroups:
  - ""
  resources:
  - pods
  - nodes
  - nodes/stats
  - namespaces
  - configmaps
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: system:metrics-server
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:metrics-server
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: kube-system
```

### 7.6 安装 metrics-server

```bash
kubectl apply -f cluster-addon/metrics-server/components.yaml
```

### 7.7 准备 ingress helm values 文件

```yaml
# mkdir cluster-addon/ingress
# vim cluster-addon/ingress/traefik-values.yaml

# Configure the deployment
deployment:
  enabled: true
  # Can be either Deployment or DaemonSet
  kind: DaemonSet
  replicas: 1

# Activate Pilot integration
pilot:
  enabled: false
  token: ""

# Create an IngressRoute for the dashboard
ingressRoute:
  dashboard:
    enabled: true

# Configure providers
providers:
  kubernetesCRD:
    enabled: true
    namespaces: []
      # - "default"
  kubernetesIngress:
    enabled: true
    namespaces: []
      # - "default"
    # IP used for Kubernetes Ingress endpoints
    publishedService:
      enabled: false
      # Published Kubernetes Service to copy status from. Format: namespace/servicename
      # By default this Traefik service
      # pathOverride: ""

# Add volumes to the traefik pod. The volume name will be passed to tpl.
# This can be used to mount a cert pair or a configmap that holds a config.toml file.
# After the volume has been mounted, add the configs into traefik by using the `additionalArguments` list below, eg:
# additionalArguments:
#  - "--entryPoints.web.address=:80"
#  - "--entryPoints.websecure.address=:443"
volumes: []
# - name: public-cert
#   mountPath: "/certs"
#   type: secret
# - name: xxx 
#   mountPath: "/config"
#   type: configMap

# Additional volumeMounts to add to the Traefik container
additionalVolumeMounts: []
  # For instance when using a logshipper for access logs
  # - name: traefik-logs
  #   mountPath: /var/log/traefik

# https://docs.traefik.io/observability/logs/
logs:
  # Traefik logs concern everything that happens to Traefik itself (startup, configuration, events, shutdown, and so on).
  general:
    # By default, the logs use a text format (common), but you can
    # also ask for the json format in the format option
    # format: json
    # By default, the level is set to ERROR. Alternative logging levels are DEBUG, PANIC, FATAL, ERROR, WARN, and INFO.
    level: ERROR
  access:
    # To enable access logs
    enabled: false
    # By default, logs are written using the Common Log Format (CLF).
    # To write logs in JSON, use json in the format option.
    # If the given format is unsupported, the default (CLF) is used instead.
    # format: json
    # To write the logs in an asynchronous fashion, specify a bufferingSize option.
    # This option represents the number of log lines Traefik will keep in memory before writing
    # them to the selected output. In some cases, this option can greatly help performances.
    # bufferingSize: 100
    # Filtering https://docs.traefik.io/observability/access-logs/#filtering
    filters: {}
      # statuscodes: "200,300-302"
      # retryattempts: true
      # minduration: 10ms
    # Fields
    # https://docs.traefik.io/observability/access-logs/#limiting-the-fieldsincluding-headers
    fields:
      general:
        defaultmode: keep
        names: {}
          # Examples:
          # ClientUsername: drop
      headers:
        defaultmode: drop
        names: {}
          # Examples:
          # User-Agent: redact
          # Authorization: drop
          # Content-Type: keep

globalArguments:
  - "--global.checknewversion"

# Configure ports
ports:
  traefik:
    port: 9000
    expose: true
    exposedPort: 9000
  web:
    hostPort: 80
    # Port Redirections
    # Added in 2.2, you can make permanent redirects via entrypoints.
    # https://docs.traefik.io/routing/entrypoints/#redirection
    # redirectTo: websecure
  websecure:
    hostPort: 443
    # Set TLS at the entrypoint
    # https://doc.traefik.io/traefik/routing/entrypoints/#tls
    tls:
      enabled: false
      # this is the name of a TLSOption definition
      options: ""
      certResolver: ""
      domains: []
      # - main: example.com
      #   sans:
      #     - foo.example.com
      #     - bar.example.com

# Options for the main traefik service, where the entrypoints traffic comes from.
service:
  enabled: true
  type: ClusterIP

# If hostNetwork is true, runs traefik in the host network namespace
hostNetwork: false

rbac:
  enabled: true

resources: {}
  # requests:
  #   cpu: "100m"
  #   memory: "50Mi"
  # limits:
  #   cpu: "300m"
  #   memory: "150Mi"
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/role
          operator: In
          values:
          - node
nodeSelector: {}

# Set the container security context
# To run the container with ports below 1024 this will need to be adjust to run as root
securityContext:
  capabilities:
    drop: [ALL]
  readOnlyRootFilesystem: true
  runAsGroup: 65532
  runAsNonRoot: true
  runAsUser: 65532

podSecurityContext:
  fsGroup: 65532
readinessProbe:
  httpGet:
    path: /ping
    port: 9000
  failureThreshold: 1
  initialDelaySeconds: 10
  periodSeconds: 10
  successThreshold: 1
  timeoutSeconds: 2
livenessProbe:
  httpGet:
    path: /ping
    port: 9000
  failureThreshold: 3
  initialDelaySeconds: 10
  periodSeconds: 10
  successThreshold: 1
  timeoutSeconds: 2
```

### 7.8 安装 traefik

```bash
helm install -n kube-system traefik \
    -f cluster-addon/ingress/traefik-values.yaml \
    cluster-addon/ingress/files/traefik-9.12.3.tgz
```

### 7.9 准备 dashboard 资源配置清单

```yaml
# mkdir cluster-addon/dashboard
# vim cluster-addon/dashboard/kubernetes-dashboard.yaml

# Copyright 2017 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

---

apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system

---

kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
    kubernetes.io/cluster-service: "true"
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  ports:
    - port: 443
      targetPort: 8443
  selector:
    k8s-app: kubernetes-dashboard
  type: NodePort

---

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-certs
  namespace: kube-system
type: Opaque

---

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-csrf
  namespace: kube-system
type: Opaque
data:
  csrf: ""

---

apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-key-holder
  namespace: kube-system
type: Opaque

---

kind: ConfigMap
apiVersion: v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard-settings
  namespace: kube-system

---

kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
rules:
  # Allow Dashboard to get, update and delete Dashboard exclusive secrets.
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["kubernetes-dashboard-key-holder", "kubernetes-dashboard-certs", "kubernetes-dashboard-csrf"]
    verbs: ["get", "update", "delete"]
    # Allow Dashboard to get and update 'kubernetes-dashboard-settings' config map.
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["kubernetes-dashboard-settings"]
    verbs: ["get", "update"]
    # Allow Dashboard to get metrics.
  - apiGroups: [""]
    resources: ["services"]
    resourceNames: ["heapster", "dashboard-metrics-scraper"]
    verbs: ["proxy"]
  - apiGroups: [""]
    resources: ["services/proxy"]
    resourceNames: ["heapster", "http:heapster:", "https:heapster:", "dashboard-metrics-scraper", "http:dashboard-metrics-scraper"]
    verbs: ["get"]

---

kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
rules:
  # Allow Metrics Scraper to get metrics from the Metrics server
  - apiGroups: ["metrics.k8s.io"]
    resources: ["pods", "nodes"]
    verbs: ["get", "list", "watch"]

---

apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kubernetes-dashboard
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard
    namespace: kube-system

---

apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubernetes-dashboard
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubernetes-dashboard
subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard
    namespace: kube-system

---

kind: Deployment
apiVersion: apps/v1
metadata:
  labels:
    k8s-app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: kubernetes-dashboard
  template:
    metadata:
      labels:
        k8s-app: kubernetes-dashboard
    spec:
      containers:
        - name: kubernetes-dashboard
          image: kubernetesui/dashboard:v2.3.1
          ports:
            - containerPort: 8443
              protocol: TCP
          args:
            - --auto-generate-certificates
            - --namespace=kube-system
            # Uncomment the following line to manually specify Kubernetes API server Host
            # If not specified, Dashboard will attempt to auto discover the API server and connect
            # to it. Uncomment only if the default does not work.
            # - --apiserver-host=http://my-address:port
          volumeMounts:
            - name: kubernetes-dashboard-certs
              mountPath: /certs
              # Create on-disk volume to store exec logs
            - mountPath: /tmp
              name: tmp-volume
          livenessProbe:
            httpGet:
              scheme: HTTPS
              path: /
              port: 8443
            initialDelaySeconds: 30
            timeoutSeconds: 30
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsUser: 1001
            runAsGroup: 2001
      volumes:
        - name: kubernetes-dashboard-certs
          secret:
            secretName: kubernetes-dashboard-certs
        - name: tmp-volume
          emptyDir: {}
      serviceAccountName: kubernetes-dashboard
      # Comment the following tolerations if Dashboard must not be deployed on master
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule

---

kind: Service
apiVersion: v1
metadata:
  labels:
    k8s-app: dashboard-metrics-scraper
  name: dashboard-metrics-scraper
  namespace: kube-system
spec:
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    k8s-app: dashboard-metrics-scraper

---

kind: Deployment
apiVersion: apps/v1
metadata:
  labels:
    k8s-app: dashboard-metrics-scraper
  name: dashboard-metrics-scraper
  namespace: kube-system
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      k8s-app: dashboard-metrics-scraper
  template:
    metadata:
      labels:
        k8s-app: dashboard-metrics-scraper
      annotations:
        seccomp.security.alpha.kubernetes.io/pod: 'runtime/default'
    spec:
      containers:
        - name: dashboard-metrics-scraper
          image: kubernetesui/metrics-scraper:v1.0.6
          ports:
            - containerPort: 8000
              protocol: TCP
          livenessProbe:
            httpGet:
              scheme: HTTP
              path: /
              port: 8000
            initialDelaySeconds: 30
            timeoutSeconds: 30
          volumeMounts:
          - mountPath: /tmp
            name: tmp-volume
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsUser: 1001
            runAsGroup: 2001
      serviceAccountName: kubernetes-dashboard
      nodeSelector:
        "kubernetes.io/os": linux
      # Comment the following tolerations if Dashboard must not be deployed on master
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      volumes:
        - name: tmp-volume
          emptyDir: {}

---
# read only user
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dashboard-read-user
  namespace: kube-system

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: dashboard-read-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: dashboard-read-clusterrole
subjects:
- kind: ServiceAccount
  name: dashboard-read-user
  namespace: kube-system

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: dashboard-read-clusterrole
rules:
- apiGroups:
  - ""
  resources:
  - configmaps
  - endpoints
  - nodes
  - persistentvolumes
  - persistentvolumeclaims
  - persistentvolumeclaims/status
  - pods
  - replicationcontrollers
  - replicationcontrollers/scale
  - serviceaccounts
  - services
  - services/status
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - bindings
  - events
  - limitranges
  - namespaces/status
  - pods/log
  - pods/status
  - replicationcontrollers/status
  - resourcequotas
  - resourcequotas/status
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - namespaces
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - controllerrevisions
  - daemonsets
  - daemonsets/status
  - deployments
  - deployments/scale
  - deployments/status
  - replicasets
  - replicasets/scale
  - replicasets/status
  - statefulsets
  - statefulsets/scale
  - statefulsets/status
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - autoscaling
  resources:
  - horizontalpodautoscalers
  - horizontalpodautoscalers/status
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - batch
  resources:
  - cronjobs
  - cronjobs/status
  - jobs
  - jobs/status
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - extensions
  resources:
  - daemonsets
  - daemonsets/status
  - deployments
  - deployments/scale
  - deployments/status
  - ingresses
  - ingresses/status
  - replicasets
  - replicasets/scale
  - replicasets/status
  - replicationcontrollers/scale
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - policy
  resources:
  - poddisruptionbudgets
  - poddisruptionbudgets/status
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - networking.k8s.io
  resources:
  - ingresses
  - ingresses/status
  - networkpolicies
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - storage.k8s.io
  resources:
  - storageclasses
  - volumeattachments
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - rbac.authorization.k8s.io
  resources:
  - clusterrolebindings
  - clusterroles
  - roles
  - rolebindings
  verbs:
  - get
  - list
  - watch

---
# admin user
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kube-system

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kube-system
```

### 7.10 安装 dashboard

```bash
kubectl apply -f cluster-addon/dashboard/kubernetes-dashboard.yaml
```

### 7.11 准备部署 prometheus 需要的文件

- 准备命名空间和证书

```bash
# 创建命名空间
kubectl create namespace monitoring

# 准备 etcd-client 证书请求
# mkdir -p /root/certs/prometheus
# vim /root/certs/prometheus/etcd-client-csr.json
{
    "CN": "etcd-client",
    "hosts": [],
    "key": {
        "algo": "rsa",
        "size": 2048
    },
    "names": [
        {
        "C": "CN",
        "ST": "Shanghai",
        "L": "XS",
        "O": "k8s",
        "OU": "System"
        }
    ]
}

# 创建 etcd-client 证书和私钥
cfssl gencert \
    -ca=ca.pem \
    -ca-key=ca-key.pem \
    -config=ca-config.json \
    -profile=kubernetes etcd-client-csr.json | cfssljson -bare etcd-client

# 创建 etcd-client-cert
kubectl create secret generic -n monitoring etcd-client-cert \
    --from-file=etcd-ca=ca.pem \
    --from-file=etcd-client=etcd-client.pem \
    --from-file=etcd-client-key=etcd-client-key.pem
```

- 准备 helm prometheus values 文件

```yaml
# mkdir cluster-addon/prometheus
# vim cluster-addon/prometheus/prom-values.yaml

## Provide a k8s version to auto dashboard import script example: kubeTargetVersionOverride: 1.16.6
kubeTargetVersionOverride: "1.21.0"

## Configuration for alertmanager
alertmanager:
  enabled: true
  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: ['job']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 12h
      receiver: 'null'
      routes:
      - match:
          alertname: Watchdog
        receiver: 'null'
    receivers:
    - name: 'null'

  ## Configuration for Alertmanager service
  service:
    nodePort: 30902
    type: NodePort 

  alertmanagerSpec:
    image:
      repository: quay.io/prometheus/alertmanager
      tag: v0.21.0

    replicas: 1
    retention: 120h

    nodeSelector: {}

## Using default values from https://github.com/grafana/helm-charts/blob/main/charts/grafana/values.yaml
grafana:
  enabled: true
  defaultDashboardsEnabled: true
  adminPassword: Admin1234!

  service:
    nodePort: 30903
    type: NodePort 

## Component scraping the kube api server
kubeApiServer:
  enabled: true

## Component scraping the kubelet and kubelet-hosted cAdvisor
kubelet:
  enabled: true
  namespace: kube-system

## Component scraping the kube controller manager
kubeControllerManager:
  enabled: true
  endpoints:
  - 192.168.0.203
  - 192.168.0.204

## Component scraping coreDns. Use either this or kubeDns
coreDns:
  enabled: true

## Component scraping etcd
kubeEtcd:
  enabled: true
  endpoints:
  - 192.168.0.203
  - 192.168.0.204
  - 192.168.0.205

  ## Configure secure access to the etcd cluster by loading a secret into prometheus and
  ## specifying security configuration below. For example, with a secret named etcd-client-cert
  serviceMonitor:
    scheme: https
    insecureSkipVerify: true 
    serverName: localhost
    caFile: /etc/prometheus/secrets/etcd-client-cert/etcd-ca
    certFile: /etc/prometheus/secrets/etcd-client-cert/etcd-client
    keyFile: /etc/prometheus/secrets/etcd-client-cert/etcd-client-key


## Component scraping kube scheduler
kubeScheduler:
  enabled: true
  endpoints:
  - 192.168.0.203
  - 192.168.0.204

## Component scraping kube proxy
kubeProxy:
  enabled: true
  endpoints:
  - 192.168.0.203
  - 192.168.0.204
  - 192.168.0.205

## Manages Prometheus and Alertmanager components
prometheusOperator:
  enabled: true

  ## Namespaces to scope the interaction of the Prometheus Operator and the apiserver (allow list).
  ## This is mutually exclusive with denyNamespaces. Setting this to an empty object will disable the configuration
  namespaces: {}
    # releaseNamespace: true
    # additional:
    # - kube-system

  ## Namespaces not to scope the interaction of the Prometheus Operator (deny list).
  denyNamespaces: []

  ## Filter namespaces to look for prometheus-operator custom resources
  ##
  alertmanagerInstanceNamespaces: []
  prometheusInstanceNamespaces: []
  thanosRulerInstanceNamespaces: []

  service:
    nodePort: 30899
    nodePortTls: 30900
    type: NodePort 

  nodeSelector: {}

  ## Prometheus-operator image
  image:
    repository: quay.io/prometheus-operator/prometheus-operator
    tag: v0.44.0

  ## Configmap-reload image to use for reloading configmaps
  configmapReloadImage:
    repository: docker.io/jimmidyson/configmap-reload
    tag: v0.4.0

  ## Prometheus-config-reloader image to use for config and rule reloading
  prometheusConfigReloaderImage:
    repository: quay.io/prometheus-operator/prometheus-config-reloader
    tag: v0.44.0

## Deploy a Prometheus instance
prometheus:
  enabled: true

  ## Configuration for Prometheus service
  service:
    nodePort: 30901
    type: NodePort 

  ## Settings affecting prometheusSpec
  ## ref: https://github.com/prometheus-operator/prometheus-operator/blob/master/Documentation/api.md#prometheusspec
  prometheusSpec:
    ## APIServerConfig
    ## ref: https://github.com/prometheus-operator/prometheus-operator/blob/master/Documentation/api.md#apiserverconfig
    apiserverConfig: {}

    image:
      repository: quay.io/prometheus/prometheus
      tag: v2.22.1

    replicas: 1

    secrets:
    - etcd-client-cert

    storageSpec: {}
    ## Using PersistentVolumeClaim
    ##
    #  volumeClaimTemplate:
    #    spec:
    #      storageClassName: gluster
    #      accessModes: ["ReadWriteOnce"]
    #      resources:
    #        requests:
    #          storage: 50Gi
    #    selector: {}

    ## Using tmpfs volume
    ##
    #  emptyDir:
    #    medium: Memory
```

### 7.12 安装 prometheus

```bash
helm install -n monitoring prometheus \
    -f cluster-addon/prometheus/prom-values.yaml \
    cluster-addon/prometheus/files/kube-prometheus-stack-12.10.6.tgz
```

### 7.13 准备 kube-system 部署文件

```yaml
# mkdir -p cluster-addon/kube-system
# vim cluster-addon/kube-system/kube-system.yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: nfs-client-provisioner
  # replace with namespace where provisioner is deployed
  namespace: kube-system
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: nfs-client-provisioner-runner
rules:
  - apiGroups: [""]
    resources: ["persistentvolumes"]
    verbs: ["get", "list", "watch", "create", "delete"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch", "update"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["storageclasses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "update", "patch"]
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: run-nfs-client-provisioner
subjects:
  - kind: ServiceAccount
    name: nfs-client-provisioner
    # replace with namespace where provisioner is deployed
    namespace: kube-system
roleRef:
  kind: ClusterRole
  name: nfs-client-provisioner-runner
  apiGroup: rbac.authorization.k8s.io
---
kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: leader-locking-nfs-client-provisioner
  # replace with namespace where provisioner is deployed
  namespace: kube-system
rules:
  - apiGroups: [""]
    resources: ["endpoints"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: leader-locking-nfs-client-provisioner
  # replace with namespace where provisioner is deployed
  namespace: kube-system
subjects:
  - kind: ServiceAccount
    name: nfs-client-provisioner
    # replace with namespace where provisioner is deployed
    namespace: kube-system
roleRef:
  kind: Role
  name: leader-locking-nfs-client-provisioner
  apiGroup: rbac.authorization.k8s.io

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nfs-client-provisioner
  labels:
    app: nfs-client-provisioner
  # replace with namespace where provisioner is deployed
  namespace: kube-system
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: nfs-client-provisioner
  template:
    metadata:
      labels:
        app: nfs-client-provisioner
    spec:
      serviceAccountName: nfs-client-provisioner
      containers:
        - name: nfs-client-provisioner
          #image: gcr.io/k8s-staging-sig-storage/nfs-subdir-external-provisioner:v4.0.1
          image: easzlab/nfs-subdir-external-provisioner:v4.0.1
          volumeMounts:
            - name: nfs-client-root
              mountPath: /persistentvolumes
          env:
            - name: PROVISIONER_NAME
              value: k8s-sigs.io/nfs-subdir-external-provisioner
            - name: NFS_SERVER
              value: 192.168.0.10
            - name: NFS_PATH
              value: /data/nfs
      volumes:
        - name: nfs-client-root
          nfs:
            server: 192.168.0.10
            path: /data/nfs

---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: managed-nfs-storage
provisioner: k8s-sigs.io/nfs-subdir-external-provisioner
parameters:
  archiveOnDelete: "false"
```

### 7.14 kube-system

```bash
kubectl apply -f cluster-addon/kube-system/kube-system.yaml
```
