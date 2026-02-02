Below is a **practical, “handoff-ready” outline** for a new **CIT teaching JupyterHub + dedicated Authentik** on your Kubernetes cluster, managed via **a separate Git repo + Fleet bundle**, and designed so the CIT admin can take over cleanly.

---

## 1) Target architecture

### Identity chain (what logs into what)

**Uni Keycloak (SSO) → Authentik (CIT) → JupyterHub (CIT)**

* Users *only* see “Login with University SSO”.
* **Authentik is the broker**:

  * creates/updates users on first login
  * assigns groups based on Keycloak claims *and/or* your **course enrollment flow**
  * provides OIDC to JupyterHub
* JupyterHub uses Authentik OIDC; group membership controls:

  * admin rights
  * which course resources / shared folders appear
  * (optional) spawn profiles / GPU access

### Workloads

* **authentik**: server + worker + (embedded) outpost + Postgres + Redis
* **jupyterhub (z2jh)**: hub + configurable-http-proxy + user pods
* **storage**:

  * per-user persistent home (PVC per user)
  * shared course volumes (RWX) for `/srv/courses/<course>` (recommended NFS/CephFS/Longhorn RWX if you must)

---

## 2) New Git repo + Fleet bundle layout

Create a new repo, e.g. `cit-teaching-platform`.

Recommended structure (GitOps-friendly, handoff-friendly):

```
cit-teaching-platform/
  README.md
  AGENTS.md
  fleet.yaml
  bundles/
    00-crds/
      fleet.yaml
      cert-manager/           # only if you deploy it here (often cluster-level elsewhere)
    10-authentik/
      fleet.yaml
      namespace.yaml
      helmrelease.yaml        # or plain HelmChart values.yaml depending on your Fleet style
      values/
        authentik-values.yaml
      secrets/
        sops/
          authentik-secrets.enc.yaml
          postgres-secrets.enc.yaml
    20-jupyterhub/
      fleet.yaml
      namespace.yaml
      values/
        jupyterhub-values.yaml
      secrets/
        sops/
          jupyterhub-secrets.enc.yaml
    30-storage/
      fleet.yaml
      manifests/
        storageclasses.yaml
        rwx-volumes.yaml
    40-policies/
      fleet.yaml
      manifests/
        networkpolicies.yaml
        resourcequotas.yaml
        podsecurity.yaml
```

**Fleet bundle naming**: keep them descriptive:

* `cit-authentik`
* `cit-jupyterhub`
* `cit-storage`
* `cit-policies`

Handoff principle: CIT admin mostly touches only:

* `values/authentik-values.yaml`
* `values/jupyterhub-values.yaml`
* the SOPS secret files

---

## 3) Namespaces, ingress, DNS

Use two namespaces:

* `cit-auth` (Authentik + db/redis/outpost)
* `cit-jhub` (JupyterHub)

Ingress:

* `auth.cit.<your-domain>` → Authentik
* `jhub.cit.<your-domain>` → JupyterHub

TLS:

* ideally cert-manager cluster-wide with per-namespace `Certificate`
* or your existing wildcard secret mirrored into these namespaces (reflector/replicator)

---

## 4) Authentik “for scale” configuration

### Core HA settings

* **Postgres**: managed external DB preferred; otherwise in-cluster with:

  * persistent volume
  * backups (CronJob + off-cluster)
  * resources sized (teaching spikes)
* **Redis**: required; use HA if you already have it
* **Authentik server**:

  * `replicas: 2+`
  * readiness/liveness probes
  * horizontal scaling OK (stateless)
* **Authentik worker**:

  * `replicas: 2+`
  * set concurrency based on load (flows + events)
* **Outpost**:

  * run as Deployment in-cluster (recommended)
  * keep it in the same namespace and managed by Helm

### Operational hardening (teaching friendly)

* rate limits / brute-force protection (Authentik has policies)
* session duration aligned with lectures
* email: optional (nice for invites), but not required if using Keycloak SSO

### What “scale” means here

For a lecture with e.g. 200 logins in 2 minutes:

* Authentik server 2–3 replicas
* worker 2 replicas
* Postgres sized adequately (or external)
* ingress with enough connections/timeouts

---

## 5) Authentik: Uni Keycloak SSO source + automatic user/group provisioning

### Configure Uni Keycloak as an Authentik “Source” (OIDC)

In Authentik:

1. **Sources → OAuth/OIDC**
2. Discovery URL from Uni Keycloak realm
3. Client ID/secret from Uni Keycloak
4. Scopes: include `openid profile email` plus whatever provides group/role claims
5. **User creation enabled** (create on first login)

### Group mapping from Keycloak → Authentik groups

If Uni Keycloak provides group/role claims:

* create **Property Mappings** (extract `groups` or `realm_access.roles`)
* add **Group Mappings**:

  * Keycloak claim contains `cit_course_ml2026` → add user to Authentik group `course-ml2026`
  * claim contains `cit_admins` → add user to `jhub-admins`

If Uni Keycloak does **not** provide course info (you said it doesn’t):

* still use Keycloak for identity
* do course membership via your **course enrollment flow** inside Authentik (next section)

---

## 6) Authentik: your course enrollment flow (choose course + enter password)

Goal:

* after first SSO login, user is routed into an enrollment flow:

  * choose course
  * enter course password (or per-course code)
  * Authentik adds them to the course group

### Minimal model in Authentik

* Groups:

  * `course-aml`
  * `course-robotics`
  * `course-datamodeling`
  * `jhub-admins`
* Each course has a **shared secret** (course password) stored in Authentik (or in a secrets backend)
* Flow:

  1. Prompt: course selection (dropdown)
  2. Prompt: password input
  3. Script stage: verify password matches the course
  4. Group assignment stage: add user to the corresponding `course-*` group
  5. Redirect to JupyterHub

### How to enforce the enrollment flow

* set Authentik **default authentication flow** for that Source
* or add a policy: if user not in any `course-*` group, force enrollment flow on login

This keeps Uni Keycloak purely for authentication while Authentik handles teaching authorization.

---

## 7) JupyterHub (Z2JH) configuration (teaching-optimized)

### Core choices

* Helm chart: **zero-to-jupyterhub**
* Auth: **GenericOAuthenticator** with Authentik OIDC
* Spawner: **KubeSpawner**
* Storage:

  * per-user PVC: default
  * shared course volumes: extra mounts based on groups

### Teaching-friendly defaults

* idle culler enabled (aggressive during class)
* pre-pulled images (reduce spawn latency)
* resource guarantees/limits per user profile (small/medium/gpu)
* node affinity/tolerations if you separate teaching nodes

### Group → profile / mounts mapping

You want:

* user in `course-aml` sees:

  * `/srv/courses/aml` (shared RWX)
  * maybe a specific image/profile
* user in `course-robotics` sees `/srv/courses/robotics`
* admins in `jhub-admins` become JupyterHub admins

This is typically implemented by:

* passing groups in OIDC claim
* in JupyterHub config:

  * `auth_state` contains groups
  * a `pre_spawn_hook` applies mounts and creates folders

---

## 8) “Automatically create new subfolders and groups” on first SSO sign-in

You asked specifically:

> instructions how to automatically create new subfolders and groups for users signed in via uni keycloak sso

There are two parts:

### A) Automatically create users + groups (in Authentik)

**Users**: created on first SSO login (standard Authentik Source setting).

**Groups**: you usually **pre-create** the canonical groups (`course-*`, `jhub-admins`) as “targets”.
Then membership is automatic via:

* Keycloak claim group mapping **or**
* your enrollment flow

If you *really* want auto-create groups dynamically:

* do it only for predictable naming (e.g. `course-<courseId>`)
* implement in Authentik via a **custom script stage** that:

  * checks if group exists, creates if missing, then assigns user
    But in teaching ops, it’s usually safer to **pre-create** groups and only automate membership.

### B) Automatically create subfolders (inside each user’s home + optional shared)

Use a **JupyterHub `pre_spawn_hook`** + an **initContainer**.

**Pattern**:

1. user logs in
2. spawner creates user pod
3. initContainer runs `mkdir -p` in the mounted PVC:

   * `/home/jovyan/work`
   * `/home/jovyan/courses/<course>`
   * `/home/jovyan/shared`
4. main notebook container starts

If you also want **shared course folders**:

* mount `/srv/courses/<course>` (RWX volume) into the pod **only if** user is in that course group.

### Example JupyterHub config snippet (conceptual)

This is the mechanism you want (not full chart values, but the key idea):

```python
# jupyterhub_config.py (in Helm values hub.extraConfig)

async def pre_spawn_hook(spawner):
    auth_state = await spawner.user.get_auth_state()
    groups = set((auth_state or {}).get("oauth_user", {}).get("groups", []))

    # Always create these user-local folders
    spawner.environment.update({
        "INIT_DIRS": "/home/jovyan/work /home/jovyan/shared"
    })

    # Add course-local folders and shared mounts based on groups
    course_ids = []
    for g in groups:
        if g.startswith("course-"):
            course_ids.append(g.replace("course-", ""))

    # user-local course dirs
    if course_ids:
        spawner.environment["INIT_DIRS"] += " " + " ".join(
            f"/home/jovyan/courses/{c}" for c in course_ids
        )

    # Optionally mount shared volumes per course
    # (you'd also set spawner.volume_mounts/spawner.volumes here)
```

Then in the singleuser pod template, use an initContainer that reads `INIT_DIRS` and creates them.

---

## 9) How to pass groups from Authentik → JupyterHub reliably

Make sure Authentik includes group membership in the OIDC token.

In Authentik:

* create a **Scope Mapping** (or claim mapping) that adds:

  * `groups: ["course-aml", "course-robotics", ...]`

In JupyterHub:

* configure the OAuthenticator to read that claim as `groups`
* map:

  * `jhub-admins` → JupyterHub admin users

---

## 10) Operational handoff checklist for CIT admin

Put this in your repo `README.md`:

* How to rotate:

  * Uni Keycloak client secret
  * Authentik secrets
  * JupyterHub cookie secret
* How to add a new course:

  1. create Authentik group `course-<id>`
  2. add course password entry (flow config)
  3. create RWX volume + mount definition for `/srv/courses/<id>`
  4. add it to JupyterHub mapping (if needed)
* How to add/remove admins:

  * manage membership of `jhub-admins` in Authentik

---

## 11) Concrete “next steps” you can execute immediately

1. Create repo `cit-teaching-platform` with the folder structure above.
2. Add Fleet bundle `cit-authentik` deploying:

   * authentik + redis + postgres (or external)
   * ingress + TLS
3. In Authentik UI:

   * create OIDC source for Uni Keycloak
   * create groups `course-*`, `jhub-admins`
   * implement enrollment flow (course select + password)
   * create provider/application for JupyterHub (OIDC)
4. Add Fleet bundle `cit-jupyterhub` deploying z2jh configured for Authentik OIDC.
5. Implement:

   * group claim mapping
   * pre_spawn_hook + initContainer for directory creation
   * shared RWX mounts per course
6. Document handoff and “course lifecycle” in README.

---

If you want, I can turn this into a **fully fleshed-out repo skeleton** (ready-to-commit) with:

* Fleet `fleet.yaml` per bundle
* Helm values for Authentik + Z2JH
* SOPS secret templates
* the `pre_spawn_hook` + initContainer wiring
* NetworkPolicies + ResourceQuotas suitable for a lecture environment
