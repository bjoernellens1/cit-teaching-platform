Below is a **code-agent friendly** change plan to adapt an existing **Z2JH (Helm) + nginx-ingress** deployment from **path-based** to **subdomain-based** user servers.

---

## Goal

Move from:

* `https://jhub.dshl.unileoben.ac.at/user/<name>/...`

to:

* `https://<name>.jhub.dshl.unileoben.ac.at/...`

Still using the same `proxy-public` Service; only routing changes.

---

## Preconditions (must exist)

1. **Wildcard DNS**

   * `jhub.dshl.unileoben.ac.at` → ingress public IP/LB
   * `*.jhub.dshl.unileoben.ac.at` → same ingress public IP/LB

2. **Wildcard TLS certificate**

   * Covers `jhub.dshl.unileoben.ac.at` **and** `*.jhub.dshl.unileoben.ac.at`
   * Stored as a Kubernetes TLS secret in the same namespace as JupyterHub (or referenced correctly)

---

## Step 1 — Update `values.yaml`

Edit your existing Z2JH `values.yaml` and add/adjust:

```yaml
hub:
  config:
    JupyterHub:
      # Enables per-user subdomains
      subdomain_host: "https://jhub.dshl.unileoben.ac.at"

      # Optional: only add if you hit login loops / cookie issues
      # cookie_domain: "jhub.dshl.unileoben.ac.at"
```

Notes:

* Use the **exact external base domain** you want.
* Keep scheme `https://`.

---

## Step 2 — Ensure ingress handles BOTH hosts

You need your ingress to route requests for:

* `jhub.dshl.unileoben.ac.at`
* `*.jhub.dshl.unileoben.ac.at`

### Option A (recommended): z2jh-managed ingress with two hosts

If you already use Z2JH’s built-in ingress config, set:

```yaml
proxy:
  https:
    enabled: false   # (only if TLS is terminated at ingress; typical with nginx-ingress)
  service:
    type: ClusterIP

ingress:
  enabled: true
  ingressClassName: nginx
  hosts:
    - jhub.dshl.unileoben.ac.at
    - "*.jhub.dshl.unileoben.ac.at"
  tls:
    - secretName: dshl-wildcard-tls #or whatver secrect name we are already using
      hosts:
        - jhub.dshl.unileoben.ac.at
        - "*.jhub.dshl.unileoben.ac.at"
```

**Important:** some chart versions name these fields differently (`proxy.ingress.*` vs `ingress.*`). If your current deployment already has ingress working, mirror the same structure and just **add the wildcard host + TLS SAN**.

### Option B: separate Ingress object you manage (Fleet / GitOps style)

Create/patch an Ingress that points to the Z2JH proxy service:

* service name: typically `<release-name>-proxy-public`
* service port: `80` (if TLS terminated at ingress) or `443` (if proxy does TLS itself)

Example Ingress (TLS at nginx-ingress):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jhub-proxy
  namespace: <NAMESPACE>
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
spec:
  ingressClassName: nginx
  tls:
    - secretName: hub-wildcard-tls
      hosts:
        - hub.example.com
        - "*.hub.example.com"
  rules:
    - host: hub.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: <RELEASE>-proxy-public
                port:
                  number: 80
    - host: "*.hub.example.com"
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: <RELEASE>-proxy-public
                port:
                  number: 80
```

---

## Step 3 — Deploy the change

Helm upgrade:

```bash
helm upgrade --install <RELEASE> jupyterhub/jupyterhub \
  -n <NAMESPACE> \
  -f values.yaml
```

If you deploy via Fleet, commit the values change and let Fleet reconcile.

---

## Step 4 — Validate

Run:

```bash
kubectl -n <NAMESPACE> get ingress
kubectl -n <NAMESPACE> describe ingress <ingress-name>
```

Then test:

* `https://hub.example.com/hub/` loads
* After login, user server appears at:

  * `https://<username>.hub.example.com/`

You can also verify routing by checking the proxy logs (optional):

```bash
kubectl -n <NAMESPACE> logs deploy/<RELEASE>-proxy -c chp --tail=200
```

---

## Step 5 — Common failure modes + fixes

### A) Login loop / “redirecting…” between domains

Add cookie domain:

```yaml
hub:
  config:
    JupyterHub:
      cookie_domain: "hub.example.com"
```

Upgrade again.

### B) Wildcard host not routed (404 from ingress)

* Confirm ingress really has rule for `*.hub.example.com`
* Confirm DNS wildcard resolves to the same LB/IP
* Confirm TLS secret includes wildcard SAN and is referenced by ingress

### C) Mixed TLS termination confusion

Pick one:

**TLS at ingress (recommended with nginx-ingress)**

* Ingress has `tls:` and points to service port `80`
* Z2JH proxy has `proxy.https.enabled: false`

**TLS at JupyterHub proxy**

* Ingress can be TCP passthrough (more complex) or terminate TLS and re-encrypt
* Avoid unless you already run it this way

---

## Exactly what the code agent should change (diff-style checklist)

1. `values.yaml`

   * Add `hub.config.JupyterHub.subdomain_host: "https://hub.example.com"`
   * Optionally add `hub.config.JupyterHub.cookie_domain: "hub.example.com"` if needed

2. Ingress configuration (choose one)

   * If chart-managed ingress: add `*.hub.example.com` to hosts + TLS hosts
   * If external ingress: add second rule for wildcard host pointing to `*-proxy-public`

3. Ensure TLS secret exists and is referenced

---

If you paste your **current** `values.yaml` ingress/proxy section (just that part), I’ll rewrite it into the exact final YAML for your deployment style (chart-managed vs separate ingress) without guessing field names.
