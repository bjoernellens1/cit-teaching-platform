import base64
import copy
import json
import unittest

import apply_overlay as overlay


def secret(name, values):
    return {
        "metadata": {"name": name},
        "data": {
            key: base64.b64encode(value.encode()).decode()
            for key, value in values.items()
        },
    }


def config_secret(text=None):
    if text is None:
        text = "\n".join(
            (
                "  extraConfig:",
                "    zz-native-group-pilot:",
                "      from cps_compute_hub.native_pending_hub import install_pending_group_hub_configuration",
                "      from cps_compute_hub.personal_exclusive import PersonalExclusiveAdapter",
                "      install_pending_group_hub_configuration(c, pending, personal_exclusive=PersonalExclusiveAdapter.from_operator_config(settings))",
                "      Path('/etc/cps-native-kai-hub/config/settings.json')",
                "      Path('/etc/cps-personal-exclusive/settings.json')",
            )
        )
    return secret(overlay.HUB_CONFIG_SECRET, {"values.yaml": text})


def exception_secret(username="m12113877", include_grant=True):
    settings = {
        "enabled": True,
        "username": username,
        "image": (
            "harbor.dshl.unileoben.ac.at/cps-users/cps-jupyter-notebook@sha256:"
            "1ed46addaed50f1874edec98001a122bd9da219d89e6cfecf1945c7338261c21"
        ),
        "namespace": "cit-jhub",
        "home_pvc": "claim-m12113877",
        "home_mount_path": "/home/jovyan",
        "runtime_class_name": "nvidia",
        "node_selector": {"kubernetes.io/hostname": "k3s-wk-gpu1"},
    }
    if include_grant:
        settings["grant_id"] = "f0de4b78-f3d5-4be4-9131-b76ee54a2a54"
    return {
        "metadata": {"name": overlay.EXCEPTION_SECRET},
        "data": {
            "settings.json": base64.b64encode(json.dumps(settings).encode()).decode(),
            "grant-record.json": base64.b64encode(b"{} ").decode(),
        },
    }


def deployment(with_exception=False):
    volumes = [
        {"name": "secret", "secret": {"secretName": "chart-generated-secret"}},
        {"name": "native-proof", "configMap": {"name": "native-proof"}},
    ]
    mounts = [
        {"name": "secret", "mountPath": "/usr/local/etc/jupyterhub/secret"},
        {"name": "native-proof", "mountPath": "/etc/cps-native-proof/reference.json"},
    ]
    if with_exception:
        volumes.append(
            {"name": "cps-personal-exclusive", "secret": {"secretName": "old-exception"}}
        )
        mounts.append(
            {
                "name": "cps-personal-exclusive",
                "mountPath": overlay.EXCEPTION_MOUNT,
                "readOnly": True,
            }
        )
    return {
        "metadata": {
            "name": "hub",
            "namespace": overlay.NAMESPACE,
            "uid": "deployment-uid",
            "resourceVersion": "42",
        },
        "spec": {
            "template": {
                "metadata": {"annotations": {"native-proof": "preserve-me"}},
                "spec": {
                    "initContainers": [{"name": "native-proof-init", "image": "proof:v1"}],
                    "containers": [
                        {
                            "name": "hub",
                            "image": "current-hub:v1",
                            "volumeMounts": mounts,
                        }
                    ],
                    "volumes": volumes,
                },
            }
        },
    }


class OverlayValidationTests(unittest.TestCase):
    def test_config_requires_scoped_adapter_and_both_config_mounts(self):
        overlay.validate_config_secret(config_secret())

    def test_config_refuses_missing_adapter_call(self):
        text = "zz-native-group-pilot: /etc/cps-personal-exclusive/settings.json"
        with self.assertRaises(overlay.Refusal):
            overlay.validate_config_secret(config_secret(text))

    def test_exception_requires_exact_user_scope_and_grant(self):
        overlay.validate_exception_secret(exception_secret())
        with self.assertRaises(overlay.Refusal):
            overlay.validate_exception_secret(exception_secret(username="someone-else"))
        with self.assertRaises(overlay.Refusal):
            overlay.validate_exception_secret(exception_secret(include_grant=False))

    def test_priority_class_requires_nondefault_value_60_never(self):
        overlay.validate_priority_class(
            {"value": 60, "preemptionPolicy": "Never", "globalDefault": False}
        )
        for bad in (
            {"value": 59, "preemptionPolicy": "Never"},
            {"value": 60, "preemptionPolicy": "PreemptLowerPriority"},
            {"value": 60, "preemptionPolicy": "Never", "globalDefault": True},
        ):
            with self.subTest(bad=bad), self.assertRaises(overlay.Refusal):
                overlay.validate_priority_class(bad)

    def test_patch_has_uid_rv_cas_and_preserves_other_deployment_fields(self):
        current = deployment()
        before = copy.deepcopy(current)
        patch = overlay.make_patch(current)
        self.assertEqual(current, before)
        self.assertEqual(patch[0], {"op": "test", "path": "/metadata/uid", "value": "deployment-uid"})
        self.assertEqual(
            patch[1],
            {"op": "test", "path": "/metadata/resourceVersion", "value": "42"},
        )
        paths = {operation["path"] for operation in patch}
        self.assertTrue(all("native-proof" not in path for path in paths))
        self.assertNotIn("/spec/template/spec/initContainers", paths)
        self.assertNotIn("/spec/template/metadata/annotations", paths)
        self.assertIn(
            {"name": "native-proof", "configMap": {"name": "native-proof"}},
            current["spec"]["template"]["spec"]["volumes"],
        )

    def test_patch_repairs_only_exception_secret_reference_when_already_mounted(self):
        patch = overlay.make_patch(deployment(with_exception=True))
        paths = {operation["path"] for operation in patch}
        self.assertIn(
            "/spec/template/spec/volumes/2/secret/secretName",
            paths,
        )
        self.assertNotIn(
            "/spec/template/spec/containers/0/volumeMounts/-",
            paths,
        )

    def test_patch_refuses_missing_uid_or_resource_version(self):
        for field in ("uid", "resourceVersion"):
            current = deployment()
            del current["metadata"][field]
            with self.subTest(field=field), self.assertRaises(overlay.Refusal):
                overlay.make_patch(current)


if __name__ == "__main__":
    unittest.main()
