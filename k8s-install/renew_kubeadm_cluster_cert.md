# Renew kubernetes certificate (The cluster installed by kubeadm)

## Error as below

```bash
crictl ps -a
crictl logs 89ca515cc7182 # kube-apiserver container

# W0517 03:40:44.955635       1 logging.go:59] [core] [Channel #4 SubChannel #6] grpc: addrConn.createTransport failed to connect to {
#   "Addr": "127.0.0.1:2379",
#   "ServerName": "127.0.0.1",
#   "Attributes": null,
#   "BalancerAttributes": null,
#   "Type": 0,
#   "Metadata": null
# }. Err: connection error: desc = "transport: authentication handshake failed: tls: failed to verify certificate: x509: certificate has expired or is not yet valid: current time 2024-05-17T03:40:44Z is after 2024-05-10T15:51:48Z"

# Check cert expire time
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -dates
kubeadm certs check-expiration
```

## Renew the certificate

```bash
kubeadm certs renew all

cp -i /etc/kubernetes/admin.conf $HOME/.kube/config

systemctl restart kubelet # restart kube-apiserver
```
