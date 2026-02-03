# CIT Teaching Platform - Security Guide

This document covers security architecture, best practices, and procedures for the CIT Teaching Platform.

## Table of Contents

- [Security Overview](#security-overview)
- [Security Architecture](#security-architecture)
- [Authentication and Authorization](#authentication-and-authorization)
- [Network Security](#network-security)
- [Secret Management](#secret-management)
- [Pod Security](#pod-security)
- [Data Security](#data-security)
- [Monitoring and Auditing](#monitoring-and-auditing)
- [Incident Response](#incident-response)
- [Compliance](#compliance)
- [Security Checklist](#security-checklist)

---

## Security Overview

### Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimum necessary access for users and services
3. **Zero Trust**: Verify every access request regardless of source
4. **Encryption Everywhere**: Data encrypted in transit and at rest
5. **Assume Breach**: Design to minimize impact if compromised

### Threat Model

**Protected Assets**:
- User credentials and authentication tokens
- Research data and course materials
- Platform secrets and API keys
- Compute and storage resources

**Threat Actors**:
- External attackers (internet)
- Malicious insiders (compromised accounts)
- Accidental misuse (user errors)

**Attack Vectors**:
- Network attacks (DDoS, MITM)
- Application vulnerabilities (XSS, CSRF, injection)
- Container escapes
- Credential theft
- Social engineering

---

## Security Architecture

### Layered Security Model

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Network Perimeter                              │
│ - Firewall                                              │
│ - DDoS Protection                                       │
│ - TLS Termination                                       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ Layer 2: Application Authentication                     │
│ - University SSO (SAML/OIDC)                           │
│ - Authentik (Identity Broker)                          │
│ - JupyterHub (OIDC Client)                             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ Layer 3: Authorization                                  │
│ - RBAC (Kubernetes)                                     │
│ - Group-based Permissions (Authentik)                   │
│ - Profile Access Control (JupyterHub)                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ Layer 4: Network Isolation                              │
│ - NetworkPolicies (namespace isolation)                 │
│ - Private Networks (internal services)                  │
│ - Service Mesh (optional: Istio/Linkerd)               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ Layer 5: Workload Security                              │
│ - Pod Security Standards                                │
│ - Non-root Containers                                   │
│ - Read-only Root Filesystems                            │
│ - Seccomp/AppArmor Profiles                            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ Layer 6: Data Protection                                │
│ - Encryption at Rest (storage)                          │
│ - Encryption in Transit (TLS)                           │
│ - Secret Management (SOPS)                              │
└─────────────────────────────────────────────────────────┘
```

---

## Authentication and Authorization

### SSO Authentication Chain

**University Keycloak (Primary Identity Provider)**:
- SAML 2.0 or OIDC
- Multi-factor authentication (MFA) enforced
- Session timeout: Configured by university IT

**Authentik (Identity Broker)**:
- OIDC provider to JupyterHub
- Session duration: 8 hours
- Remember-me: 7 days (optional)
- Brute-force protection: 5 attempts, 5-minute lockout

**JupyterHub (Application)**:
- OAuth2 client to Authentik
- Cookie-based sessions
- CSRF protection enabled
- Session timeout: 1 hour idle, 8 hours max

### Token Security

**Authentik Tokens**:
```yaml
# Token configuration
access_token_validity: 3600        # 1 hour
refresh_token_validity: 86400      # 24 hours
```

**JupyterHub API Tokens**:
- Admin tokens: Manually created, no expiration (rotate regularly)
- User tokens: Auto-generated, session-scoped
- Service tokens: For automation, stored in SOPS-encrypted secrets

### Authorization Model

**Kubernetes RBAC**:
```yaml
# Example: Limited namespace admin
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: cit-jhub-admins
  namespace: cit-jhub
subjects:
  - kind: Group
    name: cit-platform-admins
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: admin
  apiGroup: rbac.authorization.k8s.io
```

**Authentik Groups** (authorization claims):
- `jhub-admins`: Full platform administration
- `jhub-powerusers`: Advanced profiles and shared storage
- `jhub-students`: Limited profiles and resources
- `course-*`: Course-specific access

**JupyterHub Authorization**:
- Profiles filtered by group membership
- Shared storage mounted based on group
- Admin UI access restricted to `jhub-admins`

---

## Network Security

### Firewall Rules

**External (Internet-facing)**:
```
ALLOW   tcp/443   from 0.0.0.0/0       to INGRESS_IP    # HTTPS
ALLOW   tcp/80    from 0.0.0.0/0       to INGRESS_IP    # HTTP (redirect)
ALLOW   tcp/6443  from ADMIN_IPS       to K8S_API       # Kubernetes API (admin only)
DENY    *         from 0.0.0.0/0       to *             # Default deny
```

**Internal (Cluster)**:
- All inter-pod traffic allowed by default (within constraints of NetworkPolicies)
- DNS (UDP/53) allowed cluster-wide
- Kubernetes API allowed from all nodes

### Network Policies

**Default Deny All**:
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

**Allow Ingress from Ingress Controller**:
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

**Isolate User Pods**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-user-pods
  namespace: cit-jhub
spec:
  podSelector:
    matchLabels:
      component: singleuser-server
  policyTypes:
    - Egress
  egress:
    # Allow internet access
    - to:
      - ipBlock:
          cidr: 0.0.0.0/0
          except:
            - 10.0.0.0/8      # Block private IPs
            - 172.16.0.0/12
            - 192.168.0.0/16
    # Allow DNS
    - to:
      - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
```

### TLS/SSL Configuration

**Certificate Management**:
- **Provider**: Let's Encrypt (via cert-manager)
- **Renewal**: Automatic, 60 days before expiry
- **Algorithm**: RSA 2048 or ECDSA P-256

**TLS Configuration**:
```yaml
# Ingress TLS settings
metadata:
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.2 TLSv1.3"
    nginx.ingress.kubernetes.io/ssl-ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
```

**Internal TLS** (service mesh - optional):
- Mutual TLS (mTLS) between services
- Automatic certificate rotation
- Implemented via Istio or Linkerd

---

## Secret Management

### SOPS Encryption

**Age Encryption**:
```yaml
# .sops.yaml
creation_rules:
  - path_regex: .*sopssecret\.yaml$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Key Management**:
- Age private key stored securely (HSM, password manager)
- Never committed to Git
- Backup stored in separate secure location
- Key rotation annually or on compromise

**Encrypted Secret Format**:
```yaml
# Encrypted with SOPS
apiVersion: v1
kind: Secret
metadata:
  name: authentik-secrets
  namespace: cit-auth
type: Opaque
data:
  AUTHENTIK_SECRET_KEY: ENC[AES256_GCM,data:...,tag:...,type:str]
  # ... more encrypted fields
sops:
  kms: []
  gcp_kms: []
  azure_kv: []
  hc_vault: []
  age:
    - recipient: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      enc: |
        -----BEGIN AGE ENCRYPTED FILE-----
        ...
        -----END AGE ENCRYPTED FILE-----
  lastmodified: "2026-02-03T10:00:00Z"
  version: 3.8.1
```

### Secret Rotation Schedule

| Secret Type | Rotation Frequency | Priority |
|-------------|-------------------|----------|
| Age encryption key | Annually | Critical |
| Authentik secret key | Quarterly | High |
| Database passwords | Semi-annually | High |
| JupyterHub cookie secret | Quarterly | High |
| API tokens | Annually or on compromise | Medium |
| TLS certificates | Auto-renewed (Let's Encrypt) | High |

### Secret Access Control

**Kubernetes Secrets**:
- Namespace-scoped (not cluster-wide)
- RBAC: Only pods in same namespace can access
- No direct kubectl access by regular users

**SOPS Decryption**:
- Only SOPS operator has access to age private key
- Age key stored in Kubernetes Secret (protected by RBAC)
- Admins with age key can decrypt locally for editing

---

## Pod Security

### Pod Security Standards

**Namespace Configuration**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cit-jhub
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Enforcement Levels**:
- **Privileged**: Unrestricted (not used)
- **Baseline**: Minimally restrictive (infrastructure only)
- **Restricted**: Highly restrictive (user pods)

### Security Context

**JupyterHub User Pods**:
```yaml
securityContext:
  # Pod-level
  runAsNonRoot: true
  runAsUser: 1000        # jovyan user
  runAsGroup: 100        # users group
  fsGroup: 100
  
  # Container-level
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false  # Jupyter needs writable FS
  capabilities:
    drop:
      - ALL
  seccompProfile:
    type: RuntimeDefault
```

**Authentik Pods**:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  seccompProfile:
    type: RuntimeDefault
```

### Resource Limits

**Prevent Resource Exhaustion**:
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 2
    memory: 6Gi
```

**Namespace Quotas**:
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

### Image Security

**Image Scanning**:
```bash
# Scan images with Trivy
trivy image jupyter/scipy-notebook:latest
trivy image goauthentik/server:latest
```

**Allowed Registries**:
- `docker.io` (Docker Hub) - trusted images only
- `quay.io` (Red Hat Quay) - trusted images only
- `registry.dshl.unileoben.ac.at` (internal registry)

**Image Pull Policy**:
```yaml
image:
  pullPolicy: IfNotPresent  # or Always for latest tags
```

---

## Data Security

### Encryption at Rest

**Storage Encryption**:
- **User PVCs**: Encrypted by storage backend (Longhorn, Ceph)
- **Database**: PostgreSQL data directory encrypted
- **Secrets**: Encrypted in etcd (Kubernetes encryption provider)

**Kubernetes Secret Encryption**:
```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-secret>
      - identity: {}
```

### Encryption in Transit

**External Traffic**:
- All ingress: TLS 1.2+ (enforced by ingress controller)
- Certificate: Let's Encrypt with auto-renewal

**Internal Traffic**:
- Authentik → PostgreSQL: TLS (configured in connection string)
- JupyterHub → Authentik: HTTPS (OIDC endpoints)
- Optional: Service mesh for universal mTLS

### Data Access Controls

**File Permissions**:
- User home: `drwx------` (700) - owner only
- Shared folders: `drwxrwxr-x` (775) - group writable
- Course materials: `drwxr-xr-x` (755) - read-only for students

**Kubernetes PVC Access**:
- RWO (ReadWriteOnce): Single pod access
- RWX (ReadWriteMany): Multiple pod access (course shared folders)

### Data Retention

| Data Type | Retention Period | Deletion Method |
|-----------|------------------|-----------------|
| User home directories | 1 year after last login | Manual (admin approval) |
| Course materials | 5 years | Archival to object storage, then deletion |
| Audit logs | 1 year | Automated deletion |
| Backups | 30 days (daily), 12 months (monthly) | Automated deletion |

---

## Monitoring and Auditing

### Audit Logging

**Kubernetes Audit Logs**:
```yaml
# kube-apiserver flags
--audit-policy-file=/etc/kubernetes/audit-policy.yaml
--audit-log-path=/var/log/kubernetes/audit.log
--audit-log-maxage=30
--audit-log-maxbackup=10
--audit-log-maxsize=100
```

**Authentik Audit Events**:
- All authentication attempts (success/failure)
- User/group modifications
- Flow executions
- Admin actions

**JupyterHub Logs**:
- User logins/logouts
- Server spawns/stops
- Admin actions
- API calls

### Security Monitoring

**Metrics to Monitor**:
- Failed authentication attempts (rate)
- Unusual login patterns (time, location)
- High resource usage (potential cryptomining)
- Network traffic anomalies
- Container image vulnerabilities

**Alerts**:
```yaml
# Prometheus alert example
- alert: HighFailedLoginRate
  expr: rate(authentik_login_failed_total[5m]) > 10
  for: 5m
  annotations:
    summary: "High failed login rate detected"
    description: "More than 10 failed logins/minute in last 5 minutes"
```

### Intrusion Detection

**Host-based**:
- Falco for runtime security
- Auditd for system call monitoring

**Network-based**:
- NetworkPolicy violations logged
- Unusual egress traffic patterns

---

## Incident Response

### Incident Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| **Critical** | Service outage, data breach | Immediate (<1 hour) |
| **High** | Partial outage, suspected breach | <4 hours |
| **Medium** | Performance degradation, vulnerabilities | <24 hours |
| **Low** | Minor issues, potential risks | <1 week |

### Incident Response Plan

**1. Detection**:
- Automated alerts (monitoring system)
- User reports
- Security scans

**2. Assessment**:
- Determine scope and severity
- Identify affected systems and users
- Preserve evidence (logs, snapshots)

**3. Containment**:
- Isolate affected resources (NetworkPolicy)
- Disable compromised accounts
- Stop malicious processes

**4. Eradication**:
- Remove malware/backdoors
- Patch vulnerabilities
- Rotate compromised credentials

**5. Recovery**:
- Restore from clean backups
- Verify system integrity
- Gradual service restoration

**6. Post-Incident**:
- Root cause analysis
- Document lessons learned
- Update security controls
- User notification (if data breach)

### Security Incident Playbooks

**Compromised User Account**:
```bash
# 1. Disable account
# In Authentik UI: User → Uncheck "Is active"

# 2. Stop user's server
kubectl delete pod -n cit-jhub jupyter-<username>

# 3. Review logs
kubectl logs -n cit-jhub jupyter-<username> --previous > incident-logs.txt

# 4. Check for lateral movement
kubectl logs -n cit-jhub -l component=hub | grep <username>

# 5. Force password reset (via university IT)

# 6. Re-enable account after verification
```

**Container Escape Detected**:
```bash
# 1. Isolate node
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 2. Capture forensics
kubectl exec -it <pod> -- crictl inspect <container-id>
# Take node snapshot for analysis

# 3. Terminate all pods on node
kubectl delete pod --all -n cit-jhub --field-selector spec.nodeName=<node-name>

# 4. Rebuild node from trusted image

# 5. Uncordon when verified clean
kubectl uncordon <node-name>
```

---

## Compliance

### Data Protection Regulations

**GDPR Compliance**:
- **Data Minimization**: Collect only necessary user data
- **Right to Access**: Users can view their data via Authentik UI
- **Right to Deletion**: Admin procedure for data deletion
- **Data Portability**: Users can export their files via JupyterHub
- **Consent**: Users consent via university enrollment

### Security Standards

**ISO 27001 Alignment**:
- Asset management (inventory of services)
- Access control (RBAC, least privilege)
- Cryptography (TLS, SOPS)
- Operations security (change management, backups)
- Incident management (response plan)

### Audit Requirements

**Regular Audits**:
- **Security audit**: Quarterly
- **Access review**: Monthly (user/group memberships)
- **Vulnerability scan**: Weekly (automated)
- **Penetration test**: Annually (external)

---

## Security Checklist

### Deployment Checklist

- [ ] TLS certificates configured and valid
- [ ] SOPS secrets encrypted with age
- [ ] NetworkPolicies applied to all namespaces
- [ ] Pod Security Standards enforced
- [ ] Resource quotas configured
- [ ] RBAC configured with least privilege
- [ ] Non-root containers enforced
- [ ] Secrets not in plaintext in Git
- [ ] Firewall rules configured
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented and tested
- [ ] Incident response plan documented

### Operational Checklist

**Daily**:
- [ ] Review critical alerts
- [ ] Check for failed authentication attempts

**Weekly**:
- [ ] Review audit logs
- [ ] Scan images for vulnerabilities
- [ ] Check certificate expiry dates

**Monthly**:
- [ ] Review user access (remove inactive users)
- [ ] Review RBAC assignments
- [ ] Test backup restoration

**Quarterly**:
- [ ] Rotate non-automated secrets
- [ ] Security audit
- [ ] Update security documentation

**Annually**:
- [ ] Rotate age encryption key
- [ ] Penetration testing
- [ ] Security training for admins

---

## Security Resources

### Internal

- **Security Team**: security@dshl.unileoben.ac.at
- **Security Incident Hotline**: +43 XXX XXX XXX
- **Security Wiki**: https://wiki.dshl.unileoben.ac.at/security

### External

- **Kubernetes Security**: https://kubernetes.io/docs/concepts/security/
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CIS Benchmarks**: https://www.cisecurity.org/cis-benchmarks/
- **CVE Database**: https://cve.mitre.org/

---

**Last Updated**: February 2026  
**Platform Version**: 1.0  
**Security Classification**: Internal Use Only
