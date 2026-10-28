#!/usr/bin/env python3
"""CAS patch for the reviewed Rino Hub deployment overlay.

This intentionally changes only the Hub image and two Secret references. It
does not replace PodSpec lists, so unrelated native proof/policy mounts stay
intact. Secret values are read only for in-memory preflight and never printed.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import uuid


NAMESPACE = "cit-jhub"
DEPLOYMENT = "hub"
HUB_IMAGE = (
    "ghcr.io/mul-cps/cps-compute@sha256:"
    "5d6803af796bcac8b9487eafb87c3928d7279c958530a0b5ec1ae4640858f31b"
)
HUB_CONFIG_SECRET = "cps-rino-hub-config-20261028"
EXCEPTION_SECRET = "cps-rino-mujoco-exception"
EXCEPTION_MOUNT = "/etc/cps-personal-exclusive"
PRIORITY_CLASS = "cps-rino-research"


class Refusal(Exception):
    pass


def kubectl(context: str, *args: str, stdin: str | None = None) -> str:
    command = ["kubectl", "--context", context, *args]
    result = subprocess.run(command, input=stdin, text=True, capture_output=True)
    if result.returncode:
        # kubectl errors may include object content; deliberately suppress it.
        raise Refusal(f"kubectl command failed ({' '.join(args[:3])}); no changes made")
    return result.stdout


def get_json(context: str, resource: str, name: str) -> dict:
    raw = kubectl(context, "-n", NAMESPACE, "get", resource, name, "-o", "json")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise Refusal(f"{resource}/{name} returned invalid JSON; no changes made") from None


def decoded_secret_data(secret: dict, name: str) -> dict[str, bytes]:
    if secret.get("metadata", {}).get("name") != name:
        raise Refusal(f"Secret identity mismatch for {name}; no changes made")
    try:
        return {
            key: base64.b64decode(value, validate=True)
            for key, value in secret.get("data", {}).items()
        }
    except (ValueError, TypeError):
        raise Refusal(f"Secret {name} has invalid encoded data; no changes made") from None


def validate_config_secret(secret: dict) -> None:
    data = decoded_secret_data(secret, HUB_CONFIG_SECRET)
    values = data.get("values.yaml")
    if values is None:
        raise Refusal(f"Secret {HUB_CONFIG_SECRET} lacks values.yaml; no changes made")
    text = values.decode("utf-8", errors="strict")
    required = (
        "zz-native-group-pilot:",
        "from cps_compute_hub.native_pending_hub import install_pending_group_hub_configuration",
        "from cps_compute_hub.personal_exclusive import PersonalExclusiveAdapter",
        "personal_exclusive=PersonalExclusiveAdapter.from_operator_config",
        "/etc/cps-native-kai-hub/config/settings.json",
        "/etc/cps-personal-exclusive/settings.json",
    )
    if not all(part in text for part in required):
        raise Refusal(
            f"Secret {HUB_CONFIG_SECRET} does not contain the reviewed adapter config; "
            "no changes made"
        )


def validate_exception_secret(secret: dict) -> None:
    data = decoded_secret_data(secret, EXCEPTION_SECRET)
    if not {"settings.json", "grant-record.json"}.issubset(data):
        raise Refusal(f"Secret {EXCEPTION_SECRET} is missing required keys; no changes made")
    try:
        settings = json.loads(data["settings.json"])
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Refusal(f"Secret {EXCEPTION_SECRET} has invalid settings; no changes made") from None
    expected = {
        "enabled": True,
        "username": "m12113877",
        "image": (
            "harbor.dshl.unileoben.ac.at/cps-users/cps-jupyter-notebook@sha256:"
            "1ed46addaed50f1874edec98001a122bd9da219d89e6cfecf1945c7338261c21"
        ),
        "namespace": NAMESPACE,
        "home_pvc": "claim-m12113877",
        "home_mount_path": "/home/jovyan",
        "runtime_class_name": "nvidia",
        "node_selector": {"kubernetes.io/hostname": "k3s-wk-gpu1"},
    }
    if not isinstance(settings, dict) or set(settings) != set(expected) | {"grant_id"}:
        raise Refusal(f"Secret {EXCEPTION_SECRET} has an unexpected settings schema; no changes made")
    if any(settings.get(key) != value for key, value in expected.items()):
        raise Refusal(f"Secret {EXCEPTION_SECRET} does not match the reviewed scope; no changes made")
    grant_id = settings.get("grant_id")
    try:
        if str(uuid.UUID(grant_id)) != grant_id:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise Refusal(f"Secret {EXCEPTION_SECRET} has no canonical grant UUID; no changes made") from None


def validate_priority_class(priority_class: dict) -> None:
    spec = priority_class.get("value")
    preemption = priority_class.get("preemptionPolicy", "PreemptLowerPriority")
    if spec != 60 or preemption != "Never" or priority_class.get("globalDefault", False):
        raise Refusal(
            f"PriorityClass {PRIORITY_CLASS} is not value 60 / Never / non-default; "
            "no changes made"
        )


def one_named(items: list[dict], name: str, what: str) -> tuple[int, dict] | None:
    matches = [(index, item) for index, item in enumerate(items) if item.get("name") == name]
    if len(matches) > 1:
        raise Refusal(f"Deployment has duplicate {what} named {name}; no changes made")
    return matches[0] if matches else None


def make_patch(deployment: dict) -> list[dict]:
    metadata = deployment.get("metadata", {})
    if not metadata.get("uid") or not metadata.get("resourceVersion"):
        raise Refusal("Deployment lacks UID/resourceVersion compare-and-swap fields; no changes made")
    pod = deployment.get("spec", {}).get("template", {}).get("spec", {})
    containers = pod.get("containers", [])
    hub = one_named(containers, "hub", "container")
    if hub is None:
        raise Refusal("Deployment has no Hub container; no changes made")
    container_index, container = hub

    volumes = pod.get("volumes", [])
    config_volume = one_named(volumes, "secret", "volume")
    if config_volume is None:
        raise Refusal("Deployment has no chart Hub config volume named secret; no changes made")
    config_index, config = config_volume
    config_secret = config.get("secret", {}).get("secretName")
    if not config_secret:
        raise Refusal("Hub config volume is not a Secret volume; no changes made")

    mounts = container.get("volumeMounts", [])
    if one_named(mounts, "secret", "Hub mount") is None:
        raise Refusal("Hub has no mount for its chart config volume; no changes made")

    patch = [
        {"op": "test", "path": "/metadata/uid", "value": metadata.get("uid")},
        {
            "op": "test",
            "path": "/metadata/resourceVersion",
            "value": metadata.get("resourceVersion"),
        },
        {
            "op": "test",
            "path": f"/spec/template/spec/containers/{container_index}/image",
            "value": container.get("image"),
        },
        {
            "op": "test",
            "path": f"/spec/template/spec/volumes/{config_index}/secret/secretName",
            "value": config_secret,
        },
        {
            "op": "replace",
            "path": f"/spec/template/spec/containers/{container_index}/image",
            "value": HUB_IMAGE,
        },
        {
            "op": "replace",
            "path": f"/spec/template/spec/volumes/{config_index}/secret/secretName",
            "value": HUB_CONFIG_SECRET,
        },
    ]

    exception_volume = one_named(volumes, "cps-personal-exclusive", "volume")
    if exception_volume is None:
        patch.append(
            {
                "op": "add",
                "path": "/spec/template/spec/volumes/-",
                "value": {
                    "name": "cps-personal-exclusive",
                    "secret": {"secretName": EXCEPTION_SECRET},
                },
            }
        )
    else:
        index, volume = exception_volume
        if "secret" not in volume:
            raise Refusal("Personal exception volume is not a Secret; no changes made")
        patch.extend(
            [
                {
                    "op": "test",
                    "path": f"/spec/template/spec/volumes/{index}/secret/secretName",
                    "value": volume["secret"].get("secretName"),
                },
                {
                    "op": "replace",
                    "path": f"/spec/template/spec/volumes/{index}/secret/secretName",
                    "value": EXCEPTION_SECRET,
                },
            ]
        )

    personal_mount = one_named(mounts, "cps-personal-exclusive", "Hub mount")
    if personal_mount is None:
        patch.append(
            {
                "op": "add",
                "path": f"/spec/template/spec/containers/{container_index}/volumeMounts/-",
                "value": {
                    "name": "cps-personal-exclusive",
                    "mountPath": EXCEPTION_MOUNT,
                    "readOnly": True,
                },
            }
        )
    else:
        index, mount = personal_mount
        if mount.get("mountPath") != EXCEPTION_MOUNT or mount.get("subPath"):
            raise Refusal("Personal exception mount differs from the reviewed path; no changes made")
        if mount.get("readOnly") is not True:
            patch.append(
                {
                    "op": "replace",
                    "path": f"/spec/template/spec/containers/{container_index}/volumeMounts/{index}/readOnly",
                    "value": True,
                }
            )
    return patch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, help="kubectl context to target")
    parser.add_argument(
        "--expect-current-image",
        required=True,
        help="exact Hub image observed in the current Deployment",
    )
    parser.add_argument(
        "--expect-current-config-secret",
        required=True,
        help="exact Secret name in the current chart config volume",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply after preflight (without this flag the script is read-only)",
    )
    args = parser.parse_args()

    try:
        hub_secret = get_json(args.context, "secret", HUB_CONFIG_SECRET)
        validate_config_secret(hub_secret)
        exception_secret = get_json(args.context, "secret", EXCEPTION_SECRET)
        validate_exception_secret(exception_secret)
        priority_class = json.loads(
            kubectl(args.context, "get", "priorityclass", PRIORITY_CLASS, "-o", "json")
        )
        validate_priority_class(priority_class)
        deployment = get_json(args.context, "deployment", DEPLOYMENT)
        if deployment.get("metadata", {}).get("namespace") != NAMESPACE:
            raise Refusal("Deployment namespace mismatch; no changes made")
        pod = deployment.get("spec", {}).get("template", {}).get("spec", {})
        hub_match = one_named(pod.get("containers", []), "hub", "container")
        config_match = one_named(pod.get("volumes", []), "secret", "volume")
        if hub_match is None or hub_match[1].get("image") != args.expect_current_image:
            raise Refusal("Current Hub image differs from the supplied precondition; no changes made")
        if (
            config_match is None
            or config_match[1].get("secret", {}).get("secretName")
            != args.expect_current_config_secret
        ):
            raise Refusal("Current config Secret differs from the supplied precondition; no changes made")
        patch = make_patch(deployment)
        if not args.apply:
            print(
                "Preflight passed: reviewed Hub config and exception Secret are present; "
                "deployment patch is ready. No changes made."
            )
            return 0
        kubectl(
            args.context,
            "-n",
            NAMESPACE,
            "patch",
            "deployment",
            DEPLOYMENT,
            "--type=json",
            "-p",
            json.dumps(patch, separators=(",", ":")),
            "-o",
            "name",
        )
        print(
            "Applied CAS patch to Hub image and personal exception Secret refs; "
            "all other Deployment fields were preserved."
        )
        return 0
    except (Refusal, UnicodeDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
