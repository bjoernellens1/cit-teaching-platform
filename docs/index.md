# CIT Teaching Platform

A GitOps-managed Kubernetes deployment for the CIT teaching environment, featuring JupyterHub with Authentik identity management.

## Identity chain

**University Keycloak (SSO) → Authentik (CIT) → JupyterHub (CIT)**

- Users see "Login with University SSO".
- **Authentik** is the broker: it creates/updates users on first login, assigns groups based on Keycloak claims and/or the course enrollment flow, and provides OIDC to JupyterHub.
- JupyterHub uses Authentik OIDC for admin rights, course resource access, shared folders, and spawn profile / GPU access.

## Workloads

| Component | Description | Reference |
|-----------|-------------|-----------|
| **Authentik** | Server + Worker + Outpost + Postgres | `bundles/10-authentik/` |
| **JupyterHub** | Hub + Configurable HTTP Proxy + user pods | `bundles/20-jupyterhub/` |
| **Storage** | Per-user PVC homes + shared course volumes (RWX) | [Infrastructure Guide](INFRASTRUCTURE.md#storage) |

## Deployment (Fleet bundles)

Bundles apply in order, by directory naming:

```
00-crds              Custom Resource Definitions
01-sops-operator     SOPS operator for secret decryption
10-authentik         Authentik identity provider
20-jupyterhub        JupyterHub deployment
20-jupyterhub-postgres  JupyterHub's Postgres backend
20-jupyterhub-secrets   SOPS-encrypted JupyterHub secrets
30-storage           Storage configuration (per-user + shared RWX volumes)
40-policies          Network policies, quotas, security
```

## Access points

| Service | URL | Purpose |
|---------|-----|---------|
| **JupyterHub** | `jhub.dshl.unileoben.ac.at` | Interactive notebooks |
| **Authentik** | `auth.dshl.unileoben.ac.at` | Identity management |

## Where to go next

- **Students/users** → [User Guide](USER_GUIDE.md)
- **Course instructors / platform admins** → [Admin Guide](ADMIN_GUIDE.md)
- **Developers/contributors** → [Developer Guide](DEVELOPER_GUIDE.md)
- **Infrastructure team** → [Infrastructure Guide](INFRASTRUCTURE.md)
- **Something broken?** → [Troubleshooting](TROUBLESHOOTING.md)
- **Security architecture & compliance** → [Security Guide](SECURITY.md)
- **First-time secret setup** → [SOPS Bootstrap Guide](BOOTSTRAP-SOPS.md)

Security is defense-in-depth: SOPS-encrypted secrets (age keys), University SSO via Authentik (OIDC/SAML), NetworkPolicies and firewall rules, Pod Security Standards with non-root containers, encryption at rest and in transit, and audit logging. See the [Security Guide](SECURITY.md) for the full picture.
