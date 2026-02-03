# CIT Teaching Platform

A GitOps-managed Kubernetes deployment for the CIT teaching environment featuring JupyterHub with Authentik identity management.

## 📚 Documentation

Comprehensive documentation for all user roles:

- **[User Guide](docs/USER_GUIDE.md)** - Getting started, using JupyterHub, storage, profiles
- **[Admin Guide](docs/ADMIN_GUIDE.md)** - Platform administration, course management, operations
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Architecture, development setup, customization
- **[Infrastructure Guide](docs/INFRASTRUCTURE.md)** - Deployment, networking, storage, HA, DR
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Security Guide](docs/SECURITY.md)** - Security architecture, compliance, incident response
- **[SOPS Bootstrap Guide](docs/BOOTSTRAP-SOPS.md)** - Initial secret setup

## Quick Links

| For... | Start Here |
|--------|-----------|
| 🎓 **Students/Users** | [User Guide](docs/USER_GUIDE.md) → [Getting Started](docs/USER_GUIDE.md#getting-started) |
| 👨‍🏫 **Course Instructors** | [Admin Guide](docs/ADMIN_GUIDE.md) → [Course Management](docs/ADMIN_GUIDE.md#course-management) |
| 🔧 **Platform Admins** | [Admin Guide](docs/ADMIN_GUIDE.md) → [Operations](docs/ADMIN_GUIDE.md#monitoring-and-maintenance) |
| 💻 **Developers** | [Developer Guide](docs/DEVELOPER_GUIDE.md) → [Development Setup](docs/DEVELOPER_GUIDE.md#development-environment-setup) |
| 🏗️ **Infrastructure Team** | [Infrastructure Guide](docs/INFRASTRUCTURE.md) → [Initial Deployment](docs/INFRASTRUCTURE.md#initial-deployment) |
| 🆘 **Need Help?** | [Troubleshooting Guide](docs/TROUBLESHOOTING.md) |

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

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **Authentik** | Server + Worker + Outpost + Postgres | [bundles/10-authentik/README.md](bundles/10-authentik/README.md) |
| **JupyterHub** | Hub + Configurable HTTP Proxy + User Pods | [bundles/20-jupyterhub/README.md](bundles/20-jupyterhub/README.md) |
| **Storage** | Per-user PVC homes + Shared course volumes (RWX) | [Infrastructure Guide](docs/INFRASTRUCTURE.md#storage) |

## Repository Structure

```
cit-teaching-platform/
├── README.md                          # This file
├── docs/                              # 📚 Comprehensive documentation
│   ├── USER_GUIDE.md                 # User documentation
│   ├── ADMIN_GUIDE.md                # Administrator documentation
│   ├── DEVELOPER_GUIDE.md            # Developer documentation
│   ├── INFRASTRUCTURE.md             # Infrastructure documentation
│   ├── TROUBLESHOOTING.md            # Troubleshooting guide
│   ├── SECURITY.md                   # Security guide
│   └── BOOTSTRAP-SOPS.md             # SOPS setup guide
├── bundles/                           # Fleet deployment bundles
│   ├── 00-crds/                      # Custom Resource Definitions
│   ├── 01-sops-operator/             # SOPS operator for secret decryption
│   ├── 10-authentik/                 # Authentik identity provider
│   ├── 20-jupyterhub/                # JupyterHub deployment
│   ├── 30-storage/                   # Storage configuration
│   └── 40-policies/                  # Network policies, quotas, security
└── fleet.yaml                         # Root Fleet configuration
```

## Access Points

| Service | URL | Purpose | Documentation |
|---------|-----|---------|---------------|
| **JupyterHub** | `jhub.dshl.unileoben.ac.at` | Interactive notebooks | [User Guide](docs/USER_GUIDE.md) |
| **Authentik** | `auth.dshl.unileoben.ac.at` | Identity management | [Admin Guide](docs/ADMIN_GUIDE.md#accessing-admin-interfaces) |

## Quick Start

### For Users

1. Navigate to [jhub.dshl.unileoben.ac.at](https://jhub.dshl.unileoben.ac.at)
2. Click **Login** → **Login with University SSO**
3. Complete course enrollment (first time only)
4. Select compute profile and start coding!

**Full guide**: [User Guide](docs/USER_GUIDE.md)

### For Administrators

**New platform deployment**:
1. Follow the [Infrastructure Guide](docs/INFRASTRUCTURE.md#initial-deployment)
2. Bootstrap SOPS: [SOPS Bootstrap Guide](docs/BOOTSTRAP-SOPS.md)
3. Configure secrets and deploy via GitOps

**Adding a course**:
1. Create Authentik group: `course-<id>`
2. Create shared storage PVC
3. Set course password in enrollment flow
4. See: [Admin Guide - Course Management](docs/ADMIN_GUIDE.md#course-management)

### For Developers

1. Clone repository
2. Set up local development environment: [Developer Guide](docs/DEVELOPER_GUIDE.md#development-environment-setup)
3. Make changes and test locally
4. Submit pull request

**Full guide**: [Developer Guide](docs/DEVELOPER_GUIDE.md)

## Common Operations

### For Administrators

**Add a course**:
```bash
# See full guide in Admin Guide
# 1. Create group in Authentik
# 2. Add PVC to bundles/30-storage/manifests/rwx-volumes.yaml
# 3. Set course password
# 4. Commit and push
```

**Monitor platform health**:
```bash
kubectl get pods -A | grep -v Running
kubectl top nodes
kubectl get pvc -n cit-jhub
```

**View logs**:
```bash
# Authentik
kubectl logs -n cit-auth -l app.kubernetes.io/component=server --tail=50

# JupyterHub
kubectl logs -n cit-jhub -l component=hub --tail=50
```

**Full operations guide**: [Admin Guide](docs/ADMIN_GUIDE.md)

### For Developers

**Test changes locally**:
```bash
# Apply manifest
kubectl apply -f bundles/30-storage/manifests/rwx-volumes.yaml

# Verify
kubectl get pvc -n cit-jhub

# Deploy via Git
git add bundles/30-storage/manifests/rwx-volumes.yaml
git commit -m "Add course storage"
git push
```

**Customize profiles**:
- Edit `bundles/20-jupyterhub/values/jupyterhub-values.yaml`
- Modify `_original_profile_list` in profile hook
- Test and deploy via Git

**Full development guide**: [Developer Guide](docs/DEVELOPER_GUIDE.md)

## Security

The platform implements defense-in-depth security:

- 🔐 **Secrets**: SOPS encryption with age keys
- 🔒 **Authentication**: University SSO via Authentik (OIDC/SAML)
- 🛡️ **Network**: NetworkPolicies, firewall rules
- 📦 **Containers**: Pod Security Standards, non-root containers
- 💾 **Data**: Encryption at rest and in transit (TLS)
- 📊 **Monitoring**: Audit logs, security alerts

**Full security documentation**: [Security Guide](docs/SECURITY.md)

## Support

| Issue Type | Contact |
|------------|---------|
| 🎓 **Course/Assignment Questions** | Your course instructor |
| 🔧 **Technical Issues** | [support@dshl.unileoben.ac.at](mailto:support@dshl.unileoben.ac.at) |
| 🚨 **Platform Outage** | [platform-admins@dshl.unileoben.ac.at](mailto:platform-admins@dshl.unileoben.ac.at) |
| 🐛 **Bug Reports** | [GitHub Issues](https://github.com/bjoernellens1/cit-teaching-platform/issues) |

**Self-service help**: [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

## Contributing

We welcome contributions! See the [Developer Guide](docs/DEVELOPER_GUIDE.md#contributing) for:

- Development workflow
- Code review process
- Commit message conventions
- Testing requirements

## License

Internal use only - CIT Teaching Platform  
Maintained by CIT Platform Team

---

**📖 Complete Documentation**: See [docs/](docs/) directory for comprehensive guides covering all aspects of the platform.
