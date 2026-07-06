# CIT Teaching Platform - Infrastructure Guide

This guide covers the infrastructure requirements, deployment, and operations for the CIT Teaching Platform.

## Table of Contents

- [Overview](#overview)
- [Infrastructure Requirements](#infrastructure-requirements)
- [Cluster Architecture](#cluster-architecture)
- [Initial Deployment](#initial-deployment)
- [Networking](#networking)
- [Storage](#storage)
- [High Availability](#high-availability)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Monitoring and Observability](#monitoring-and-observability)
- [Capacity Planning](#capacity-planning)
- [Security](#security)
- [Upgrades and Maintenance](#upgrades-and-maintenance)

---

## Overview

The CIT Teaching Platform runs on Kubernetes and uses GitOps (Fleet) for declarative infrastructure management. This document describes the infrastructure layer: compute, storage, networking, and operational considerations.

### Infrastructure Stack

```
┌─────────────────────────────────────────────────────┐
│              Application Layer                       │
│   (Authentik, JupyterHub, User Pods)                │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│           Kubernetes Platform                        │
│   (Orchestration, Scheduling, Networking)           │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│          Infrastructure Layer                        │
│   (Compute, Storage, Network, Security)             │
└─────────────────────────────────────────────────────┘
```

### Design Goals

- **High Availability**: No single point of failure for critical services
- **Scalability**: Support 200+ concurrent users per lecture
- **Security**: Network isolation, encryption, least privilege
- **Observability**: Comprehensive monitoring and logging
- **Cost Efficiency**: Optimize resource utilization

---

## Infrastructure Requirements

### Minimum Requirements (Development)

For testing and development:

- **Kubernetes**: 1 master + 2 worker nodes
- **CPU**: 8 cores per node (24 total)
- **RAM**: 32 GB per node (96 GB total)
- **Storage**: 500 GB SSD + 2 TB HDD/NFS
- **Network**: 1 Gbps internal, 100 Mbps internet

### Production Requirements

For production deployment supporting ~200 concurrent users:

#### Compute Nodes

**Master Nodes** (3x for HA):
- **CPU**: 4 cores
- **RAM**: 16 GB
- **Storage**: 100 GB SSD
- **Purpose**: Kubernetes control plane

**Worker Nodes - Standard** (5x):
- **CPU**: 24 cores
- **RAM**: 128 GB
- **Storage**: 500 GB SSD local
- **Purpose**: JupyterHub user pods (CPU profiles)

**Worker Nodes - GPU** (2x):
- **CPU**: 48 cores
- **RAM**: 256 GB
- **GPU**: 2× NVIDIA A100 (40GB VRAM each)
- **Storage**: 1 TB NVMe SSD local
- **Purpose**: GPU-accelerated workloads

**Infrastructure Nodes** (2x):
- **CPU**: 8 cores
- **RAM**: 32 GB
- **Storage**: 200 GB SSD
- **Purpose**: Authentik, PostgreSQL, monitoring

#### Storage

**Block Storage** (for PVCs):
- **Capacity**: 10 TB minimum
- **Type**: SSD-backed distributed storage (Longhorn, Ceph, or cloud provider)
- **IOPS**: 5000+ sustained
- **Purpose**: User home directories

**Shared Storage** (for RWX volumes):
- **Capacity**: 5 TB minimum
- **Type**: NFS, CephFS, or equivalent
- **Performance**: 1000+ MB/s throughput
- **Purpose**: Course materials, shared folders

**Object Storage** (optional):
- **Capacity**: 50 TB
- **Type**: S3-compatible (MinIO, AWS S3, etc.)
- **Purpose**: Backups, archives, large datasets

#### Network

- **Internal**: 10 Gbps between nodes
- **Internet**: 1 Gbps symmetrical
- **Load Balancer**: For ingress (NodePort, MetalLB, or cloud LB)
- **VPN**: For admin access (optional but recommended)

#### External Dependencies

- **DNS**: Control over `*.dshl.unileoben.ac.at`
- **TLS Certificates**: Let's Encrypt or internal CA
- **SSO**: University Keycloak/SAML provider
- **SMTP**: Email server for notifications

### Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Kubernetes | 1.28+ | Container orchestration |
| Fleet | 0.9+ | GitOps continuous deployment |
| cert-manager | 1.13+ | TLS certificate management |
| SOPS | 3.8+ | Secret encryption |
| CNI Plugin | Calico/Cilium | Network policies |
| Storage Driver | Longhorn/Ceph | Dynamic PV provisioning |
| Ingress Controller | nginx/Traefik | HTTP(S) routing |

---

## Cluster Architecture

### Cluster Topology

```
┌────────────────────────────────────────────────────────────┐
│                    Load Balancer / Ingress                 │
│            (External IP: 193.170.xxx.xxx)                  │
└───────────────────────┬────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼─────┐ ┌──────▼─────┐
│   Master 1   │ │  Master 2  │ │  Master 3  │
│ (Control     │ │ (Control   │ │ (Control   │
│  Plane)      │ │  Plane)    │ │  Plane)    │
└──────────────┘ └────────────┘ └────────────┘
        │
        ├─────────────────┬─────────────────┬────────────
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│  Worker 1    │  │  Worker 2    │  │  Worker 3    │
│  (Standard)  │  │  (Standard)  │  │  (Standard)  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│  Worker 4    │  │  Worker 5    │  │  GPU Node 1  │
│  (Standard)  │  │  (Standard)  │  │  (2×A100)    │
└──────────────┘  └──────────────┘  └──────┬───────┘
        │                                   │
┌───────▼──────┐                    ┌───────▼──────┐
│  GPU Node 2  │                    │  Infra 1     │
│  (2×A100)    │                    │  (Authentik) │
└──────────────┘                    └──────┬───────┘
                                            │
                                    ┌───────▼──────┐
                                    │  Infra 2     │
                                    │  (Authentik) │
                                    └──────────────┘
```

### Node Labels and Taints

**Node Labels** (for pod scheduling):
```yaml
# Standard workers
node-role.kubernetes.io/worker: "true"
workload-type: "standard"

# GPU workers
node-role.kubernetes.io/worker: "true"
workload-type: "gpu"
nvidia.com/gpu.present: "true"
gpu-type: "a100"

# Infrastructure nodes
node-role.kubernetes.io/infra: "true"
workload-type: "infrastructure"
```

**Node Taints** (to dedicate resources):
```bash
# GPU nodes - only GPU workloads
kubectl taint nodes gpu-node-1 nvidia.com/gpu=true:NoSchedule

# Infrastructure nodes - only infrastructure workloads
kubectl taint nodes infra-node-1 workload-type=infrastructure:NoSchedule
```

### Namespace Strategy

| Namespace | Purpose | Resource Quota |
|-----------|---------|----------------|
| `cit-auth` | Authentik, PostgreSQL | 8 CPU, 32 GB RAM |
| `cit-jhub` | JupyterHub hub, user pods | 480 CPU, 2 TB RAM, 32 GPU |
| `sops-system` | SOPS operator | 1 CPU, 2 GB RAM |
| `cert-manager` | Certificate management | 2 CPU, 2 GB RAM |
| `ingress-nginx` | Ingress controller | 4 CPU, 8 GB RAM |
| `monitoring` | Prometheus, Grafana | 8 CPU, 32 GB RAM |
| `fleet-local` | Fleet GitOps | 2 CPU, 4 GB RAM |

---

## Initial Deployment

### Prerequisites Checklist

- [ ] Kubernetes cluster installed and accessible
- [ ] kubectl configured with admin access
- [ ] Node labels and taints applied
- [ ] DNS records created (A records for ingress)
- [ ] TLS certificates available (or Let's Encrypt configured)
- [ ] Storage classes configured and tested
- [ ] SOPS age key generated and stored securely
- [ ] University SSO integration credentials obtained

### Step 1: Install Core Components

#### cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Verify
kubectl get pods -n cert-manager

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@dshl.unileoben.ac.at
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
EOF
```

#### Fleet

```bash
# Add Helm repo
helm repo add fleet https://rancher.github.io/fleet-helm-charts/
helm repo update

# Install Fleet CRDs
helm install fleet-crd fleet/fleet-crd \
  --namespace cattle-fleet-system \
  --create-namespace

# Install Fleet
helm install fleet fleet/fleet \
  --namespace cattle-fleet-system

# Verify
kubectl get pods -n cattle-fleet-system
```

#### Ingress Controller

```bash
# Install nginx ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Or for bare-metal with MetalLB
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/baremetal/deploy.yaml

# Verify
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

#### Storage Provisioner (Longhorn example)

```bash
# Install Longhorn
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml

# Verify
kubectl get pods -n longhorn-system

# Set as default storage class
kubectl patch storageclass longhorn -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# Verify
kubectl get storageclass
```

### Step 2: Bootstrap SOPS

```bash
# Generate age key (if not already done)
age-keygen -o age.key
# Save the public key from output

# Create .sops.yaml in repository root
cat > .sops.yaml <<EOF
creation_rules:
  - path_regex: .*sopssecret\.yaml$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF

# Create SOPS operator namespace
kubectl create namespace sops-system

# Create age key secret
kubectl create secret generic sops-age-key \
  -n sops-system \
  --from-file=age.agekey=age.key

# Store age.key securely (password manager, HSM)
# NEVER commit age.key to Git
```

### Step 3: Configure and Encrypt Secrets

```bash
# Edit secrets with real values
export SOPS_AGE_KEY_FILE=./age.key

# Authentik secrets
sops bundles/10-authentik/authentik-sopssecret.yaml
# Fill in:
# - AUTHENTIK_SECRET_KEY (openssl rand -hex 32)
# - AUTHENTIK_POSTGRESQL_PASSWORD
# - University SSO client secret

# JupyterHub secrets
sops bundles/20-jupyterhub/jupyterhub-sopssecret.yaml
# Fill in:
# - JupyterHub cookie secret (openssl rand -hex 32)
# - Authentik OIDC client secret
# - Proxy auth token (openssl rand -hex 32)

# Commit encrypted secrets
git add .sops.yaml bundles/*/authentik-sopssecret.yaml bundles/*/jupyterhub-sopssecret.yaml
git commit -m "Add encrypted secrets for production"
git push
```

### Step 4: Register GitRepo with Fleet

```bash
kubectl apply -f - <<EOF
apiVersion: fleet.cattle.io/v1alpha1
kind: GitRepo
metadata:
  name: cit-teaching-platform
  namespace: fleet-local
spec:
  repo: https://github.com/bjoernellens1/cit-teaching-platform
  branch: main
  paths:
    - bundles/
  targets:
    - name: local
      clusterSelector:
        matchLabels:
          management.cattle.io/cluster-display-name: local
EOF

# Watch deployment
kubectl get gitrepo -n fleet-local -w

# Check bundle status
kubectl get bundles -A

# Verify pods are running
kubectl get pods -n cit-auth
kubectl get pods -n cit-jhub
```

### Step 5: Configure DNS and Ingress

```bash
# Get ingress external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Create DNS A records:
# auth.dshl.unileoben.ac.at -> <EXTERNAL_IP>
# jhub.dshl.unileoben.ac.at -> <EXTERNAL_IP>

# Verify ingress
kubectl get ingress -A

# Test HTTPS
curl -I https://auth.dshl.unileoben.ac.at
curl -I https://jhub.dshl.unileoben.ac.at
```

### Step 6: Post-Deployment Configuration

**Configure Authentik**:
1. Login to Authentik admin: `https://auth.dshl.unileoben.ac.at/if/admin/`
2. Configure University SSO source (OIDC/SAML)
3. Create initial admin user group: `jhub-admins`
4. Configure course enrollment flows
5. Set course passwords
6. Test SSO flow

**Verify JupyterHub**:
1. Login to JupyterHub: `https://jhub.dshl.unileoben.ac.at`
2. Verify SSO authentication works
3. Add yourself to `jhub-admins` group in Authentik
4. Verify admin UI access
5. Spawn a test server
6. Verify storage mounts

---

## Networking

### Network Architecture

```
                     Internet
                        │
                        ▼
┌──────────────────────────────────────────────┐
│          Firewall / Cloud Security           │
│  - Allow 80/443 (HTTP/HTTPS)                │
│  - Allow 6443 (Kubernetes API, admin only)  │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│           Load Balancer / Ingress            │
│  - SSL Termination                           │
│  - Virtual Host Routing                      │
└────────────────┬─────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌───────────────┐  ┌───────────────┐
│   cit-auth    │  │   cit-jhub    │
│   namespace   │  │   namespace   │
└───────────────┘  └───────────────┘
```

### Ingress Configuration

**Authentik Ingress**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: authentik
  namespace: cit-auth
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - auth.dshl.unileoben.ac.at
      secretName: authentik-tls
  rules:
    - host: auth.dshl.unileoben.ac.at
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: authentik-server
                port:
                  number: 80
```

### Network Policies

**Default Deny Policy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: cit-jhub
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

**Allow Ingress from Controller**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-ingress
  namespace: cit-jhub
spec:
  podSelector:
    matchLabels:
      component: hub
  policyTypes:
    - Ingress
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
```

**Allow DNS**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: cit-jhub
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
      - namespaceSelector:
          matchLabels:
            name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

### Network Performance Tuning

**Enable BBR Congestion Control** (Linux kernel 4.9+):
```bash
# On all nodes
cat >> /etc/sysctl.conf <<EOF
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
EOF

sysctl -p
```

**Optimize Kubernetes Network**:
```yaml
# In CNI configuration (Calico example)
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  bpfEnabled: true  # Use eBPF for better performance
  bpfKubeProxyIptablesCleanupEnabled: false
```

---

## Storage

### Storage Classes

**Fast SSD (default)**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-ssd
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: driver.longhorn.io
parameters:
  numberOfReplicas: "3"
  staleReplicaTimeout: "2880"
  diskSelector: "ssd"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
```

**Shared NFS**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-csi
provisioner: nfs.csi.k8s.io
parameters:
  server: nfs-server.dshl.unileoben.ac.at
  share: /export/cit-shared
volumeBindingMode: Immediate
reclaimPolicy: Retain
allowVolumeExpansion: true
```

### PVC Design

**User Home Directories**:
- **Type**: RWO (ReadWriteOnce) - single pod
- **Size**: 10 GB default (expandable to 100 GB)
- **Storage Class**: longhorn-ssd (fast, replicated)
- **Backup**: Daily snapshots

**Course Shared Folders**:
- **Type**: RWX (ReadWriteMany) - multiple pods
- **Size**: 50-200 GB per course
- **Storage Class**: nfs-csi or cephfs
- **Backup**: Weekly full, daily incremental

### Storage Performance

**Benchmarking**:
```bash
# Test PVC performance
kubectl run fio-test --image=nixery.dev/shell/fio --rm -it -- bash

# In pod:
fio --name=randwrite --ioengine=libaio --iodepth=16 \
    --rw=randwrite --bs=4k --size=4G --numjobs=4 \
    --runtime=60 --time_based --group_reporting

fio --name=randread --ioengine=libaio --iodepth=16 \
    --rw=randread --bs=4k --size=4G --numjobs=4 \
    --runtime=60 --time_based --group_reporting
```

**Expected Performance**:
- **Sequential Write**: >500 MB/s per PVC
- **Sequential Read**: >1000 MB/s per PVC
- **Random Write IOPS**: >10000 IOPS
- **Random Read IOPS**: >20000 IOPS

---

## High Availability

### Control Plane HA

**etcd HA** (3+ nodes):
```yaml
# Ensure 3 master nodes
kubeadm init --control-plane-endpoint "k8s-api.internal:6443" \
  --upload-certs \
  --apiserver-advertise-address <IP>

# Join additional masters
kubeadm join k8s-api.internal:6443 --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane --certificate-key <cert-key>
```

### Application HA

**Authentik** (already configured):
```yaml
server:
  replicas: 2
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app.kubernetes.io/name: authentik
                app.kubernetes.io/component: server
            topologyKey: kubernetes.io/hostname
```

**JupyterHub Hub**:
```yaml
hub:
  replicas: 1  # Single replica with StatefulSet
  pdb:
    enabled: true
    minAvailable: 1
```

**Database HA** (PostgreSQL):
```yaml
# Option 1: Patroni (recommended for production)
# Deploy PostgreSQL with Patroni for automatic failover

# Option 2: PostgreSQL replication
postgresql:
  replication:
    enabled: true
    numSynchronousReplicas: 1
    synchronousCommit: "on"
```

### Pod Disruption Budgets

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: authentik-server
  namespace: cit-auth
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: authentik
      app.kubernetes.io/component: server
```

---

## Backup and Disaster Recovery

### Backup Strategy

| Component | Frequency | Retention | Tool |
|-----------|-----------|-----------|------|
| etcd | Hourly | 7 days | etcdctl, Velero |
| PostgreSQL | Daily | 30 days | pg_dump, Velero |
| User PVCs | Daily | 7 days | Longhorn snapshots, Velero |
| Course PVCs | Weekly | 90 days | NFS snapshots, Velero |
| Manifests | Every commit | Infinite | Git |
| Secrets | Every change | Infinite | SOPS + Git |

### etcd Backup

```bash
#!/bin/bash
# etcd-backup.sh

ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-$(date +%Y%m%d-%H%M%S).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify snapshot
ETCDCTL_API=3 etcdctl snapshot status /backup/etcd-latest.db

# Upload to object storage
aws s3 cp /backup/etcd-latest.db s3://cit-backups/etcd/
```

### PostgreSQL Backup

```bash
#!/bin/bash
# postgres-backup.sh

PG_POD=$(kubectl get pod -n cit-auth -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n cit-auth $PG_POD -- \
  pg_dump -U authentik authentik | \
  gzip > /backup/authentik-$(date +%Y%m%d).sql.gz

# Upload to object storage
aws s3 cp /backup/authentik-latest.sql.gz s3://cit-backups/postgres/
```

### Velero for Cluster Backup

```bash
# Install Velero
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket cit-backups \
  --backup-location-config region=eu-central-1 \
  --snapshot-location-config region=eu-central-1 \
  --secret-file ./credentials-velero

# Create backup schedule
velero schedule create cit-daily \
  --schedule="0 2 * * *" \
  --include-namespaces cit-auth,cit-jhub \
  --exclude-resources pods,replicasets

# Manual backup
velero backup create cit-manual-backup \
  --include-namespaces cit-auth,cit-jhub
```

### Disaster Recovery Procedure

**Complete Cluster Loss**:
1. Provision new Kubernetes cluster
2. Restore etcd from backup (if applicable)
3. Install core components (Fleet, cert-manager, etc.)
4. Restore Velero backup:
   ```bash
   velero restore create --from-backup cit-daily-20260203020000
   ```
5. Verify all pods are running
6. Test authentication and application access
7. Restore user data from storage snapshots if needed

**Data Corruption**:
1. Identify affected PVCs
2. Restore from Longhorn/storage provider snapshots:
   ```bash
   # Longhorn example
   kubectl apply -f - <<EOF
   apiVersion: longhorn.io/v1beta2
   kind: Volume
   metadata:
     name: pvc-restored
   spec:
     fromBackup: "backup://backup-name"
   EOF
   ```

---

## Monitoring and Observability

### Monitoring Stack

**Install Prometheus + Grafana**:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=<secure-password>
```

### Key Metrics to Monitor

**Cluster Level**:
- Node CPU, memory, disk usage
- Pod count and health
- Network throughput
- Storage IOPS and latency

**Application Level**:
- Authentik request rate, latency, errors
- JupyterHub active users, spawning time
- User pod resource usage
- Database connections, query performance

**Custom Metrics**:
```yaml
# ServiceMonitor for Authentik
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: authentik-metrics
  namespace: cit-auth
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: authentik
  endpoints:
    - port: metrics
      interval: 30s
```

### Grafana Dashboards

**Recommended Dashboards**:
- **Kubernetes Cluster Monitoring**: ID 12114
- **Node Exporter Full**: ID 1860
- **JupyterHub Dashboard**: ID 3802
- **PostgreSQL Database**: ID 9628

### Logging

**Install Loki Stack**:
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --set grafana.enabled=false \
  --set promtail.enabled=true
```

**Query Logs**:
```bash
# Via kubectl
kubectl logs -n cit-auth -l app.kubernetes.io/name=authentik --tail=100

# Via Grafana Loki (LogQL)
{namespace="cit-auth", app="authentik"} |= "error"
```

### Alerting

**Alertmanager Configuration**:
```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'platform-admins@dshl.unileoben.ac.at'
        from: 'alertmanager@dshl.unileoben.ac.at'
        smarthost: 'smtp.unileoben.ac.at:587'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10m
  repeat_interval: 12h
  receiver: 'email'
```

**Critical Alerts**:
- High pod restart rate
- Node down
- PVC nearly full (>80%)
- Certificate expiring (<7 days)
- High error rate in applications

---

## Capacity Planning

### Current Capacity (Example)

- **Total CPU**: 200 cores
- **Total RAM**: 1 TB
- **Total GPU**: 8× A100
- **User PVC Storage**: 10 TB
- **Shared Storage**: 5 TB

### Usage Projections

**Per-User Resource Usage**:
- **CPU Small**: 2 cores, 6 GB RAM
- **GPU Small**: 16 cores, 48 GB RAM, 10 GB VRAM via MPS sharing (see below)
- **Storage**: 10 GB (grows 1-2 GB per semester)

**Concurrent Users**:
- **Peak (lecture)**: 200 users
- **Average**: 50 users
- **Off-hours**: 10 users

**Resource Requirements for 200 Concurrent Users**:
- **CPU**: 400 cores (with 2:1 overcommit = 200 physical)
- **RAM**: 1.2 TB (with 1.2:1 overcommit = 1 TB physical)
- **GPU**: MIG partitioning is retired cluster-wide (A100 excludes NVIDIA
  DRA's DynamicMIG feature, and MIG mode toggles require a disruptive
  reboot on this passthrough hardware). GPU sharing is now done via NVIDIA
  MPS + KAI Scheduler's `gpu-memory` annotation and reservation-pod
  mechanism, on top of a plain (non-MIG) device-plugin mode that also
  supports real multi-GPU-per-pod exclusive requests (GPU Large/XLarge
  profiles). See cps-gpu-cluster's `docs/troubleshooting.md` for the full
  incident history behind this architecture.

### Scaling Plan

**Short-term (Next 6 months)**:
- Add 2× standard worker nodes (→ 7 total)
- Expand storage by 5 TB

**Medium-term (Next 2 years)**:
- Add 2× GPU nodes (→ 4 total)
- Expand storage to 30 TB
- Implement tiered storage (hot/warm/cold)

**Monitoring Thresholds**:
- **Scale up** when average utilization >70% for 1 week
- **Scale down** when average utilization <30% for 1 month

---

## Security

See [SECURITY.md](SECURITY.md) for comprehensive security documentation.

### Security Layers

1. **Network**: Firewall, NetworkPolicies, private networks
2. **Authentication**: SSO via Authentik, OIDC/SAML
3. **Authorization**: RBAC, group-based permissions
4. **Secrets**: SOPS encryption, least privilege access
5. **Workload**: Pod Security Standards, non-root containers
6. **Data**: Encryption at rest, TLS in transit

### Security Checklist

- [ ] NetworkPolicies applied to all namespaces
- [ ] Pod Security Standards enforced (restricted/baseline)
- [ ] RBAC configured with least privilege
- [ ] Secrets encrypted with SOPS
- [ ] TLS everywhere (ingress, internal services)
- [ ] Regular security updates applied
- [ ] Audit logging enabled
- [ ] Vulnerability scanning (Trivy, Snyk)
- [ ] Penetration testing annually

---

## Upgrades and Maintenance

### Maintenance Windows

**Schedule**:
- **Regular**: Every Sunday, 02:00-06:00 CET
- **Emergency**: As needed (with 2-hour notice if possible)

**Communication**:
- Notify users 1 week in advance for regular maintenance
- Post maintenance schedule to platform status page

### Kubernetes Upgrade

**Process**:
1. Review Kubernetes release notes
2. Test in dev environment
3. Backup cluster (etcd, Velero)
4. Upgrade control plane nodes (one at a time)
5. Upgrade worker nodes (rolling upgrade)
6. Verify all workloads healthy
7. Test user access end-to-end

```bash
# Drain node
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data

# Upgrade node (via package manager or kubeadm)
kubeadm upgrade node

# Uncordon node
kubectl uncordon <node>
```

### Component Upgrades

**Via GitOps** (Authentik, JupyterHub):
1. Update version in `bundles/*/fleet.yaml`
2. Review changelogs and breaking changes
3. Test in dev environment
4. Commit and push to main branch
5. Fleet automatically applies changes
6. Monitor rollout

**Manual** (Core infrastructure):
```bash
# Example: cert-manager upgrade
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml
```

---

## Additional Resources

- **Kubernetes Best Practices**: [https://kubernetes.io/docs/concepts/cluster-administration/](https://kubernetes.io/docs/concepts/cluster-administration/)
- **Fleet Documentation**: [https://fleet.rancher.io/](https://fleet.rancher.io/)
- **Longhorn Documentation**: [https://longhorn.io/docs/](https://longhorn.io/docs/)
- **Prometheus Operator**: [https://prometheus-operator.dev/](https://prometheus-operator.dev/)

---

**Last Updated**: February 2026  
**Platform Version**: 1.0  
**Maintainer**: Infrastructure Team
