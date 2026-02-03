# Authentik - Identity Provider

> **📚 For comprehensive documentation, see:**
> - **Users**: [User Guide](../../docs/USER_GUIDE.md)
> - **Admins**: [Admin Guide](../../docs/ADMIN_GUIDE.md)
> - **Developers**: [Developer Guide](../../docs/DEVELOPER_GUIDE.md) - [Authentik Configuration](../../docs/DEVELOPER_GUIDE.md#authentik-configuration)

Authentik is the identity management system for the CIT Teaching Platform. It serves as the central authentication broker between the University's SSO (Keycloak) and downstream applications like JupyterHub.

## Why Authentik?

- **Single Sign-On Bridge**: Connects University Keycloak SSO with teaching applications
- **Course Management**: Handles course enrollment flows and group membership
- **Flexible Authorization**: Maps user groups to application permissions (admin access, GPU profiles, shared storage)
- **Self-Service**: Users can join courses via enrollment flow without admin intervention

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Uni Keycloak   │────▶│    Authentik    │────▶│   JupyterHub    │
│   (SSO Source)  │     │  (CIT Broker)   │     │  (Application)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────┐
                        │  PostgreSQL │
                        └─────────────┘
```

**Components:**
- **Server** (2 replicas): Handles HTTP requests, login flows, admin UI
- **Worker** (2 replicas): Background tasks, flow processing, events
- **PostgreSQL**: User data, configuration, session storage

---

## Quick Reference

This document provides component-specific technical details. For complete workflows and guides:

- **User Login & Enrollment**: See [User Guide - First-Time Login](../../docs/USER_GUIDE.md#first-time-login)
- **Admin Operations**: See [Admin Guide - User Management](../../docs/ADMIN_GUIDE.md#user-management)
- **Troubleshooting**: See [Troubleshooting Guide - Authentication Issues](../../docs/TROUBLESHOOTING.md#authentication-issues)

### For Users

**Logging In:**
1. Navigate to any CIT application (e.g., JupyterHub)
2. Click **"Login with University SSO"**
3. Enter your university credentials
4. On first login, you may be prompted to enroll in a course

**Managing Your Account:**

Visit **[auth.dshl.unileoben.ac.at](https://auth.dshl.unileoben.ac.at)** to:
- View your profile information
- See your group memberships
- Manage linked accounts
- Review active sessions

---

## For Administrators

> **📖 See [Admin Guide](../../docs/ADMIN_GUIDE.md) for complete admin operations**

### Accessing the Admin Interface

1. Navigate to [auth.dshl.unileoben.ac.at/if/admin/](https://auth.dshl.unileoben.ac.at/if/admin/)
2. Login with an account that has admin privileges

### User Groups

| Group | Purpose |
|-------|---------|
| `jhub-admins` | Full admin access to JupyterHub, all profiles, shared storage |
| `jhub-powerusers` | Access to all compute profiles and shared storage |
| `jhub-students` | Basic access: cpu-small, gpu-small profiles only |
| `course-<id>` | Course-specific groups for enrollment tracking |

### Managing Users

**Add Admin:**
1. Navigate to **Directory → Groups → jhub-admins**
2. Click **Add existing user**
3. Search and select the user

**View User Details:**
1. Navigate to **Directory → Users**
2. Search for the user
3. View groups, sessions, and activity

### Managing Courses

**Create a New Course Group:**
1. Navigate to **Directory → Groups**
2. Click **Create**
3. Name: `course-<course-id>` (e.g., `course-aml`)
4. Save

**Update Course Enrollment Password:**
1. Navigate to **Flows → course-enrollment** (or similar)
2. Edit the password validation stage
3. Update the password mapping

### Rotating Secrets

Secrets are stored in `secrets/sops/authentik-secrets.enc.yaml` (SOPS encrypted):

```bash
# Decrypt
sops -d secrets/sops/authentik-secrets.enc.yaml > /tmp/secrets.yaml

# Edit
vim /tmp/secrets.yaml

# Re-encrypt
sops -e /tmp/secrets.yaml > secrets/sops/authentik-secrets.enc.yaml

# Clean up
rm /tmp/secrets.yaml
```

### Monitoring

**Check Server Logs:**
```bash
kubectl logs -n authentik -l app.kubernetes.io/component=server -f
```

**Check Worker Logs:**
```bash
kubectl logs -n authentik -l app.kubernetes.io/component=worker -f
```

**View Pod Status:**
```bash
kubectl get pods -n authentik
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login loops | Check server logs for OIDC errors, verify client secrets |
| Users not in groups | Check flow execution logs in Authentik admin |
| SSO redirect fails | Verify Keycloak client configuration and redirect URIs |
| Slow logins | Check PostgreSQL performance, worker queue |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `values/authentik-values.yaml` | Helm chart configuration |
| `secrets/sops/authentik-secrets.enc.yaml` | Encrypted secrets (SOPS) |
| `namespace.yaml` | Namespace definition |
| `fleet.yaml` | Fleet deployment configuration |

---

## Security Considerations

- **Rate Limiting**: Configure login rate limits in Authentik UI (recommended: 5 attempts/minute)
- **Session Duration**: 8 hours (aligned with lecture day)
- **Remember Me**: 7 days maximum
- **Brute-force Protection**: Automatic lockout after failed attempts
- **Network Policies**: Authentik namespace is isolated, only ingress allowed
