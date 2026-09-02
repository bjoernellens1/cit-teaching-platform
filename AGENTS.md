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
- **Always** use SOPS for secret management, make sure fleet.yaml bundles have a name: field
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

<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->
