# CIT compute pilot integration

Status: staged / not deployed. This directory is outside Fleet's `bundles/` tree.
The existing chart remains 4.4.2, with Authentik via Dex, unchanged usernames/PVCs
and existing authenticator group replacement until grants have been seeded.
Do not switch `manage_groups` off before importing and reviewing grants.

`config.json` targets application 0.1.0 and pins the shared generated policy hash.
The policy was compiled from the CPS cluster catalog; edit it there and refresh
this copy together with its hash. It uses the eight nominal40GiB A100 pool, not
an independently duplicated CIT allowance. CPU/batch grants remain independent
of pooled interactive reservations, keyed by canonical person across Hubs.

The CIT console owns CIT course/project/grant records, uses one replica and its
own persistent SQLite database, OAuth client and distinct Hub/policy/backup
credential references. CPS console storage and credentials must not be reused.
No secret values, workloads or migration jobs are installed by this stage.
Moodle remains planned / not deployed and local courses stay active.

`hub-values.yaml` delegates to the released `cps_compute.hub.configure_hub(c,
config)` adapter only if explicitly enabled. `hub-config.json` provides its exact released
configuration keys with `enabled: false`. Its configuration file, released
Hub adapter image, exact policy mount, identity mapping and secret references must
be rendered from qualified release artifacts before activation. The adapter is
not vendored into live Helm values. The overlay is intentionally not wired into
Fleet or accompanied by guessed image digests or live secret material.

The addon uses PageConfig `cpsComputeGatewayUrl` pointing to a same-origin
visitor-authenticated proxy, e.g. `/api/compute/v1/`. A server authenticates the
actual visitor via the Hub, forwards that verified visitor bearer and trusted
`X-CPS-Hub: cit` internally, and never exposes Kubernetes, administrative Hub,
policy or Argo credentials. A shared notebook kernel's token cannot identify the
browser visitor. This proxy requires end-to-end identity qualification.

Before enabling: record image digests and tested compatibility, seed existing
memberships/time-bounded grants, review canonical-person aliases and NFS/PVC
mappings, back up matching Hub/console DB versions, qualify OAuth state/redirect/
PKCE/cookies, verify visitor identity and cross-Hub reservations. Validate with
`python3 scripts/validate_compute_platform.py` and `python3 -m pytest tests -q`.
Activation still requires the main platform acceptance evidence and an explicit
reviewed Fleet change. Hub6 qualification remains an independent stage.

Canonical application APIs and migrations belong in the released cps-compute
and CPS e2x-course-hub fork; cluster-wide queues, admission, monitoring, artifact
storage and operator recovery guidance belong in cps-gpu-cluster. Notebook
variants consume the same released compute wheel and prebuilt addon via the
cps-jupyter-notebook runtime release overlay.
