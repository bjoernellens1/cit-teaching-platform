# AGENTS.md - CIT Teaching Platform

This document provides instructions for AI agents and automated systems interacting with this repository.

## Repository Overview

This is a GitOps repository for deploying the CIT Teaching Platform on Kubernetes using Fleet. The platform consists of:

- **Authentik**: Identity provider bridging University Keycloak SSO to JupyterHub
- **JupyterHub**: Interactive computing environment for courses
- **Storage**: Persistent volumes for user homes and shared course data
- **Policies**: Network policies, resource quotas, and pod security

## Directory Structure

```
bundles/
├── 00-crds/          # Custom Resource Definitions (cert-manager)
├── 10-authentik/     # Authentik identity provider
├── 20-jupyterhub/    # JupyterHub deployment (z2jh)
├── 30-storage/       # PVCs and storage classes
└── 40-policies/      # Network policies, quotas, pod security
```

## Key Files to Understand

### Configuration Files

| File | Purpose |
|------|---------|
| `bundles/10-authentik/values/authentik-values.yaml` | Authentik Helm values |
| `bundles/20-jupyterhub/values/jupyterhub-values.yaml` | JupyterHub Helm values |
| `bundles/30-storage/manifests/rwx-volumes.yaml` | Shared course volumes |
| `bundles/40-policies/manifests/networkpolicies.yaml` | Network isolation rules |

### Secrets (SOPS Encrypted)

| File | Purpose |
|------|---------|
| `bundles/10-authentik/secrets/sops/authentik-secrets.enc.yaml` | Authentik secrets |
| `bundles/10-authentik/secrets/sops/postgres-secrets.enc.yaml` | Database credentials |
| `bundles/20-jupyterhub/secrets/sops/jupyterhub-secrets.enc.yaml` | JupyterHub secrets |

## Common Tasks

### Adding a New Course

1. Add group to Authentik (manual in UI or via API)
2. Create PVC in `bundles/30-storage/manifests/rwx-volumes.yaml`:
   ```yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: course-<id>-shared
     namespace: cit-jhub
   spec:
     accessModes: ["ReadWriteMany"]
     storageClassName: nfs-csi
     resources:
       requests:
         storage: 50Gi
   ```
3. Update JupyterHub values if needed for course-specific profiles

### Modifying User Quotas

Edit `bundles/40-policies/manifests/resourcequotas.yaml`

### Updating JupyterHub Images

Modify `singleuser.image` in `bundles/20-jupyterhub/values/jupyterhub-values.yaml`

## Testing Changes

This repository is deployed via Fleet. To test:

1. Create a feature branch
2. Deploy to a test cluster first
3. Verify Authentik login flow
4. Verify JupyterHub spawning
5. Check course folder mounting

## Important Notes

- **Do not** commit unencrypted secrets
- **Always** use SOPS for secret management
- **Preserve** the bundle naming convention (##-name)
- **Test** authentication flows after changes to Authentik config
- **Coordinate** with Uni Keycloak admins for SSO changes

## Fleet Bundle Dependencies

Bundles are applied in order:
1. `00-crds` - CRDs must exist first
2. `10-authentik` - Auth before apps
3. `20-jupyterhub` - Depends on Authentik OIDC
4. `30-storage` - Can be parallel with 20
5. `40-policies` - Applied last

## Contact

For issues with this platform, contact the CIT infrastructure team.
