import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch


OVERLAY = Path(__file__).parents[1] / "bundles/20-jupyterhub/overlays/dedicated-profile-images.py"


def test_src_filtered_profiles_keep_the_bridge_images_through_every_load():
    slugs = ("gpu-large-pytorch", "gpu-large-tf", "gpu-xlarge-pytorch", "gpu-xlarge-tf")
    policy = {slug: {"image": f"notebook@sha256:{i:064x}"} for i, slug in enumerate(slugs, 1)}
    originals = [{"slug": slug, "kubespawner_override": {"image": "notebook:mutable", "cpu_limit": 24}} for slug in slugs]
    shared = {"slug": "gpu-mujoco-xpra"}
    cpu = {"slug": "cpu-small"}

    async def inherited(spawner):
        return [cpu, shared, *originals] if spawner.authorized else [cpu, shared]

    config = SimpleNamespace(KubeSpawner=SimpleNamespace(profile_list=inherited))
    bridge = SimpleNamespace(config={"profiles": policy})
    modules = {"cps_compute_hub.personal_gpu": SimpleNamespace(cit_bridge=lambda spawner: bridge)}
    with patch.dict(sys.modules, modules):
        exec(compile(OVERLAY.read_text(), str(OVERLAY), "exec"), {"c": config})
    loader = config.KubeSpawner.profile_list

    for _ in range(2):
        rows = asyncio.run(loader(SimpleNamespace(authorized=True)))
        assert rows[:2] == [cpu, shared]
        for row in rows[2:]:
            assert row["kubespawner_override"] == {"image": policy[row["slug"]]["image"], "cpu_limit": 24}
    assert all(row["kubespawner_override"]["image"] == "notebook:mutable" for row in originals)
    assert asyncio.run(loader(SimpleNamespace(authorized=False))) == [cpu, shared]


def test_private_dedicated_image_uses_the_scoped_harbor_pull_reference():
    profile = {"image": "harbor.dshl.unileoben.ac.at/cps-users/probe@sha256:" + 64 * "b"}
    row = {"slug": "gpu-mujoco-admin", "kubespawner_override": {"image": "legacy:tag"}}

    async def inherited(spawner):
        return [row]

    config = SimpleNamespace(KubeSpawner=SimpleNamespace(profile_list=inherited))
    bridge = SimpleNamespace(config={"profiles": {"gpu-mujoco-admin": profile}})
    modules = {"cps_compute_hub.personal_gpu": SimpleNamespace(cit_bridge=lambda spawner: bridge)}
    with patch.dict(sys.modules, modules):
        exec(compile(OVERLAY.read_text(), str(OVERLAY), "exec"), {"c": config})
    rows = asyncio.run(config.KubeSpawner.profile_list(SimpleNamespace()))
    assert rows[0]["kubespawner_override"] == {
        "image": profile["image"], "image_pull_secrets": ["harbor-cps-users-pull"],
    }
