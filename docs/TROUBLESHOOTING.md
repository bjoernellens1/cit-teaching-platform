# CIT Teaching Platform - Troubleshooting Guide

Quick reference for diagnosing and resolving common issues with the CIT Teaching Platform.

## Table of Contents

- [Authentication Issues](#authentication-issues)
- [JupyterHub Issues](#jupyterhub-issues)
- [Storage Issues](#storage-issues)
- [Network Issues](#network-issues)
- [Performance Issues](#performance-issues)
- [Secret and Configuration Issues](#secret-and-configuration-issues)
- [Deployment Issues](#deployment-issues)
- [Emergency Procedures](#emergency-procedures)

---

## Authentication Issues

### Users Cannot Login

**Symptoms**: Login redirects to error page, loops, or shows "Access Denied"

**Diagnostic Steps**:
```bash
# Check Authentik server logs
kubectl logs -n cit-auth -l app.kubernetes.io/component=server --tail=50 | grep -i error

# Check if Authentik is running
kubectl get pods -n cit-auth

# Verify ingress is configured
kubectl get ingress -n cit-auth
```

**Common Causes & Solutions**:

1. **University SSO is down**:
   - Verify university Keycloak is accessible
   - Contact university IT

2. **Wrong client secret**:
   ```bash
   # Update Authentik SSO source configuration in UI
   # Or update in SopsSecret:
   sops bundles/10-authentik/authentik-sopssecret.yaml
   # Then restart pods
   kubectl rollout restart -n cit-auth deployment/authentik-server
   ```

3. **Certificate issues**:
   ```bash
   # Check certificate status
   kubectl describe certificate -n cit-auth authentik-tls
   
   # Force renewal if needed
   kubectl delete secret -n cit-auth authentik-tls
   ```

4. **Authentik database connection failure**:
   ```bash
   # Check PostgreSQL
   kubectl get pods -n cit-auth -l app.kubernetes.io/name=postgresql
   kubectl logs -n cit-auth -l app.kubernetes.io/name=postgresql --tail=50
   ```

### Course Enrollment Fails

**Symptoms**: User enters course password but not added to group

**Diagnostic Steps**:
```bash
# Check Authentik worker logs (flow execution)
kubectl logs -n cit-auth -l app.kubernetes.io/component=worker --tail=100 | grep -i "flow"

# Check if course group exists
# Login to Authentik UI: Directory → Groups
```

**Common Causes & Solutions**:

1. **Wrong course password**:
   - Verify password in flow configuration
   - Update: Flows & Stages → course-enrollment → Edit password stage

2. **Course group doesn't exist**:
   - Create group: Directory → Groups → Create
   - Name must match: `course-<course-id>`

3. **Flow not triggered**:
   - Check flow bindings in Authentik UI
   - Verify user is not already in a course group (may skip enrollment)

### User Has Wrong Permissions

**Symptoms**: User can't access certain profiles or resources

**Diagnostic Steps**:
```bash
# Check user's groups in JupyterHub logs
kubectl logs -n cit-jhub -l component=hub --tail=100 | grep "groups"
```

**Solution**:
1. Login to Authentik UI
2. Directory → Users → Search user
3. View Groups tab
4. Add/remove group memberships as needed
5. User must logout and login again to refresh

---

## JupyterHub Issues

### Server Won't Start / Stuck on Spawn

**Symptoms**: Spinner spins forever, or "Failed to spawn" error

**Diagnostic Steps**:
```bash
# Check hub logs
kubectl logs -n cit-jhub -l component=hub --tail=100

# Check if user pod exists
kubectl get pod -n cit-jhub jupyter-<username>

# Check pod events
kubectl describe pod -n cit-jhub jupyter-<username>

# Check pending pods
kubectl get pods -n cit-jhub --field-selector=status.phase=Pending
```

**Common Causes & Solutions**:

1. **Insufficient resources**:
   ```bash
   # Check node resources
   kubectl top nodes
   
   # Check resource quotas
   kubectl describe resourcequota -n cit-jhub
   ```
   - **Solution**: Scale cluster or stop idle servers

2. **PVC binding failure**:
   ```bash
   # Check PVC status
   kubectl get pvc -n cit-jhub claim-<username>
   
   # Describe PVC for events
   kubectl describe pvc -n cit-jhub claim-<username>
   ```
   - **Solution**: Check storage provisioner, ensure storage class exists

3. **Image pull failure**:
   ```bash
   # Check pod events
   kubectl describe pod -n cit-jhub jupyter-<username> | grep -A5 "Events:"
   ```
   - **Solution**: Verify image exists and is accessible

4. **Profile hook error**:
   ```bash
   # Check hub logs for Python errors
   kubectl logs -n cit-jhub -l component=hub --tail=200 | grep -i "traceback"
   ```
   - **Solution**: Fix Python syntax in profile_list_hook in values file

5. **Node selector mismatch** (GPU pods):
   ```bash
   # Check if GPU nodes exist and are ready
   kubectl get nodes -l nvidia.com/gpu.present=true
   ```
   - **Solution**: Ensure GPU nodes are labeled correctly

### Server Stops Unexpectedly

**Symptoms**: User's server terminates without warning

**Diagnostic Steps**:
```bash
# Check if pod was evicted
kubectl get pods -n cit-jhub | grep Evicted

# Check previous pod logs
kubectl logs -n cit-jhub jupyter-<username> --previous

# Check pod events
kubectl describe pod -n cit-jhub jupyter-<username>
```

**Common Causes & Solutions**:

1. **Out of Memory (OOM killed)**:
   - Pod exceeded memory limit
   - **Solution**: User needs larger profile or to optimize code

2. **Node eviction** (node pressure):
   ```bash
   # Check node conditions
   kubectl describe node <node-name> | grep -A10 "Conditions:"
   ```
   - **Solution**: Add more resources to cluster

3. **Culler terminated idle server**:
   - Expected behavior after 1 hour idle
   - **Solution**: Inform user, adjust culling settings if needed

### Can't Access Files

**Symptoms**: Files saved previously are not visible

**Diagnostic Steps**:
```bash
# Check PVC exists and is bound
kubectl get pvc -n cit-jhub claim-<username>

# Exec into pod and check mounts
kubectl exec -n cit-jhub jupyter-<username> -- df -h

# Check volume mounts
kubectl get pod -n cit-jhub jupyter-<username> -o jsonpath='{.spec.volumes}'
```

**Common Causes & Solutions**:

1. **Files saved in /home/jovyan/temp**:
   - This directory is ephemeral (cleared on restart)
   - **Solution**: No recovery possible, educate user

2. **PVC not mounted**:
   ```bash
   # Check volume mounts
   kubectl describe pod -n cit-jhub jupyter-<username> | grep -A5 "Mounts:"
   ```
   - **Solution**: Check JupyterHub storage configuration

3. **Different username** (edge case):
   - User's username changed, PVC name changed
   - **Solution**: Identify old PVC and migrate data

### Admin Panel Not Accessible

**Symptoms**: No "Admin" button in JupyterHub UI

**Solution**:
1. Verify user is in `jhub-admins` group in Authentik
2. User must logout and login again
3. Check hub logs for group information:
   ```bash
   kubectl logs -n cit-jhub -l component=hub --tail=100 | grep admin
   ```

---

## Storage Issues

### PVC Stuck in Pending

**Symptoms**: PVC status shows "Pending" for extended time

**Diagnostic Steps**:
```bash
# Check PVC status
kubectl get pvc -n cit-jhub <pvc-name>

# Describe PVC for events
kubectl describe pvc -n cit-jhub <pvc-name>

# Check storage class
kubectl get storageclass
```

**Common Causes & Solutions**:

1. **Storage class doesn't exist**:
   ```bash
   # List available storage classes
   kubectl get storageclass
   ```
   - **Solution**: Create storage class or change PVC storageClassName

2. **Storage provisioner not running**:
   ```bash
   # Check Longhorn (or your provisioner)
   kubectl get pods -n longhorn-system
   ```
   - **Solution**: Restart provisioner or check logs

3. **Insufficient storage capacity**:
   ```bash
   # Check available storage
   kubectl get pv
   ```
   - **Solution**: Add more storage to cluster

### Storage Full

**Symptoms**: User can't save files, "No space left on device" error

**Diagnostic Steps**:
```bash
# Check PVC usage (requires exec into pod)
kubectl exec -n cit-jhub jupyter-<username> -- df -h /home/jovyan

# Check PVC capacity
kubectl get pvc -n cit-jhub claim-<username> -o jsonpath='{.spec.resources.requests.storage}'
```

**Solutions**:

1. **Expand PVC** (if storage class supports it):
   ```bash
   kubectl edit pvc -n cit-jhub claim-<username>
   # Increase spec.resources.requests.storage
   ```

2. **User cleanup**:
   - Ask user to delete unnecessary files
   - Clear `/home/jovyan/temp`

3. **Increase default PVC size** (for future users):
   - Edit `bundles/20-jupyterhub/values/jupyterhub-values.yaml`
   - Update `singleuser.storage.capacity`

### Slow Storage Performance

**Symptoms**: File operations are slow, notebooks lag

**Diagnostic Steps**:
```bash
# Benchmark storage from pod
kubectl exec -n cit-jhub jupyter-<username> -- fio \
  --name=randread --ioengine=libaio --iodepth=16 \
  --rw=randread --bs=4k --size=1G --numjobs=1 \
  --runtime=10 --time_based --group_reporting
```

**Solutions**:
- Check storage backend health (Longhorn, Ceph, etc.)
- Consider migrating to faster storage class
- Check for noisy neighbors (other high-I/O workloads)

---

## Network Issues

### Can't Access Platform URLs

**Symptoms**: Connection timeout or DNS resolution failure

**Diagnostic Steps**:
```bash
# Check DNS resolution
nslookup auth.dshl.unileoben.ac.at
nslookup jhub.dshl.unileoben.ac.at

# Check ingress
kubectl get ingress -A

# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller --tail=50
```

**Common Causes & Solutions**:

1. **DNS not configured**:
   - Create A records pointing to ingress IP
   - Verify: `kubectl get svc -n ingress-nginx`

2. **Ingress controller not running**:
   ```bash
   kubectl get pods -n ingress-nginx
   ```
   - **Solution**: Restart or reinstall ingress controller

3. **Certificate issues**:
   ```bash
   # Check certificate
   kubectl describe certificate -n cit-auth authentik-tls
   kubectl describe certificate -n cit-jhub jupyterhub-tls
   ```
   - **Solution**: Check cert-manager logs, verify DNS01/HTTP01 challenge

4. **Firewall blocking ports**:
   - Verify ports 80/443 are open
   - Check cloud security groups / firewall rules

### Network Policy Blocking Traffic

**Symptoms**: Services can't communicate, unexpected connection refused

**Diagnostic Steps**:
```bash
# List network policies
kubectl get networkpolicy -A

# Test connectivity from one pod to another
kubectl exec -n cit-jhub -it <pod> -- curl http://<service>.<namespace>.svc.cluster.local
```

**Solution**:
- Review and update NetworkPolicy manifests
- Add necessary ingress/egress rules
- Temporary workaround: Delete restrictive policy (not recommended for production)

---

## Performance Issues

### High Resource Usage

**Symptoms**: Slow response times, pods evicted

**Diagnostic Steps**:
```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n cit-jhub --sort-by=memory

# Identify resource hogs
kubectl top pods -n cit-jhub -l component=singleuser-server --sort-by=cpu
```

**Solutions**:

1. **Identify and stop idle servers**:
   - JupyterHub Admin → View active users → Stop idle servers

2. **Adjust resource limits**:
   - Edit profile limits in `jupyterhub-values.yaml`

3. **Scale cluster**:
   - Add more worker nodes

4. **Optimize culling**:
   - Reduce idle timeout to free resources faster
   - Edit `cull.timeout` in JupyterHub values

### Slow Spawning

**Symptoms**: User server takes >2 minutes to spawn

**Diagnostic Steps**:
```bash
# Check image pull time
kubectl describe pod -n cit-jhub jupyter-<username> | grep -A10 "Events:"

# Check PVC binding time
kubectl describe pvc -n cit-jhub claim-<username>
```

**Solutions**:

1. **Pre-pull images** to all nodes:
   ```bash
   # Create DaemonSet to pull images
   kubectl apply -f - <<EOF
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: image-prepuller
     namespace: cit-jhub
   spec:
     selector:
       matchLabels:
         name: image-prepuller
     template:
       metadata:
         labels:
           name: image-prepuller
       spec:
         containers:
         - name: prepuller
           image: jupyter/scipy-notebook:latest
           command: ["sh", "-c", "sleep infinity"]
   EOF
   ```

2. **Use image pull secrets** if private registry is slow

3. **Optimize storage provisioning**:
   - Use `volumeBindingMode: Immediate` if appropriate

---

## Secret and Configuration Issues

### SOPS Decryption Failure

**Symptoms**: Secrets not created, SopsSecret resource shows error

**Diagnostic Steps**:
```bash
# Check SOPS operator
kubectl get pods -n sops-system

# Check operator logs
kubectl logs -n sops-system -l app.kubernetes.io/name=sops-secrets-operator --tail=50

# Check SopsSecret status
kubectl get sopssecret -A
kubectl describe sopssecret -n cit-auth authentik-secrets
```

**Common Causes & Solutions**:

1. **Age key missing or incorrect**:
   ```bash
   # Verify secret exists
   kubectl get secret -n sops-system sops-age-key
   
   # Recreate if needed
   kubectl delete secret -n sops-system sops-age-key
   kubectl create secret generic sops-age-key \
     -n sops-system \
     --from-file=age.agekey=/path/to/age.key
   ```

2. **SopsSecret YAML malformed**:
   - Verify YAML syntax
   - Ensure SOPS metadata is present (encrypted fields)

3. **Age public key mismatch**:
   - Ensure `.sops.yaml` has correct public key
   - Re-encrypt secrets if key changed

### Configuration Not Applied

**Symptoms**: Changes in Git not reflected in cluster

**Diagnostic Steps**:
```bash
# Check Fleet GitRepo status
kubectl get gitrepo -n fleet-local cit-teaching-platform

# Check bundle status
kubectl get bundles -A | grep cit

# Check bundle deployment logs
kubectl logs -n cattle-fleet-system -l app=fleet-agent --tail=100
```

**Solutions**:

1. **Force Fleet sync**:
   ```bash
   kubectl delete gitrepo -n fleet-local cit-teaching-platform
   # Then recreate GitRepo
   ```

2. **Check Fleet agent logs** for errors

3. **Verify Git repository is accessible**:
   ```bash
   git ls-remote https://github.com/bjoernellens1/cit-teaching-platform
   ```

---

## Deployment Issues

### Helm Chart Fails to Deploy

**Symptoms**: Bundle shows "Failed", pods not created

**Diagnostic Steps**:
```bash
# Check bundle deployment
kubectl get bundledeployment -A | grep authentik

# Get deployment details
kubectl describe bundledeployment -n <namespace> <bundle-name>

# Check helm release
helm list -A | grep authentik
helm status authentik -n cit-auth
```

**Solutions**:

1. **Syntax error in values file**:
   - Validate YAML: `yamllint bundles/10-authentik/values/authentik-values.yaml`

2. **Missing dependencies**:
   - Ensure required CRDs are installed
   - Check bundle `dependsOn` in fleet.yaml

3. **Resource conflicts**:
   - Check for existing resources with same name
   - Delete conflicting resources if safe

### Rolling Update Stuck

**Symptoms**: Deployment stuck in "Progressing" state

**Diagnostic Steps**:
```bash
# Check rollout status
kubectl rollout status deployment/authentik-server -n cit-auth

# Check deployment
kubectl describe deployment/authentik-server -n cit-auth

# Check pod events
kubectl get events -n cit-auth --sort-by='.lastTimestamp'
```

**Solutions**:

1. **New pods failing to start**:
   - Check pod logs: `kubectl logs -n cit-auth <pod-name>`
   - Rollback: `kubectl rollout undo deployment/authentik-server -n cit-auth`

2. **Resource exhaustion**:
   - Check node resources
   - Scale cluster or reduce other workloads

---

## Emergency Procedures

### Complete Platform Outage

**Immediate Actions**:
1. **Assess scope**: Which components are down?
   ```bash
   kubectl get pods -A | grep -v Running
   ```

2. **Check cluster health**:
   ```bash
   kubectl get nodes
   kubectl get componentstatuses
   ```

3. **Notify users**: Post outage notice

4. **Check recent changes**:
   ```bash
   git log --oneline -10
   ```

5. **Rollback if needed**:
   ```bash
   git revert HEAD
   git push
   ```

### Database Corruption

**Immediate Actions**:
1. **Stop writes**: Scale Authentik to 0 replicas
   ```bash
   kubectl scale deployment/authentik-server --replicas=0 -n cit-auth
   kubectl scale deployment/authentik-worker --replicas=0 -n cit-auth
   ```

2. **Restore from backup**:
   ```bash
   # See INFRASTRUCTURE.md → Backup and Disaster Recovery
   ```

3. **Verify integrity**:
   ```bash
   PG_POD=$(kubectl get pod -n cit-auth -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')
   kubectl exec -n cit-auth $PG_POD -- psql -U authentik -c "SELECT version();"
   ```

4. **Scale back up**:
   ```bash
   kubectl scale deployment/authentik-server --replicas=2 -n cit-auth
   kubectl scale deployment/authentik-worker --replicas=2 -n cit-auth
   ```

### Security Breach

**Immediate Actions**:
1. **Isolate affected resources**:
   ```bash
   # Apply strict NetworkPolicy
   kubectl apply -f - <<EOF
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: emergency-deny-all
     namespace: cit-jhub
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   EOF
   ```

2. **Rotate all secrets** (see ADMIN_GUIDE.md)

3. **Review audit logs**:
   ```bash
   # Authentik audit events
   # JupyterHub logs
   kubectl logs -n cit-jhub -l component=hub --since=24h | grep -i auth
   ```

4. **Notify security team and affected users**

5. **Perform forensic analysis**

---

## Getting Help

### Internal Support Channels

- **Platform Admins**: platform-admins@dshl.unileoben.ac.at
- **Emergency Hotline**: +43 XXX XXX XXX
- **Internal Wiki**: https://wiki.dshl.unileoben.ac.at/cit-platform

### External Resources

- **Authentik Support**: https://goauthentik.io/docs/troubleshooting/
- **JupyterHub Discourse**: https://discourse.jupyter.org/
- **Kubernetes Troubleshooting**: https://kubernetes.io/docs/tasks/debug/

### Creating a Support Ticket

Include the following information:
1. **Symptoms**: What's not working?
2. **Timeline**: When did it start?
3. **Scope**: Who's affected?
4. **Logs**: Relevant log excerpts
5. **Steps to reproduce**
6. **What you've tried**

---

**Last Updated**: February 2026  
**Platform Version**: 1.0
