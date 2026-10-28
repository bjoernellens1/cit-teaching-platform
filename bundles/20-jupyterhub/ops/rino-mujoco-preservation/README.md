# Rino MuJoCo Hub overlay recovery

The CIT JupyterHub Fleet bundle currently owns the Helm chart values, while the
restored deployment also carries native proof and policy volumes that are not
represented in the checked-in values file. A full Helm-values change can replace
the generated Hub configuration Secret and PodSpec lists, removing those
overlays. This recovery applies only the three reviewed Deployment fields and
leaves every other volume, mount, annotation, and container setting intact.

The current Hub configuration Secret contains credentials and the effective
`hub.extraConfig.zz-native-group-pilot` adapter call. The exception Secret
contains `settings.json` and `grant-record.json`. Neither Secret payload belongs
in Git or terminal output. `apply_overlay.py` validates the required adapter
references and exact one-user exception settings in memory, without displaying
or writing secret data.

## Preconditions

Use the actual CIT cluster context and wait until any Fleet rollout has settled.
First inspect only the Hub image and Secret reference names (never use
`kubectl get secret -o yaml` in a terminal):

```sh
kubectl --context <cit-context> -n cit-jhub get deployment hub \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="hub")].image}{"\n"}{.spec.template.spec.volumes[?(@.name=="secret")].secret.secretName}{"\n"}'
```

The expected target is Hub image
`ghcr.io/mul-cps/cps-compute@sha256:5d6803af796bcac8b9487eafb87c3928d7279c958530a0b5ec1ae4640858f31b`,
config Secret `cps-rino-hub-config-20261028`, and exception Secret
`cps-rino-mujoco-exception`. The script requires the currently observed image
and config Secret name as explicit compare-and-swap inputs. Its default mode is
read-only:

```sh
python3 bundles/20-jupyterhub/ops/rino-mujoco-preservation/apply_overlay.py \
  --context <cit-context> \
  --expect-current-image '<exact image printed above>' \
  --expect-current-config-secret '<exact config Secret name printed above>'
```

Review the clean preflight result, then add `--apply` to apply the bounded patch.
The script checks the current Deployment UID and resourceVersion at patch time,
so a concurrent Fleet update makes it fail closed. It pins the Hub image and
config Secret, and adds or corrects only the exception Secret volume and
read-only mount at `/etc/cps-personal-exclusive`. It validates the live
`cps-rino-research` PriorityClass is value 60, has `preemptionPolicy: Never`,
and is not the global default. The adapter assigns that class only to
m12113877's default server; the class resource is managed separately in the
cluster repository. The Hub Deployment itself is not assigned this class.

After an apply, confirm the Deployment image and Secret reference names with the
same JSONPath query, then wait for the Hub rollout and confirm Rino's default
server through the established recovery procedure. Do not infer workload
qualification from a successful Deployment patch.

## Secret recovery

The script refuses to act if either Secret is missing, malformed, or outside
the reviewed one-user settings. Restore a missing Secret from the CIT-approved
encrypted backup or the authorized SOPS secret-management workflow before
retrying. Do not reconstruct it from a terminal dump, copy `values.yaml` into
this repository, or paste secret data into an issue. If no encrypted backup is
available, stop and have the secret owner recover the original values through
the approved credential custody process; the grant UUID and credentials must
remain unchanged.

## Durability boundary

This is a compare-and-swap repair for a reconciled Deployment, not an automatic
Fleet post-renderer. Re-run it after any Fleet reconciliation that resets the
Hub image or personal Secret references. A permanent declarative conversion
requires first bringing the current native proof/policy overlay resources and
their secret custody into the CIT bundle's reviewed source of truth, then
rendering and reviewing the complete Fleet result before changing ownership.
The existing CIT values file is intentionally left untouched by this patch.
