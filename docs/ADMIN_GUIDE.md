# CIT Teaching Platform - Admin Guide

This guide is for platform administrators responsible for managing the CIT Teaching Platform, including Authentik, JupyterHub, user access, and course management.

## Table of Contents

- [Overview](#overview)
- [Admin Responsibilities](#admin-responsibilities)
- [Accessing Admin Interfaces](#accessing-admin-interfaces)
- [User Management](#user-management)
- [Course Management](#course-management)
- [Resource Management](#resource-management)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Secret Management](#secret-management)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

---

## Overview

As a CIT Teaching Platform administrator, you manage:

- **Authentik**: User authentication, SSO, course enrollment flows
- **JupyterHub**: Interactive computing environment, profiles, resources
- **Storage**: User homes, shared volumes, course materials
- **Policies**: Network policies, resource quotas, security

### Architecture Quick Reference

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Uni Keycloak   │────▶│    Authentik    │────▶│   JupyterHub    │
│   (SSO Source)  │     │  (CIT Broker)   │     │  (Application)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                       │
                               ▼                       ▼
                         ┌─────────────┐         ┌─────────────┐
                         │  PostgreSQL │         │   Storage   │
                         └─────────────┘         │   (PVCs)    │
                                                 └─────────────┘
```

### Admin Access Requirements

- **Kubernetes**: Cluster admin or namespace admin access
- **Authentik Admin**: Member of Authentik superuser group
- **JupyterHub Admin**: Member of `jhub-admins` Authentik group
- **SOPS**: Access to age private key for secret decryption

---

## Admin Responsibilities

### Daily Operations

- Monitor system health and user activity
- Respond to user support requests
- Verify backup operations
- Check for failed pods or services

### Weekly Tasks

- Review resource usage and capacity
- Check for pending system updates
- Review authentication logs for anomalies
- Audit user group memberships

### Semester/Course Start

- Create course groups and enrollment flows
- Set course passwords
- Provision course shared storage
- Test enrollment process
- Verify compute profile assignments

### Semester/Course End

- Archive course data
- Clean up inactive user pods
- Review and update resource quotas
- Generate usage reports

---

## Accessing Admin Interfaces

### Authentik Admin UI

**URL**: [https://auth.dshl.unileoben.ac.at/if/admin/](https://auth.dshl.unileoben.ac.at/if/admin/)

**Login**: Use your admin account with University SSO

**Capabilities**:
- User and group management
- Flow and stage configuration
- SSO provider configuration
- Authentication audit logs

### JupyterHub Admin UI

**URL**: [https://jhub.dshl.unileoben.ac.at/hub/admin](https://jhub.dshl.unileoben.ac.at/hub/admin)

**Login**: Must be member of `jhub-admins` group in Authentik

**Capabilities**:
- View all active users and servers
- Start/stop user servers
- Access user servers (for debugging)
- View server spawn logs

### Kubernetes CLI Access

```bash
# Set context to CIT cluster
kubectl config use-context cit-teaching-cluster

# Verify access
kubectl get namespaces
kubectl get pods -A
```

**Primary Namespaces**:
- `cit-auth`: Authentik and PostgreSQL
- `cit-jhub`: JupyterHub hub and user pods
- `sops-system`: SOPS operator for secret decryption
- `cert-manager`: Certificate management (cluster-wide)

---

## User Management

### Understanding User Groups

| Group | Purpose | Permissions |
|-------|---------|-------------|
| `jhub-admins` | Platform administrators | Full JupyterHub admin, all profiles, shared storage access |
| `jhub-powerusers` | Research staff, TAs | All compute profiles, shared storage access |
| `jhub-students` | Regular students | Limited profiles (cpu-small, gpu-small) |
| `course-<id>` | Course enrollment | Course-specific resources and shared folders |

### Adding an Admin

**Via Authentik UI**:
1. Navigate to **Directory → Groups → jhub-admins**
2. Click **Add existing user**
3. Search for the user by username or email
4. Click **Add**

**Verify**:
```bash
# Check if user's pod will have admin access
kubectl logs -n cit-jhub -l component=hub --tail=50 | grep "Admin users"
```

### Adding a Power User

**Via Authentik UI**:
1. Navigate to **Directory → Groups → jhub-powerusers**
2. Click **Add existing user**
3. Search and select the user
4. Click **Add**

The user will see all compute profiles on next login.

### Viewing User Details

**Via Authentik UI**:
1. Navigate to **Directory → Users**
2. Search for the user
3. Click on username to view:
   - Group memberships
   - Recent authentication events
   - Active sessions
   - User attributes from SSO

**Via kubectl**:
```bash
# View active user pods
kubectl get pods -n cit-jhub -l component=singleuser-server

# View specific user's pod
kubectl get pod -n cit-jhub jupyter-<username> -o yaml

# Check user's PVC
kubectl get pvc -n cit-jhub claim-<username>
```

### Removing User Access

**Temporary Suspension** (user keeps their data):
1. In Authentik: **Directory → Users → [username]**
2. Uncheck **Is active**
3. Click **Update**

**Remove from Course**:
1. In Authentik: **Directory → Groups → course-<id>**
2. Find user in members list
3. Click remove icon

**Complete Removal** (delete all data - use with extreme caution):
```bash
# Stop user's server
kubectl delete pod -n cit-jhub jupyter-<username>

# Delete user's home PVC (IRREVERSIBLE!)
kubectl delete pvc -n cit-jhub claim-<username>
```

> ⚠️ **Warning**: Deleting a PVC permanently deletes all user data. Only do this for users who have explicitly requested data deletion or have left the institution.

### Bulk User Operations

**Export User List**:
```bash
# Get all users who have accessed JupyterHub
kubectl get pvc -n cit-jhub -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | grep "^claim-" | sed 's/claim-//'
```

**Get Active Sessions**:
```bash
# Count currently running user pods
kubectl get pods -n cit-jhub -l component=singleuser-server --field-selector=status.phase=Running --no-headers | wc -l
```

---

## Course Management

### Creating a New Course

Follow this complete workflow when adding a new course:

#### Step 1: Create Authentik Group

**Via Authentik UI**:
1. Navigate to **Directory → Groups**
2. Click **Create**
3. **Name**: `course-<course-id>` (e.g., `course-ml2026`)
4. **Parent**: None
5. Click **Create**

#### Step 2: Set Course Password

**Via Authentik Flow Configuration**:
1. Navigate to **Flows & Stages → Flows**
2. Find `course-enrollment` flow
3. Edit the password validation stage
4. Add password mapping for new course:
   ```python
   course_passwords = {
       "course-aml": "password1",
       "course-robotics": "password2",
       "course-ml2026": "new_course_password"  # Add this line
   }
   ```
5. Save changes

**Alternative: Separate Flow per Course** (more secure):
1. Duplicate the `course-enrollment` flow
2. Name it `course-enrollment-<course-id>`
3. Configure single course password
4. Provide course-specific enrollment URL to students

#### Step 3: Create Shared Storage

**Edit**: `bundles/30-storage/manifests/rwx-volumes.yaml`

Add PVC definition:
```yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: course-ml2026-shared
  namespace: cit-jhub
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: longhorn  # or your RWX storage class
  resources:
    requests:
      storage: 50Gi  # Adjust based on course needs
```

#### Step 4: Update JupyterHub Configuration (if needed)

If course needs custom profiles or storage mounts, edit:  
`bundles/20-jupyterhub/values/jupyterhub-values.yaml`

Add course-specific volume mount in the kubespawner configuration:
```python
# In the singleuser.extraFiles section, update profile_list_hook.py
# Add volume mount logic for the new course
```

#### Step 5: Deploy Changes

```bash
# Commit changes
git add bundles/30-storage/manifests/rwx-volumes.yaml
git commit -m "Add storage for course-ml2026"
git push

# Verify Fleet reconciliation
kubectl get gitrepo -n fleet-local cit-teaching-platform -w

# Verify PVC creation
kubectl get pvc -n cit-jhub course-ml2026-shared
```

#### Step 6: Upload Course Materials

```bash
# Option 1: Via kubectl
kubectl cp /local/path/materials cit-jhub/jupyter-<admin-username>:/srv/courses/ml2026/

# Option 2: Via JupyterHub UI as admin
# 1. Login to JupyterHub
# 2. Navigate to /srv/courses/ml2026/
# 3. Upload files via UI
```

#### Step 7: Test Enrollment

1. Use a test account (or incognito browser)
2. Login to JupyterHub
3. Complete enrollment flow with course password
4. Verify:
   - User is added to `course-ml2026` group in Authentik
   - User can access `/srv/courses/ml2026/` in JupyterHub
   - Course materials are visible

### Updating Course Password

**Via Authentik UI**:
1. Navigate to **Flows & Stages → Flows → course-enrollment**
2. Edit the password validation stage
3. Update password for course
4. Save

**Via GitOps** (if flow is version-controlled):
1. Edit flow configuration in repository
2. Commit and push
3. Verify deployment

### Managing Course Storage

**Check Storage Usage**:
```bash
# View PVC status and capacity
kubectl get pvc -n cit-jhub course-<id>-shared

# Get detailed usage (requires exec access to a pod)
kubectl exec -n cit-jhub jupyter-<admin-username> -- df -h /srv/courses/<id>
```

**Expand Storage**:
```bash
# Edit PVC (if storage class supports expansion)
kubectl edit pvc -n cit-jhub course-<id>-shared

# Increase storage request
spec:
  resources:
    requests:
      storage: 100Gi  # Increased from 50Gi
```

**Backup Course Materials**:
```bash
# From a running admin pod
kubectl exec -n cit-jhub jupyter-<admin-username> -- tar czf /tmp/course-<id>-backup.tar.gz /srv/courses/<id>/
kubectl cp cit-jhub/jupyter-<admin-username>:/tmp/course-<id>-backup.tar.gz ./course-<id>-backup.tar.gz
```

### End-of-Semester Cleanup

**Archive Course Data**:
```bash
# 1. Backup course shared storage (see above)
# 2. Notify users to backup personal work
# 3. Optional: Remove course from enrollment flow
# 4. Optional: Archive and delete PVC after grace period
```

**Preserve Data Approach** (recommended):
1. Keep PVC but remove from active enrollment
2. Users in course group retain read-only access
3. Archive at end of academic year

---

## Resource Management

### Understanding Compute Profiles

Compute profiles are defined in `bundles/20-jupyterhub/values/jupyterhub-values.yaml`.

**Current Profiles**:

| Profile | CPU | RAM | GPU | Storage | Groups |
|---------|-----|-----|-----|---------|--------|
| cpu-small | 2 | 6GB | - | 10GB | All |
| cpu-large | 12 | 24GB | - | 100GB | admins, powerusers |
| cpu-xlarge | 48 | 128GB | - | 100GB | admins, powerusers |
| gpu-xsmall | 8 | 24GB | 5GB MIG | 10GB | admins, powerusers |
| gpu-small | 16 | 48GB | 10GB MIG | 10GB | All (course-dependent) |
| gpu-large | 24 | 96GB | 1×A100 | 100GB | admins, powerusers |
| gpu-xlarge | 48 | 128GB | 2×A100 | 100GB | admins, powerusers |

### Adding a New Compute Profile

**Edit**: `bundles/20-jupyterhub/values/jupyterhub-values.yaml`

In the `_original_profile_list`, add:
```python
{
    "display_name": "GPU Medium - Research",
    "slug": "gpu-medium-research",
    "description": "16 CPU, 64GB RAM, 1×A100 GPU (40GB VRAM) - For research projects",
    "kubespawner_override": {
        "cpu_limit": 16,
        "cpu_guarantee": 4,
        "mem_limit": "64G",
        "mem_guarantee": "16G",
        "extra_resource_limits": {
            "nvidia.com/gpu": "1"
        },
        "extra_resource_guarantees": {
            "nvidia.com/gpu": "1"
        },
        "node_selector": {
            "node-role.kubernetes.io/gpu": "true"
        }
    }
},
```

**Deploy**:
```bash
git add bundles/20-jupyterhub/values/jupyterhub-values.yaml
git commit -m "Add GPU medium research profile"
git push
```

**Verify**:
- Check Fleet reconciliation
- Login to JupyterHub as power user
- Verify new profile appears

### Modifying Profile Access

**Make Profile Available to All Students**:

In the `profile_list_hook.py` within values file, add slug to `student_profiles`:
```python
student_profiles = [
    "cpu-small",
    "gpu-small",
    "gpu-medium-research"  # Add this
]
```

**Make Profile Available to Specific Course**:

Add course-specific logic in the hook:
```python
if "course-advanced-ml" in user_groups:
    # Add high-end GPU profiles for advanced ML course
    allowed_profiles.append("gpu-xlarge")
```

### Setting Resource Quotas

**Edit**: `bundles/40-policies/manifests/resourcequotas.yaml`

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: jupyterhub-quota
  namespace: cit-jhub
spec:
  hard:
    requests.cpu: "500"      # Total CPU requests
    requests.memory: "2Ti"   # Total RAM requests
    requests.nvidia.com/gpu: "32"  # Total GPUs
    persistentvolumeclaims: "500"  # Max number of PVCs
    requests.storage: "50Ti" # Total storage
```

**Apply**:
```bash
kubectl apply -f bundles/40-policies/manifests/resourcequotas.yaml
```

### Monitoring Resource Usage

**Current Usage**:
```bash
# Overall cluster usage
kubectl top nodes

# JupyterHub namespace usage
kubectl top pods -n cit-jhub

# Check quota status
kubectl get resourcequota -n cit-jhub jupyterhub-quota -o yaml
```

**User Pod Resource Usage**:
```bash
# Top resource consumers
kubectl top pods -n cit-jhub -l component=singleuser-server --sort-by=memory

# Specific user
kubectl top pod -n cit-jhub jupyter-<username>
```

**GPU Usage**:
```bash
# From a GPU node
kubectl exec -n cit-jhub jupyter-<username> -- nvidia-smi
```

---

## Monitoring and Maintenance

### Health Checks

**Daily Health Check Script**:
```bash
#!/bin/bash
# Save as: /usr/local/bin/cit-platform-health-check.sh

echo "=== CIT Teaching Platform Health Check ==="
echo ""

echo "1. Checking Authentik..."
kubectl get pods -n cit-auth -l app.kubernetes.io/name=authentik
echo ""

echo "2. Checking JupyterHub Hub..."
kubectl get pods -n cit-jhub -l component=hub
echo ""

echo "3. Checking PostgreSQL..."
kubectl get pods -n cit-auth -l app.kubernetes.io/name=postgresql
echo ""

echo "4. Checking active user sessions..."
kubectl get pods -n cit-jhub -l component=singleuser-server --field-selector=status.phase=Running --no-headers | wc -l
echo ""

echo "5. Checking PVC status..."
kubectl get pvc -n cit-jhub | grep -v Bound | wc -l
echo "(Non-bound PVCs - should be 0)"
echo ""

echo "6. Checking cert-manager certificates..."
kubectl get certificates -A | grep -v "True"
echo "(Non-ready certificates - should be empty)"
echo ""

echo "=== Health Check Complete ==="
```

**Run regularly**:
```bash
# Run manually
./cit-platform-health-check.sh

# Or via cron (daily at 8 AM)
0 8 * * * /usr/local/bin/cit-platform-health-check.sh | mail -s "CIT Platform Health" admin@dshl.unileoben.ac.at
```

### Log Monitoring

**Authentik Logs**:
```bash
# Server logs
kubectl logs -n cit-auth -l app.kubernetes.io/component=server -f --tail=100

# Worker logs
kubectl logs -n cit-auth -l app.kubernetes.io/component=worker -f --tail=100

# PostgreSQL logs
kubectl logs -n cit-auth -l app.kubernetes.io/name=postgresql -f --tail=100
```

**JupyterHub Logs**:
```bash
# Hub logs
kubectl logs -n cit-jhub -l component=hub -f --tail=100

# Proxy logs
kubectl logs -n cit-jhub -l component=proxy -f --tail=100

# Specific user pod logs
kubectl logs -n cit-jhub jupyter-<username> -f
```

**Searching Logs for Errors**:
```bash
# Authentik errors in last hour
kubectl logs -n cit-auth -l app.kubernetes.io/component=server --since=1h | grep -i error

# JupyterHub spawn failures
kubectl logs -n cit-jhub -l component=hub --since=1h | grep -i "failed to spawn"
```

### Certificate Management

**Check Certificate Status**:
```bash
# All certificates
kubectl get certificates -A

# Specific certificate
kubectl describe certificate -n cit-auth authentik-tls
kubectl describe certificate -n cit-jhub jupyterhub-tls
```

**Force Certificate Renewal**:
```bash
# Delete certificate secret to trigger renewal
kubectl delete secret -n cit-auth authentik-tls
# cert-manager will automatically recreate it
```

### Database Maintenance

**PostgreSQL Backup**:
```bash
# Get PostgreSQL pod name
PG_POD=$(kubectl get pod -n cit-auth -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')

# Backup database
kubectl exec -n cit-auth $PG_POD -- pg_dump -U authentik authentik > authentik-backup-$(date +%Y%m%d).sql
```

**PostgreSQL Restore** (use with caution):
```bash
# Upload backup
kubectl cp authentik-backup-20260203.sql cit-auth/$PG_POD:/tmp/

# Restore
kubectl exec -n cit-auth $PG_POD -- psql -U authentik authentik < /tmp/authentik-backup-20260203.sql
```

---

## Secret Management

All secrets are encrypted using SOPS with age encryption.

### Prerequisites

- Age private key file (`age.key`)
- SOPS CLI tool installed
- Git repository access

### Decrypting Secrets

```bash
# Set age key path
export SOPS_AGE_KEY_FILE=/path/to/age.key

# Decrypt a secret file
sops -d bundles/10-authentik/authentik-sopssecret.yaml
```

### Editing Secrets

```bash
# Edit and re-encrypt in one command
sops bundles/10-authentik/authentik-sopssecret.yaml

# Your editor opens with decrypted content
# Make changes and save
# File is automatically re-encrypted on save
```

### Rotating Secrets

#### Authentik Secret Key

1. Generate new secret:
   ```bash
   openssl rand -hex 32
   ```

2. Edit SopsSecret:
   ```bash
   sops bundles/10-authentik/authentik-sopssecret.yaml
   ```

3. Update the `AUTHENTIK_SECRET_KEY` value

4. Commit and push:
   ```bash
   git add bundles/10-authentik/authentik-sopssecret.yaml
   git commit -m "Rotate Authentik secret key"
   git push
   ```

5. Restart Authentik pods:
   ```bash
   kubectl rollout restart -n cit-auth deployment/authentik-server
   kubectl rollout restart -n cit-auth deployment/authentik-worker
   ```

#### JupyterHub Cookie Secret

1. Generate new secret:
   ```bash
   openssl rand -hex 32
   ```

2. Edit SopsSecret:
   ```bash
   sops bundles/20-jupyterhub/jupyterhub-sopssecret.yaml
   ```

3. Update the cookie secret value

4. Commit and push

5. Restart JupyterHub:
   ```bash
   kubectl rollout restart -n cit-jhub deployment/hub
   ```

> ⚠️ **Note**: Rotating cookie secret will log out all users.

#### University Keycloak Client Secret

1. Generate new secret in University Keycloak admin
2. Update in Authentik's SSO provider configuration (UI)
3. Also update in SopsSecret for persistence:
   ```bash
   sops bundles/10-authentik/authentik-sopssecret.yaml
   ```

### Managing SOPS Age Key

**Key Storage**:
- Store securely (password manager, HSM, or encrypted storage)
- Never commit to Git
- Maintain backup in separate secure location

**Key Rotation** (advanced):
1. Generate new age key: `age-keygen -o new-age.key`
2. Update `.sops.yaml` with new public key
3. Re-encrypt all secrets: `find bundles -name "*sopssecret.yaml" -exec sops updatekeys {} \;`
4. Update age key secret in cluster:
   ```bash
   kubectl delete secret -n sops-system sops-age-key
   kubectl create secret generic sops-age-key -n sops-system --from-file=age.agekey=new-age.key
   ```
5. Restart SOPS operator:
   ```bash
   kubectl rollout restart -n sops-system deployment/sops-secrets-operator
   ```

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive troubleshooting guide.

### Quick Reference

**User Can't Login**:
1. Check Authentik logs for authentication errors
2. Verify user exists and is active in Authentik
3. Check University Keycloak SSO is operational
4. Verify Authentik OIDC client secret is correct

**User Pod Won't Start**:
1. Check hub logs: `kubectl logs -n cit-jhub -l component=hub --tail=50`
2. Check pending pod events: `kubectl describe pod -n cit-jhub jupyter-<username>`
3. Verify node resources available
4. Check PVC binding status

**Course Enrollment Not Working**:
1. Check flow execution logs in Authentik admin
2. Verify course group exists
3. Verify course password is correct in flow configuration
4. Check user successfully added to group after enrollment

**High Resource Usage**:
1. Identify top consumers: `kubectl top pods -n cit-jhub --sort-by=memory`
2. Check for idle servers: Review admin panel
3. Consider reducing culling timeouts
4. Contact users running large workloads

---

## Emergency Procedures

### Complete Platform Outage

**Triage Steps**:
1. Check Kubernetes cluster health
2. Check namespace resources: `kubectl get pods -A | grep -v Running`
3. Check ingress controller status
4. Check cert-manager certificates

**Communication**:
1. Notify instructors and users via email/Slack
2. Post status update to platform status page
3. Provide estimated resolution time

### Mass Login Event (Lecture Start)

**Preparation**:
1. Verify cluster has adequate resources
2. Pre-pull container images to nodes
3. Increase JupyterHub proxy replicas if needed
4. Monitor during event

**During Event**:
```bash
# Watch pod creation
kubectl get pods -n cit-jhub -l component=singleuser-server -w

# Monitor resource usage
watch kubectl top nodes
```

### Data Loss Incident

**If User Reports Lost Data**:
1. Check PVC still exists: `kubectl get pvc -n cit-jhub claim-<username>`
2. Check pod mount status: `kubectl describe pod -n cit-jhub jupyter-<username>`
3. Check PV backing storage
4. If recoverable, restore from backup
5. If not recoverable, document and notify user

**Prevention**:
- Regular PV backups via Velero or storage provider snapshots
- User education on proper file locations
- Retention policies

### Security Incident

**If Suspicious Activity Detected**:
1. Document the incident (logs, timestamps, affected users)
2. Isolate affected resources (NetworkPolicy, pod deletion)
3. Rotate compromised secrets
4. Notify security team and affected users
5. Review audit logs
6. Implement additional controls

**Compromised User Account**:
```bash
# Immediately stop user's server
kubectl delete pod -n cit-jhub jupyter-<username>

# Disable user in Authentik
# (Uncheck "Is active" in user profile)

# Investigate
kubectl logs -n cit-jhub jupyter-<username> --previous

# Rotate user-specific secrets if applicable
```

---

## Best Practices

### Change Management

1. **Test in development first**: Use a dev cluster or namespace
2. **Change during maintenance windows**: Avoid exam periods
3. **Communicate changes**: Notify users in advance
4. **Have rollback plan**: Know how to revert changes
5. **Document changes**: Update GitOps repo with clear commit messages

### Security

1. **Principle of least privilege**: Grant minimum necessary access
2. **Regular secret rotation**: Rotate secrets quarterly
3. **Audit logs**: Review Authentik audit logs monthly
4. **Update components**: Keep Authentik and JupyterHub updated
5. **Monitor CVEs**: Subscribe to security advisories

### Capacity Planning

1. **Monitor trends**: Track user growth and resource usage
2. **Plan for peaks**: Lectures, exam periods require extra capacity
3. **Storage growth**: PVCs grow over time, plan for expansion
4. **GPU utilization**: Expensive resources should have high utilization

---

## Additional Resources

- **Authentik Documentation**: [https://goauthentik.io/docs/](https://goauthentik.io/docs/)
- **JupyterHub Documentation**: [https://jupyterhub.readthedocs.io/](https://jupyterhub.readthedocs.io/)
- **Zero to JupyterHub (Z2JH)**: [https://z2jh.jupyter.org/](https://z2jh.jupyter.org/)
- **SOPS Documentation**: [https://github.com/mozilla/sops](https://github.com/mozilla/sops)

---

**Last Updated**: February 2026  
**Platform Version**: 1.0  
**Questions?** Contact platform-admins@dshl.unileoben.ac.at
