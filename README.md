# CIT Teaching Platform

A GitOps-managed Kubernetes deployment for the CIT teaching environment featuring JupyterHub with Authentik identity management.

## Architecture Overview

### Identity Chain

**Uni Keycloak (SSO) → Authentik (CIT) → JupyterHub (CIT)**

- Users see "Login with University SSO"
- **Authentik** is the broker:
  - Creates/updates users on first login
  - Assigns groups based on Keycloak claims and/or course enrollment flow
  - Provides OIDC to JupyterHub
- JupyterHub uses Authentik OIDC for:
  - Admin rights
  - Course resource access
  - Shared folders
  - Spawn profiles / GPU access

### Workloads

| Component | Description |
|-----------|-------------|
| authentik | Server + Worker + Outpost + Postgres + Redis |
| jupyterhub | Hub + Configurable HTTP Proxy + User Pods |
| storage | Per-user PVC homes + Shared course volumes (RWX) |

## Repository Structure

```
cit-teaching-platform/
  README.md                          # This file
  AGENTS.md                          # Agent instructions
  fleet.yaml                         # Root Fleet configuration
  bundles/
    00-crds/                         # CRDs (cert-manager)
    10-authentik/                    # Authentik deployment
    20-jupyterhub/                   # JupyterHub deployment
    30-storage/                      # Storage configuration
    40-policies/                     # Network policies & quotas
```

## Namespaces & Ingress

| Namespace | Ingress URL | Purpose |
|-----------|-------------|---------|
| cit-auth | `auth.cit.<your-domain>` | Authentik |
| cit-jhub | `jhub.cit.<your-domain>` | JupyterHub |

## Quick Start

### Prerequisites

- Kubernetes cluster with Fleet installed
- cert-manager (cluster-wide)
- SOPS with age/GPG configured for secret encryption
- Access to Uni Keycloak for SSO configuration

### Deployment

1. Clone this repository
2. Configure SOPS secrets in `bundles/*/secrets/sops/`
3. Update values files with your domain and credentials
4. Register this repository with Fleet

```bash
# Example: Apply Fleet GitRepo
kubectl apply -f - <<EOF
apiVersion: fleet.cattle.io/v1alpha1
kind: GitRepo
metadata:
  name: cit-teaching-platform
  namespace: fleet-local
spec:
  repo: https://github.com/your-org/cit-teaching-platform
  branch: main
  paths:
    - bundles/
EOF
```

## Configuration Files You'll Typically Modify

As a CIT admin, you'll mainly work with:

- `bundles/10-authentik/values/authentik-values.yaml` - Authentik configuration
- `bundles/20-jupyterhub/values/jupyterhub-values.yaml` - JupyterHub configuration
- `bundles/*/secrets/sops/*.enc.yaml` - Encrypted secrets

---

## Operations Guide

### Rotating Secrets

#### Uni Keycloak Client Secret
1. Generate new secret in Keycloak
2. Update `bundles/10-authentik/secrets/sops/authentik-secrets.enc.yaml`
3. Commit and push

#### Authentik Secrets
1. Update `bundles/10-authentik/secrets/sops/authentik-secrets.enc.yaml`
2. Commit and push

#### JupyterHub Cookie Secret
1. Generate new secret: `openssl rand -hex 32`
2. Update `bundles/20-jupyterhub/secrets/sops/jupyterhub-secrets.enc.yaml`
3. Commit and push

### Adding a New Course

1. **Create Authentik group**: In Authentik UI, create group `course-<id>`
2. **Add course password**: Update enrollment flow configuration
3. **Create RWX volume**: Add volume definition to `bundles/30-storage/manifests/rwx-volumes.yaml`
4. **Update JupyterHub mapping**: If custom profiles needed, update values

Example volume addition:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: course-<id>-shared
  namespace: cit-jhub
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-csi
  resources:
    requests:
      storage: 50Gi
```

### Managing Admins

Add or remove users from the `jhub-admins` group in Authentik UI.

### Troubleshooting

#### Check Authentik logs
```bash
kubectl logs -n cit-auth -l app.kubernetes.io/name=authentik-server -f
```

#### Check JupyterHub logs
```bash
kubectl logs -n cit-jhub -l component=hub -f
```

#### Check user pod status
```bash
kubectl get pods -n cit-jhub -l component=singleuser-server
```

---

## User Flow

### First-time Login

1. User visits `jhub.cit.<domain>`
2. Redirected to Authentik → "Login with University SSO"
3. Authenticated via Uni Keycloak
4. If not in any course group, prompted with enrollment flow:
   - Select course from dropdown
   - Enter course password
5. Added to course group, redirected to JupyterHub
6. User pod spawns with:
   - Personal home directory
   - Course-specific shared folders mounted

### Returning Users

1. SSO authentication (session-based)
2. Direct access to JupyterHub with existing group memberships

---

## Course Enrollment Flow (Authentik)

The enrollment flow is configured to:

1. **Prompt**: Course selection (dropdown)
2. **Prompt**: Password input
3. **Script stage**: Verify password matches course
4. **Group assignment**: Add user to `course-*` group
5. **Redirect**: Send user to JupyterHub

Groups are pre-created:
- `course-aml`
- `course-robotics`
- `course-datamodeling`
- `jhub-admins`

---

## Directory Structure on User Pods

Each user's pod has:

```
/home/jovyan/
├── work/                    # User's work directory
├── shared/                  # General shared space
└── courses/
    └── <course-id>/         # Per-course user directories
```

Shared course volumes are mounted at:
```
/srv/courses/<course-id>/    # RWX shared storage per course
```

---

## Scale Considerations

For a lecture with ~200 simultaneous logins:

| Component | Replicas | Notes |
|-----------|----------|-------|
| Authentik Server | 2-3 | Stateless, horizontal scaling |
| Authentik Worker | 2 | Handle flow/event processing |
| PostgreSQL | 1 | Sized adequately with backups |
| Redis | 1 | HA if available |
| JupyterHub | 1 | Single hub with autoscaling |

---

## Security

- Secrets managed with SOPS encryption
- Network policies isolate namespaces
- Resource quotas prevent resource exhaustion
- Pod security policies enforce container restrictions
- Rate limiting on Authentik for brute-force protection

---

## License

Internal use only - CIT Teaching Platform
