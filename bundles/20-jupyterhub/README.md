# JupyterHub - Interactive Computing Platform

JupyterHub provides the interactive computing environment for the CIT Teaching Platform. Students and researchers use it for data science, machine learning, and course exercises.

## Why JupyterHub?

- **Browser-Based**: No local installation required - students use any browser
- **Consistent Environment**: All users get the same pre-configured environment
- **Scalable Resources**: From small CPU jobs to multi-GPU workloads
- **Persistent Storage**: User work is saved between sessions
- **Course Integration**: Automatic access to course materials and shared storage

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Authentik    │────▶│   JupyterHub    │────▶│   User Pods     │
│   (Auth/OIDC)   │     │      (Hub)      │     │  (Notebooks)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                       │
                              ▼                       ▼
                        ┌─────────────┐         ┌─────────────┐
                        │   SQLite    │         │   Storage   │
                        └─────────────┘         │   (PVCs)    │
                                                └─────────────┘
```

**Components:**
- **Hub**: Orchestrates user authentication and pod spawning
- **Proxy**: Routes traffic to user pods
- **User Pods**: Individual Jupyter notebook servers per user
- **Storage**: Persistent home directories and shared volumes

---

## User Guide

### Getting Started

1. Navigate to **[jhub.dshl.unileoben.ac.at](https://jhub.dshl.unileoben.ac.at)**
2. Click **Login** (redirects to University SSO via Authentik)
3. Select a compute profile (if options appear)
4. Wait for your server to start (~30 seconds)
5. Start coding!

### Compute Profiles

Depending on your group membership, you may see different profiles:

| Profile | CPU | RAM | GPU/VRAM | Storage | Who Can Access |
|---------|-----|-----|----------|---------|----------------|
| **CPU Small** | 2 | 6 GB | - | 10 GB | Everyone |
| **CPU Large** | 12 | 24 GB | - | 100 GB | Admins, Powerusers |
| **CPU XLarge** | 48 | 128 GB | - | 100 GB | Admins, Powerusers |
| **GPU XSmall** | 8 | 24 GB | 5 GB (MIG) | 10 GB | Admins, Powerusers |
| **GPU Small** | 16 | 48 GB | 10 GB (MIG) | 10 GB | Everyone |
| **GPU Large** | 24 | 96 GB | 1x A100 | 100 GB | Admins, Powerusers |
| **GPU XLarge** | 48 | 128 GB | 2x A100 | 100 GB | Admins, Powerusers |

> **Note**: Students (`jhub-students` group) only see CPU Small and GPU Small profiles.

### Your Storage Layout

```
/home/jovyan/
├── work/           # Your personal work directory (persistent)
├── temp/           # Fast temporary storage (cleared on restart!)
├── shared/         # Global shared folder (admins/powerusers only)
└── courses/
    └── <course>/   # Per-course personal directories

/srv/courses/
└── <course>/       # Shared course materials (RWX, all course members)
```

| Directory | Persistent? | Shared? | Notes |
|-----------|-------------|---------|-------|
| `/home/jovyan/work` | ✅ Yes | ❌ Private | Your main working directory |
| `/home/jovyan/temp` | ❌ No | ❌ Private | Fast SSD, cleared on pod restart |
| `/home/jovyan/shared` | ✅ Yes | ✅ Shared | Only for admins/powerusers |
| `/srv/courses/<id>` | ✅ Yes | ✅ Shared | Course materials, all members |

### Tips for Users

1. **Save important work** in `/home/jovyan/work` - this survives restarts
2. **Use temp for scratch work** - `/home/jovyan/temp` is fast but ephemeral
3. **Close your server** when done - click **Control Panel → Stop My Server**
4. **Sessions auto-terminate** after 1 hour of inactivity (max 8 hours)

---

## Admin Guide

### Accessing Admin Features

1. Login to JupyterHub
2. Click **Admin** in the top navigation
3. View all users, their servers, and activity

### User Groups and Access

| Group | Profile Access | Shared Storage | Admin UI |
|-------|----------------|----------------|----------|
| `jhub-admins` | All profiles | ✅ Yes | ✅ Yes |
| `jhub-powerusers` | All profiles | ✅ Yes | ❌ No |
| `jhub-students` | cpu-small, gpu-small | ❌ No | ❌ No |

### Managing Users

**View Active Servers:**
```bash
kubectl get pods -n jupyterhub -l component=singleuser-server
```

**Stop a User's Server (Admin UI):**
1. Go to Admin panel
2. Find the user
3. Click **Stop Server**

**Stop a User's Server (kubectl):**
```bash
kubectl delete pod -n jupyterhub jupyter-<username>
```

### Adding a New Course

1. **Create Authentik group**: `course-<id>` in Authentik admin
2. **Create shared PVC** (add to `30-storage/manifests/rwx-volumes.yaml`):
   ```yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: course-<id>-shared
     namespace: jupyterhub
   spec:
     accessModes:
       - ReadWriteMany
     storageClassName: longhorn
     resources:
       requests:
         storage: 50Gi
   ```
3. **Commit and push** - Fleet will deploy automatically

### Modifying Compute Profiles

Edit `values/jupyterhub-values.yaml` and update the `_original_profile_list` in the `profile_list_hook`:

```python
{
    "display_name": "My New Profile",
    "slug": "my-new-profile",
    "description": "Description here",
    "kubespawner_override": {
        "cpu_limit": 4,
        "cpu_guarantee": 1,
        "mem_limit": "8G",
        "mem_guarantee": "2G",
    }
},
```

To make it available to students, add the slug to `student_profiles` in the hook.

### Monitoring

**Hub Logs:**
```bash
kubectl logs -n jupyterhub -l component=hub -f
```

**User Pod Logs:**
```bash
kubectl logs -n jupyterhub jupyter-<username> -f
```

**Storage Usage:**
```bash
kubectl get pvc -n jupyterhub
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| 500 error on spawn | Check hub logs for Python errors in hooks |
| Pod stuck pending | Check node resources, PVC binding status |
| User can't see profiles | Verify user groups in Authentik |
| Shared folder not mounted | Check if user is in privileged group |
| GPU not available | Verify GPU node labels and MIG configuration |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `values/jupyterhub-values.yaml` | Main Helm configuration (profiles, auth, storage) |
| `shared-pvc.yaml` | Global shared storage PVC |
| `namespace.yaml` | Namespace definition |
| `fleet.yaml` | Fleet deployment configuration |
| `jupyterhub-sopssecret.yaml` | Encrypted secrets reference |

---

## Culling and Resource Management

- **Idle timeout**: 1 hour - inactive servers are stopped
- **Max age**: 8 hours - servers are stopped regardless of activity
- **Check interval**: Every 5 minutes

This ensures resources are freed up between lecture sessions.

---

## Security Considerations

- **OAuth2/OIDC**: All authentication via Authentik
- **Network Policies**: User pods are isolated
- **Resource Quotas**: Prevent resource exhaustion
- **No root access**: Containers run as non-root user (jovyan, UID 1000)
- **Ephemeral temp**: Sensitive temp data cleared on pod restart
