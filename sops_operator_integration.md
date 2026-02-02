Here’s the clean, battle-tested way to do **SOPS + Fleet** without foot-guns. I’ll cover the two patterns that actually work well, what to avoid, and a concrete repo layout + commands.

---

## The core constraint

Fleet itself is “just” applying Kubernetes YAML / Helm. **Kubernetes cannot apply SOPS-encrypted YAML**. So you must ensure **decryption happens before resources reach the API server**.

That gives you two good options:

1. **Decrypt in-cluster using a controller** (recommended for Fleet GitOps)
2. **Decrypt before Fleet sees it** (CI pipeline or local pre-render; simple but less GitOps)

---

## Option A (recommended): SOPS controller in-cluster + commit encrypted secrets

### Best practice: Use **SOPS Secrets Operator** (or Flux SOPS integration if you already run Flux)

In a Fleet/Rancher world, the most common approach is:

* Install a **SOPS-aware operator** in the cluster
* Commit encrypted secret manifests (or “EncryptedSecret” CRs)
* The operator decrypts and creates real `Secret` objects

This avoids giving Fleet itself decryption keys and keeps Git clean.

### How it works (high level)

* You commit `*.enc.yaml` (encrypted)
* You apply a custom resource like `SopsSecret` / `EncryptedSecret` (depends on operator)
* Operator uses a key (Age or KMS) stored in cluster
* Operator writes the decrypted `Secret` into the namespace

### Why this is the right model

* No plaintext secrets in Git
* No plaintext secrets in Fleet bundle rendering logs
* Rotation is manageable
* CIT admin can operate it without “special Fleet magic”

### What you need

* **age** keypair (simplest) *or* cloud KMS (AWS/GCP/Azure)
* SOPS operator installed in `cattle-fleet-system` or a dedicated ops namespace
* RBAC so operator can write Secrets in target namespaces

### Repo pattern

```
bundles/
  10-authentik/
    fleet.yaml
    namespace.yaml
    secrets/
      authentik-secrets.sops.yaml   # encrypted custom resource the operator reads
  20-jupyterhub/
    fleet.yaml
    namespace.yaml
    secrets/
      jhub-secrets.sops.yaml
```

### What NOT to do

* Don’t put `sops:` blocks in a normal `Secret` manifest and expect Fleet/kubectl to decrypt. It won’t.
* Don’t rely on “Fleet doing SOPS by itself” unless you’ve explicitly installed/validated a Fleet extension in your environment. Vanilla Fleet doesn’t magically decrypt.

---

## Option B: Decrypt pre-apply (CI pipeline or local) and feed Fleet plaintext (only in transient artifacts)

This is viable if:

* you control a CI runner
* you want the cluster to be “dumb” (no operators)
* you’re ok with plaintext existing **only as ephemeral CI output**

### Flow

* Keep `secret.enc.yaml` in Git
* CI job decrypts into a **temporary workspace artifact**
* CI runs `fleet apply` / `kubectl apply` against the cluster, or generates a rendered bundle that Fleet pulls from a *private* registry/repo

But: this breaks the “Fleet pulls from Git and applies” simplicity unless you do a second repo or artifact channel.

So for “CIT admins manage afterwards”, **Option A is usually much easier**.

---

## Recommended concrete setup: Age + SOPS Secrets Operator + Fleet

### 1) Create an age keypair (admin machine)

```bash
age-keygen -o age.key
grep "public key" age.key
# note the public key: age1...
```

### 2) Add `.sops.yaml` in repo root (rules)

Example policy:

* encrypt anything in `bundles/**/secrets/*.yaml`
* use the age public key

```yaml
creation_rules:
  - path_regex: bundles/.*/secrets/.*\.yaml
    encrypted_regex: "^(data|stringData)$"
    age: ["age1YOURPUBLICKEY..."]
```

### 3) Install SOPS Secrets Operator via Fleet (bootstrap bundle)

Create `bundles/00-sops-operator/` and deploy:

* operator helm chart
* a `Secret` containing the private age key (in operator namespace)

**Important**: that one secret (age private key) must be injected somehow.
Common approaches:

* Manually apply it once (acceptable bootstrap step)
* Or use your existing secret manager (Infisical/Vault) to inject it
* Or store it as a sealed secret (if you already run sealed-secrets)

### 4) Store the age private key in cluster

In operator namespace (example `sops-system`):

```bash
kubectl -n sops-system create secret generic sops-age \
  --from-file=age.agekey=age.key
```

### 5) Encrypt secrets locally and commit

Create a secret template (plaintext) once:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: authentik-secrets
  namespace: cit-auth
type: Opaque
stringData:
  AUTHENTIK_SECRET_KEY: "..."
  POSTGRES_PASSWORD: "..."
```

Encrypt it:

```bash
sops -e -i bundles/10-authentik/secrets/authentik-secrets.yaml
git add bundles/10-authentik/secrets/authentik-secrets.yaml
```

### 6) Ensure the operator watches that namespace

Depending on operator, you might need:

* label namespaces for reconciliation
* define a CR that references the encrypted file
* or use a “SopsSecret” CR instead of encrypting a normal Secret

(Exact YAML differs by operator, so implement according to the operator you choose.)

---

## Fleet specifics: how to “use it correctly”

### Keep secrets as their own bundle phase

You want ordering:

1. namespaces + CRDs/operators
2. secrets
3. apps that reference secrets

Fleet ordering tools:

* split into multiple bundles with `dependsOn`
* or use bundle `targetCustomizations` with `dependsOn`
* or rely on natural ordering (not recommended)

**Do this:**

* `00-sops-operator` bundle
* `10-authentik-secrets` bundle (dependsOn operator)
* `20-authentik` bundle (dependsOn secrets)
* `30-jhub-secrets` bundle
* `40-jhub` bundle

### Don’t mix “helm values secrets” directly unless you have a plan

Helm values often need secrets.
Best pattern:

* create real Kubernetes Secrets (via operator)
* reference them from Helm values (`existingSecret`, `extraEnvFrom`, etc.)

This keeps Helm values non-sensitive and Git diffable.

---

## What I’d recommend for your CIT stack

For Authentik + JupyterHub:

* Use **SOPS operator** to materialize:

  * `authentik-secret-key`
  * db credentials
  * OIDC client secrets
  * JupyterHub cookie secret
* Use Helm values that reference those secrets.
* Use Fleet bundle dependencies so CIT admin never sees “it works sometimes”.

---

## Quick “choose one” recommendation

* If the CIT admin should manage this long term with minimal CI complexity:
  **Option A: in-cluster SOPS operator + encrypted secrets in Git**.

* If your org forbids secret-decryption operators in clusters:
  **Option B: decrypt in CI and apply directly** (but then Fleet is less central).

---

If you tell me which you prefer (operator vs CI), I’ll give you:

* a repo-ready `bundles/00-sops-operator` Fleet bundle,
* the exact secret/CR format for the chosen operator,
* and the Fleet `dependsOn` wiring for the Authentik + JupyterHub bundles.
