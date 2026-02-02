# Bootstrap Guide: SOPS Operator Setup

This document describes the one-time bootstrap procedure required to enable SOPS-encrypted secrets in the CIT Teaching Platform cluster.

## Prerequisites

- `kubectl` configured with cluster admin access
- `age` CLI tool installed (`brew install age` or `nix-env -iA nixpkgs.age`)
- `sops` CLI tool installed (`brew install sops` or `nix-env -iA nixpkgs.sops`)
- Access to the age private key file (`age.key`)

## Step 1: Deploy Age Private Key Secret

The SOPS operator needs access to the age private key to decrypt secrets. This secret must be created manually before Fleet can reconcile the SOPS operator bundle.

```bash
# Create the sops-system namespace
kubectl create namespace sops-system

# Create the age key secret
kubectl -n sops-system create secret generic sops-age-key \
  --from-file=age.agekey=/path/to/your/age.key
```

> **Security Note**: The `age.key` file should be stored securely (e.g., in a password manager or HSM) and never committed to Git.

## Step 2: Encrypt SopsSecret Files

The SopsSecret template files in this repository contain placeholder values. You need to fill in the actual secret values and encrypt them using SOPS.

### Decrypt existing secrets for migration

If migrating from the old `*.enc.yaml` format:

```bash
# Decrypt an existing secret to get the values
export SOPS_AGE_KEY_FILE=/path/to/your/age.key
sops -d bundles/05-postgres/secrets/sops/postgres-secrets.enc.yaml
```

### Edit and encrypt new SopsSecret files

```bash
# Edit the SopsSecret file with real values
# Replace PLACEHOLDER_REENCRYPT with actual secret values
nano bundles/05-postgres/secrets/sopssecrets/postgres-sopssecret.yaml

# Encrypt the file in-place
sops -e -i bundles/05-postgres/secrets/sopssecrets/postgres-sopssecret.yaml
```

Repeat for all SopsSecret files:
- `bundles/05-postgres/secrets/sopssecrets/postgres-sopssecret.yaml`
- `bundles/10-authentik/secrets/sopssecrets/authentik-sopssecret.yaml`
- `bundles/20-jupyterhub/secrets/sopssecrets/jupyterhub-sopssecret.yaml`

## Step 3: Verify Fleet Reconciliation

After committing and pushing the encrypted SopsSecret files:

```bash
# Check that the SOPS operator is running
kubectl get pods -n sops-system

# Verify SopsSecrets are being processed
kubectl get sopssecrets -A

# Check that actual Secrets are created
kubectl get secrets -n cit-postgres postgres-credentials
kubectl get secrets -n cit-auth authentik-secrets
kubectl get secrets -n cit-jhub jupyterhub-oidc-secret
```

## Step 4: Clean Up Old Encrypted Secrets

Once verified, you can optionally remove the old `*.enc.yaml` files:

```bash
rm bundles/*/secrets/sops/*.enc.yaml
```

## Troubleshooting

### Operator not starting
Check the operator logs:
```bash
kubectl logs -n sops-system -l app.kubernetes.io/name=sops-secrets-operator
```

### Secrets not being created
Verify the age key is correctly mounted:
```bash
kubectl exec -n sops-system deploy/sops-secrets-operator -- ls -la /etc/sops-age-key/
```

### Decryption errors
Ensure the SOPS metadata in your SopsSecret files matches the age public key in `.sops.yaml`.
