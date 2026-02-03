# CIT Teaching Platform - Developer Guide

This guide is for developers who need to understand, modify, extend, or contribute to the CIT Teaching Platform codebase.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Development Environment Setup](#development-environment-setup)
- [Repository Structure](#repository-structure)
- [GitOps Workflow](#gitops-workflow)
- [Component Deep Dives](#component-deep-dives)
- [Customization Guide](#customization-guide)
- [Testing](#testing)
- [Deployment Pipeline](#deployment-pipeline)
- [Contributing](#contributing)
- [Common Development Tasks](#common-development-tasks)

---

## Overview

The CIT Teaching Platform is a GitOps-managed Kubernetes deployment that provides:

- **Identity Management**: Authentik as SSO broker between University Keycloak and applications
- **Interactive Computing**: JupyterHub with customizable compute profiles
- **Storage Management**: Per-user persistent homes and shared course volumes
- **Security**: Network policies, resource quotas, SOPS-encrypted secrets

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **GitOps** | Fleet (Rancher) | Continuous deployment from Git |
| **Identity** | Authentik | SSO broker, user/group management |
| **Notebooks** | JupyterHub (Z2JH) | Interactive computing platform |
| **Database** | PostgreSQL | Authentik data persistence |
| **Secrets** | SOPS + age | Encrypted secrets in Git |
| **Certificates** | cert-manager | TLS certificate management |
| **Orchestration** | Kubernetes | Container orchestration |

### Design Principles

1. **Everything as Code**: All configuration in Git, no manual changes
2. **Declarative**: Describe desired state, let systems converge
3. **Secure by Default**: Secrets encrypted, least privilege, network isolation
4. **Reproducible**: Can deploy identical environment from Git alone
5. **Observable**: Comprehensive logging and monitoring

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                │
└────────────────┬───────────────────┬───────────────────────────┘
                 │                   │
                 ▼                   ▼
         ┌──────────────┐    ┌──────────────┐
         │   Authentik  │    │  JupyterHub  │
         │   Ingress    │    │   Ingress    │
         └──────┬───────┘    └──────┬───────┘
                │                   │
                ▼                   ▼
┌───────────────────────┐   ┌───────────────────────┐
│   cit-auth namespace  │   │  cit-jhub namespace   │
│  ┌─────────────────┐  │   │  ┌─────────────────┐  │
│  │ Authentik       │  │   │  │ JupyterHub Hub  │  │
│  │ - Server (2x)   │  │   │  │                 │  │
│  │ - Worker (2x)   │  │   │  └─────────────────┘  │
│  └─────────────────┘  │   │  ┌─────────────────┐  │
│  ┌─────────────────┐  │   │  │ User Pods       │  │
│  │ PostgreSQL      │  │   │  │ - jupyter-user1 │  │
│  └─────────────────┘  │   │  │ - jupyter-user2 │  │
└───────────────────────┘   │  │ - ...           │  │
                             │  └─────────────────┘  │
                             └───────────────────────┘
                                      │
                                      ▼
                             ┌───────────────────────┐
                             │  Persistent Storage   │
                             │  - User PVCs          │
                             │  - Shared Course PVCs │
                             └───────────────────────┘
```

### Authentication Flow

```
┌─────────┐         ┌─────────┐         ┌─────────┐         ┌─────────┐
│  User   │────1───▶│ JupyterH│────2───▶│Authentik│────3───▶│   Uni   │
│ Browser │         │   Hub   │         │         │         │Keycloak │
└─────────┘         └─────────┘         └─────────┘         └─────────┘
     ▲                                        │                    │
     │                                        └────────4───────────┘
     │                                        │
     └────────────────────7───────────────────┘
          
1. User visits JupyterHub, clicks Login
2. JupyterHub redirects to Authentik (OIDC)
3. Authentik redirects to University Keycloak (SAML/OIDC)
4. User authenticates with university credentials
5. Keycloak returns to Authentik with user claims
6. Authentik processes enrollment flow (if needed)
7. Authentik returns to JupyterHub with OIDC token
8. JupyterHub spawns user pod with group-based permissions
```

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                     │
│                                                             │
│  ┌──────────────┐                                           │
│  │   Ingress    │  ← Cluster Ingress (nginx/traefik)      │
│  └──────┬───────┘                                           │
│         │                                                   │
│  ┌──────▼─────────────────────────────────────────────┐    │
│  │              Network Policies                      │    │
│  │  - Deny all ingress by default                     │    │
│  │  - Allow ingress from ingress controller           │    │
│  │  - Allow namespace-internal communication          │    │
│  │  - Deny cross-namespace (except DNS, metrics)      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │  cit-auth    │        │  cit-jhub    │                  │
│  │  namespace   │        │  namespace   │                  │
│  └──────────────┘        └──────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Development Environment Setup

### Prerequisites

Install the following tools:

```bash
# Kubernetes CLI
brew install kubectl

# Fleet CLI (optional, for local testing)
brew install fleet

# SOPS for secret management
brew install sops

# Age for encryption
brew install age

# Git
brew install git

# A Kubernetes cluster (one of):
# - k3d (local): brew install k3d
# - kind (local): brew install kind
# - Rancher Desktop
# - Access to production cluster
```

### Local Development Cluster

For testing changes locally before deploying to production:

```bash
# Create local k3d cluster
k3d cluster create cit-dev \
  --agents 2 \
  --port "8443:443@loadbalancer"

# Install Fleet
helm repo add fleet https://rancher.github.io/fleet-helm-charts/
helm install fleet-crd fleet/fleet-crd --namespace cattle-fleet-system --create-namespace
helm install fleet fleet/fleet --namespace cattle-fleet-system

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create SOPS operator age key
kubectl create namespace sops-system
kubectl create secret generic sops-age-key \
  -n sops-system \
  --from-file=age.agekey=./age.key
```

### Clone Repository

```bash
git clone https://github.com/bjoernellens1/cit-teaching-platform.git
cd cit-teaching-platform
```

### Configure SOPS

```bash
# Your age key for encryption/decryption
export SOPS_AGE_KEY_FILE=/path/to/age.key

# Verify you can decrypt secrets
sops -d bundles/10-authentik/authentik-sopssecret.yaml
```

---

## Repository Structure

```
cit-teaching-platform/
│
├── README.md                    # Main repository documentation
├── AGENTS.md                    # AI agent instructions
├── fleet.yaml                   # Root Fleet configuration
├── .sops.yaml                   # SOPS encryption rules
├── .gitignore                   # Git ignore patterns
│
├── docs/                        # Documentation
│   ├── USER_GUIDE.md           # End-user documentation
│   ├── ADMIN_GUIDE.md          # Administrator documentation
│   ├── DEVELOPER_GUIDE.md      # This file
│   ├── INFRASTRUCTURE.md       # Infrastructure documentation
│   ├── TROUBLESHOOTING.md      # Troubleshooting guide
│   ├── SECURITY.md             # Security documentation
│   └── BOOTSTRAP-SOPS.md       # SOPS setup guide
│
└── bundles/                     # Fleet bundles (deployment units)
    │
    ├── 00-crds/                # Custom Resource Definitions
    │   ├── fleet.yaml          # Bundle configuration
    │   └── cert-manager/       # cert-manager CRDs
    │
    ├── 01-sops-operator/       # SOPS operator for secret decryption
    │   ├── fleet.yaml
    │   ├── namespace.yaml
    │   └── values/
    │       └── values.yaml
    │
    ├── 10-authentik/           # Authentik identity provider
    │   ├── README.md           # Component-specific docs
    │   ├── fleet.yaml          # Bundle deployment config
    │   ├── namespace.yaml      # Namespace definition
    │   ├── authentik-sopssecret.yaml  # Encrypted secrets
    │   └── values/
    │       └── authentik-values.yaml  # Helm values
    │
    ├── 20-jupyterhub/          # JupyterHub deployment
    │   ├── README.md
    │   ├── fleet.yaml
    │   ├── namespace.yaml
    │   ├── shared-pvc.yaml
    │   ├── jupyterhub-sopssecret.yaml
    │   └── values/
    │       └── jupyterhub-values.yaml
    │
    ├── 30-storage/             # Storage configuration
    │   ├── fleet.yaml
    │   └── manifests/
    │       ├── rwx-volumes.yaml      # RWX PVCs for courses
    │       └── storageclasses.yaml   # Storage class configs
    │
    └── 40-policies/            # Security and resource policies
        ├── fleet.yaml
        └── manifests/
            ├── networkpolicies.yaml  # Network isolation
            ├── podsecurity.yaml      # Pod security standards
            └── resourcequotas.yaml   # Resource limits
```

### Bundle Naming Convention

Bundles are numbered to ensure deployment order:

- `00-*`: Prerequisites (CRDs)
- `01-*`: Operators and controllers
- `10-*`: Core infrastructure services
- `20-*`: Application services
- `30-*`: Supporting services
- `40-*`: Policies and constraints

Fleet deploys bundles in lexicographic order.

---

## GitOps Workflow

### How Fleet Works

1. **Watch Git**: Fleet watches this repository for changes
2. **Detect Changes**: On commit, Fleet detects modified bundles
3. **Plan Changes**: Fleet computes diff between Git and cluster state
4. **Apply Changes**: Fleet applies Kubernetes resources
5. **Monitor**: Fleet monitors resource health and reports status

### Making Changes

```bash
# 1. Create feature branch
git checkout -b feature/add-new-course

# 2. Make changes
vim bundles/30-storage/manifests/rwx-volumes.yaml

# 3. Commit
git add bundles/30-storage/manifests/rwx-volumes.yaml
git commit -m "Add storage for course-ml2026"

# 4. Push
git push origin feature/add-new-course

# 5. Create Pull Request
# Review changes on GitHub

# 6. Merge to main
# Fleet automatically deploys changes to cluster

# 7. Verify deployment
kubectl get gitrepo -n fleet-local cit-teaching-platform
kubectl get pvc -n cit-jhub course-ml2026-shared
```

### Testing Changes Locally

Before pushing to production:

```bash
# Apply to local cluster
kubectl apply -f bundles/30-storage/manifests/rwx-volumes.yaml

# Verify
kubectl get pvc -n cit-jhub

# If working, commit to Git
git add bundles/30-storage/manifests/rwx-volumes.yaml
git commit -m "Add storage for course-ml2026"
```

---

## Component Deep Dives

### Authentik Configuration

**Location**: `bundles/10-authentik/`

**Key Files**:
- `values/authentik-values.yaml`: Helm chart configuration
- `authentik-sopssecret.yaml`: Encrypted secrets (SOPS)
- `namespace.yaml`: Namespace and labels

**Helm Chart**: `goauthentik/authentik`  
**Documentation**: [https://goauthentik.io/docs/](https://goauthentik.io/docs/)

**Key Configuration Sections**:

```yaml
# In authentik-values.yaml

# Replicas for HA
server:
  replicas: 2
worker:
  replicas: 2

# PostgreSQL
postgresql:
  enabled: true
  persistence:
    enabled: true
    size: 20Gi

# Ingress
ingress:
  enabled: true
  hosts:
    - host: auth.dshl.unileoben.ac.at
  tls:
    - secretName: authentik-tls
      hosts:
        - auth.dshl.unileoben.ac.at
```

**Customization Examples**:

1. **Add custom branding**:
   ```yaml
   authentik:
     branding:
       logo: "/static/custom/logo.svg"
       title: "CIT Teaching Platform"
   ```

2. **Adjust worker count**:
   ```yaml
   worker:
     replicas: 4  # Increase for heavy flow processing
   ```

3. **Configure email**:
   ```yaml
   authentik:
     email:
       host: smtp.unileoben.ac.at
       port: 587
       use_tls: true
       from: noreply@dshl.unileoben.ac.at
   ```

### JupyterHub Configuration

**Location**: `bundles/20-jupyterhub/`

**Key Files**:
- `values/jupyterhub-values.yaml`: Massive Helm values file
- `jupyterhub-sopssecret.yaml`: Encrypted secrets
- `shared-pvc.yaml`: Global shared storage

**Helm Chart**: `jupyterhub/jupyterhub` (Zero to JupyterHub)  
**Documentation**: [https://z2jh.jupyter.org/](https://z2jh.jupyter.org/)

**Key Configuration Sections**:

1. **Authentication** (OIDC with Authentik):
   ```yaml
   hub:
     config:
       JupyterHub:
         authenticator_class: generic-oauth
       GenericOAuthenticator:
         client_id: jupyterhub
         authorize_url: https://auth.dshl.unileoben.ac.at/application/o/authorize/
         token_url: https://auth.dshl.unileoben.ac.at/application/o/token/
         userdata_url: https://auth.dshl.unileoben.ac.at/application/o/userinfo/
         username_claim: preferred_username
   ```

2. **Compute Profiles** (defined in Python hook):
   ```python
   # In singleuser.extraFiles.profile_list_hook.py
   _original_profile_list = [
       {
           "display_name": "CPU Small",
           "slug": "cpu-small",
           "kubespawner_override": {
               "cpu_limit": 2,
               "mem_limit": "6G",
           }
       },
       # ... more profiles
   ]
   ```

3. **Storage Configuration**:
   ```yaml
   singleuser:
     storage:
       type: dynamic
       capacity: 10Gi
       dynamic:
         storageClass: longhorn
     extraVolumes:
       - name: shared
         persistentVolumeClaim:
           claimName: jupyterhub-shared
     extraVolumeMounts:
       - name: shared
         mountPath: /home/jovyan/shared
   ```

**Profile List Hook Deep Dive**:

The profile list is dynamically filtered based on user groups:

```python
# Extract from profile_list_hook.py

def dynamic_profile_list(spawner):
    # Get user's Authentik groups
    user_groups = spawner.user.data.get('auth_state', {}).get('oauth_user', {}).get('groups', [])
    
    # Define student-accessible profiles
    student_profiles = ["cpu-small", "gpu-small"]
    
    # Admins and powerusers get all profiles
    if "jhub-admins" in user_groups or "jhub-powerusers" in user_groups:
        return _original_profile_list
    
    # Students get limited profiles
    return [p for p in _original_profile_list if p["slug"] in student_profiles]

c.KubeSpawner.profile_list = dynamic_profile_list
```

To add custom logic:
```python
# Add course-specific GPU access
if "course-advanced-ml" in user_groups:
    allowed_profiles.extend(["gpu-large", "gpu-xlarge"])

# Add per-user overrides
if spawner.user.name == "special_researcher":
    return _original_profile_list  # Full access
```

### Storage Configuration

**Location**: `bundles/30-storage/`

**RWX Volumes** (`manifests/rwx-volumes.yaml`):
```yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: course-aml-shared
  namespace: cit-jhub
spec:
  accessModes:
    - ReadWriteMany  # Multiple pods can mount
  storageClassName: longhorn  # Or nfs-csi, cephfs, etc.
  resources:
    requests:
      storage: 50Gi
```

**Storage Classes** (`manifests/storageclasses.yaml`):
```yaml
# Define custom storage classes if needed
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/no-provisioner  # or driver name
parameters:
  type: ssd
volumeBindingMode: WaitForFirstConsumer
```

### Policies

**Location**: `bundles/40-policies/`

**Network Policies** (`manifests/networkpolicies.yaml`):
```yaml
# Example: Isolate JupyterHub namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: cit-jhub
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  # Deny all ingress by default
---
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
```

**Resource Quotas** (`manifests/resourcequotas.yaml`):
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: jupyterhub-quota
  namespace: cit-jhub
spec:
  hard:
    requests.cpu: "500"
    requests.memory: "2Ti"
    requests.nvidia.com/gpu: "32"
    persistentvolumeclaims: "500"
```

---

## Customization Guide

### Adding a New Compute Profile

1. **Edit JupyterHub values**:
   ```bash
   vim bundles/20-jupyterhub/values/jupyterhub-values.yaml
   ```

2. **Add profile definition**:
   ```python
   # In _original_profile_list
   {
       "display_name": "CPU Medium - Teaching",
       "slug": "cpu-medium-teaching",
       "description": "4 CPU, 16GB RAM - For teaching demos",
       "kubespawner_override": {
           "cpu_limit": 4,
           "cpu_guarantee": 1,
           "mem_limit": "16G",
           "mem_guarantee": "4G",
           "image": "jupyter/scipy-notebook:latest",
       }
   },
   ```

3. **Make available to students** (optional):
   ```python
   student_profiles = [
       "cpu-small",
       "cpu-medium-teaching",  # Add this
       "gpu-small"
   ]
   ```

4. **Commit and deploy**:
   ```bash
   git add bundles/20-jupyterhub/values/jupyterhub-values.yaml
   git commit -m "Add CPU medium teaching profile"
   git push
   ```

### Changing the JupyterHub Image

**Default Image Location** (in values file):
```yaml
singleuser:
  image:
    name: jupyter/scipy-notebook
    tag: "2023-06-13"
```

**Creating a Custom Image**:

1. **Create Dockerfile**:
   ```dockerfile
   # Dockerfile
   FROM jupyter/scipy-notebook:2023-06-13
   
   USER root
   RUN apt-get update && apt-get install -y \
       vim \
       htop \
       && rm -rf /var/lib/apt/lists/*
   
   USER ${NB_UID}
   
   # Install additional Python packages
   RUN pip install --no-cache-dir \
       scikit-learn==1.3.0 \
       tensorflow==2.13.0 \
       torch torchvision
   ```

2. **Build and push**:
   ```bash
   docker build -t registry.dshl.unileoben.ac.at/jupyter-cit:latest .
   docker push registry.dshl.unileoben.ac.at/jupyter-cit:latest
   ```

3. **Update values**:
   ```yaml
   singleuser:
     image:
       name: registry.dshl.unileoben.ac.at/jupyter-cit
       tag: "latest"
       pullPolicy: Always
   ```

### Adding a Custom Authentik Flow

1. **Design flow** in Authentik UI:
   - Navigate to **Flows & Stages**
   - Click **Create Flow**
   - Add stages (prompts, actions, policies)
   - Test flow

2. **Export flow**:
   ```bash
   # Use Authentik API to export flow as YAML
   kubectl exec -n cit-auth -it deploy/authentik-server -- \
     ak export_flow <flow-slug> > flow-export.yaml
   ```

3. **Store in repository** (optional):
   ```bash
   mkdir -p bundles/10-authentik/flows
   mv flow-export.yaml bundles/10-authentik/flows/course-enrollment.yaml
   ```

4. **Document flow logic** in README

---

## Testing

### Manual Testing

**Test Authentication Flow**:
1. Deploy changes to dev environment
2. Navigate to JupyterHub URL
3. Click Login
4. Complete SSO flow
5. Verify groups are populated
6. Verify profile list is correct
7. Spawn server and check mounts

**Test Profile Changes**:
```bash
# As admin, inspect spawned pod
kubectl get pod -n cit-jhub jupyter-testuser -o yaml

# Check resource requests/limits
kubectl get pod -n cit-jhub jupyter-testuser -o jsonpath='{.spec.containers[0].resources}'

# Check volumes
kubectl get pod -n cit-jhub jupyter-testuser -o jsonpath='{.spec.volumes}'
```

### Automated Testing

**Helm Lint**:
```bash
# Test Authentik chart
helm lint bundles/10-authentik --values bundles/10-authentik/values/authentik-values.yaml

# Test JupyterHub chart
helm lint jupyterhub/jupyterhub --values bundles/20-jupyterhub/values/jupyterhub-values.yaml
```

**Kubernetes Manifest Validation**:
```bash
# Validate YAML syntax
kubectl apply --dry-run=client -f bundles/30-storage/manifests/rwx-volumes.yaml

# Validate against cluster (server-side dry-run)
kubectl apply --dry-run=server -f bundles/30-storage/manifests/rwx-volumes.yaml
```

**Fleet Simulation**:
```bash
# Check Fleet will accept the bundle
fleet apply --dry-run --local bundles/10-authentik
```

---

## Deployment Pipeline

### CI/CD with Fleet

```
┌─────────────┐
│  Developer  │
└──────┬──────┘
       │ git push
       ▼
┌─────────────┐
│   GitHub    │
└──────┬──────┘
       │ webhook (optional)
       ▼
┌─────────────┐
│    Fleet    │
│  (in K8s)   │
└──────┬──────┘
       │ git pull (poll: 15s)
       ▼
┌─────────────┐
│  Apply to   │
│   Cluster   │
└─────────────┘
```

**Fleet Configuration** (`fleet.yaml`):
```yaml
# Per-bundle fleet.yaml
defaultNamespace: cit-jhub

helm:
  chart: jupyterhub
  repo: https://jupyterhub.github.io/helm-chart/
  releaseName: jupyterhub
  version: 3.0.0
  values:
    # Reference to values file
    valuesFiles:
      - values/jupyterhub-values.yaml

# Deployment order (depends on other bundles)
dependsOn:
  - selector:
      matchLabels:
        bundle: authentik

# Health checks
targetCustomizations:
  - name: production
    helm:
      waitForJobs: true
    values:
      replicas: 3
```

### Rollback Procedure

**Via Git**:
```bash
# Revert last commit
git revert HEAD
git push

# Fleet will automatically roll back

# Or reset to specific commit
git reset --hard <commit-hash>
git push --force
```

**Via kubectl** (emergency only):
```bash
# Manual rollback of deployment
kubectl rollout undo deployment/authentik-server -n cit-auth

# Check rollout status
kubectl rollout status deployment/authentik-server -n cit-auth
```

---

## Contributing

### Development Workflow

1. **Fork repository** (external contributors)
2. **Create feature branch**: `git checkout -b feature/my-feature`
3. **Make changes**
4. **Test locally**
5. **Commit with descriptive messages**
6. **Push and create Pull Request**
7. **Address review comments**
8. **Merge after approval**

### Code Review Checklist

**For Reviewers**:
- [ ] Changes are minimal and focused
- [ ] No hardcoded secrets (use SopsSecret)
- [ ] Documentation updated
- [ ] Tested in dev environment
- [ ] No breaking changes for existing users
- [ ] Resource limits are reasonable
- [ ] Network policies are not weakened

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

**Example**:
```
feat(jupyterhub): Add GPU medium profile

- Add gpu-medium profile with 32GB VRAM
- Available to powerusers and course-ml2026
- Tested with PyTorch workloads

Closes #123
```

---

## Common Development Tasks

### Update Authentik Version

```bash
# 1. Check current version
helm list -n cit-auth

# 2. Check available versions
helm search repo goauthentik/authentik --versions

# 3. Update in fleet.yaml
vim bundles/10-authentik/fleet.yaml
# Change version: X.X.X

# 4. Review changelog
curl https://goauthentik.io/docs/releases/XXXX/vX.X.X

# 5. Test in dev
# 6. Commit and push
git add bundles/10-authentik/fleet.yaml
git commit -m "chore(authentik): Update to version X.X.X"
git push
```

### Update JupyterHub Version

```bash
# 1. Check Z2JH compatibility matrix
# https://z2jh.jupyter.org/en/stable/administrator/upgrading.html

# 2. Update version in fleet.yaml
vim bundles/20-jupyterhub/fleet.yaml

# 3. Review breaking changes

# 4. Test in dev environment

# 5. Deploy to production via Git
```

### Add Custom Python Package to All Users

**Option 1: Update container image**:
```dockerfile
# In custom Dockerfile
RUN pip install --no-cache-dir my-package==1.2.3
```

**Option 2: Post-start hook**:
```yaml
# In jupyterhub-values.yaml
singleuser:
  lifecycleHooks:
    postStart:
      exec:
        command:
          - /bin/sh
          - -c
          - |
            pip install --user my-package==1.2.3
```

**Option 3: Shared pip cache**:
```yaml
# Mount shared pip cache for faster installs
singleuser:
  extraVolumes:
    - name: pip-cache
      persistentVolumeClaim:
        claimName: shared-pip-cache
  extraVolumeMounts:
    - name: pip-cache
      mountPath: /home/jovyan/.cache/pip
```

### Debug SOPS Decryption Issues

```bash
# Check SOPS operator logs
kubectl logs -n sops-system -l app.kubernetes.io/name=sops-secrets-operator

# Verify age key exists
kubectl get secret -n sops-system sops-age-key

# Test decryption manually
export SOPS_AGE_KEY_FILE=/path/to/age.key
sops -d bundles/10-authentik/authentik-sopssecret.yaml

# Check SopsSecret status
kubectl get sopssecret -n cit-auth authentik-secrets -o yaml

# Verify secret was created
kubectl get secret -n cit-auth authentik-secrets
```

### Monitor Fleet Deployment

```bash
# Watch GitRepo status
kubectl get gitrepo -n fleet-local cit-teaching-platform -w

# Check bundle status
kubectl get bundles -A

# View Fleet agent logs
kubectl logs -n cattle-fleet-system -l app=fleet-agent -f

# Check specific bundle deployment
kubectl get bundledeployment -A | grep jupyterhub
```

---

## API References

### Authentik API

**Documentation**: [https://goauthentik.io/developer-docs/api/](https://goauthentik.io/developer-docs/api/)

**Example: Get user groups**:
```bash
# Get API token from Authentik UI: Admin → Tokens

curl -H "Authorization: Bearer <token>" \
  https://auth.dshl.unileoben.ac.at/api/v3/core/users/<user-id>/
```

### JupyterHub API

**Documentation**: [https://jupyterhub.readthedocs.io/en/stable/reference/rest-api.html](https://jupyterhub.readthedocs.io/en/stable/reference/rest-api.html)

**Example: List users**:
```bash
# Get API token from JupyterHub admin UI

curl -H "Authorization: token <token>" \
  https://jhub.dshl.unileoben.ac.at/hub/api/users
```

---

## Additional Resources

- **Zero to JupyterHub**: [https://z2jh.jupyter.org/](https://z2jh.jupyter.org/)
- **Authentik Docs**: [https://goauthentik.io/docs/](https://goauthentik.io/docs/)
- **Fleet Docs**: [https://fleet.rancher.io/](https://fleet.rancher.io/)
- **SOPS**: [https://github.com/mozilla/sops](https://github.com/mozilla/sops)
- **Kubernetes Docs**: [https://kubernetes.io/docs/](https://kubernetes.io/docs/)

---

**Last Updated**: February 2026  
**Platform Version**: 1.0  
**Maintainer**: Platform Development Team
