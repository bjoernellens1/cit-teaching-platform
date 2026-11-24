import asyncio
from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import patch


HOOK = Path(__file__).parents[1] / "bundles/20-jupyterhub/overlays/course-student-profile.py"
FRACTION = "gpu-mujoco-xpra"
PROFILES = [
    {"slug": "cpu-small"},
    {"slug": "gpu-large-pytorch"},
    {"slug": "mujoco-desktop-exclusive"},
    {"slug": FRACTION, "profile_options": {
        "gpu_memory_gib": {"choices": {str(i): {"display_name": f"{i} GiB", "default": i == 1}
                                       for i in range(1, 21)}},
        "session_duration_hours": {"choices": {"2": {}, "4": {}}},
    }},
]


async def original_profiles(spawner):
    return PROFILES


async def original_pre(spawner):
    return dict(spawner.user_options)


def load_hook():
    container = SimpleNamespace(KubeSpawner=SimpleNamespace(profile_list=original_profiles,
                                pre_spawn_hook=original_pre), Spawner=SimpleNamespace())
    modules = {
        "cps_compute.personal_fraction": SimpleNamespace(SLUG=FRACTION),
        "cps_compute_hub.personal_exclusive": SimpleNamespace(SLUG="mujoco-desktop-exclusive", USERNAME="reviewed-user"),
    }
    with patch.dict(sys.modules, modules):
        exec(compile(HOOK.read_text(), str(HOOK), "exec"), {"c": container})
    return container


def spawner(owner="student", groups=(), name="", **options):
    async def get_state():
        return {"oauth_user": {"groups": list(groups)}}
    user = SimpleNamespace(name=owner, get_auth_state=get_state)
    return SimpleNamespace(user=user, name=name, user_options=options)


def test_student_menu_has_only_two_shared_sizes_and_cpu():
    hooks = load_hook()
    rows = asyncio.run(hooks.KubeSpawner.profile_list(spawner()))
    assert [row["slug"] for row in rows] == ["cpu-small", FRACTION]
    choices = rows[1]["profile_options"]["gpu_memory_gib"]["choices"]
    assert set(choices) == {"2", "5"}
    assert choices["5"]["default"] and not choices["2"]["default"]
    assert "session_duration_hours" not in rows[1]["profile_options"]
    assert len(PROFILES[-1]["profile_options"]["gpu_memory_gib"]["choices"]) == 20


def test_student_choices_use_canonical_fraction_with_two_hour_limit():
    hook = load_hook().KubeSpawner.pre_spawn_hook
    for requested, expected in (("2", "2"), ("5", "5"), ("20", "5"), (None, "5"), (["2"], "5")):
        result = asyncio.run(hook(spawner(profile=FRACTION, gpu_memory_gib=requested, session_duration_hours="24")))
        assert result["profile"] == FRACTION
        assert result["gpu_memory_gib"] == expected
        assert result["session_duration_hours"] == "2"


def test_poweruser_and_admin_profiles_are_unchanged():
    hooks = load_hook()
    for group in ("jhub-admins", "jhub-powerusers"):
        elevated = spawner(groups=(group,), profile=FRACTION, gpu_memory_gib="20", session_duration_hours="24")
        assert asyncio.run(hooks.KubeSpawner.profile_list(elevated)) == PROFILES
        assert asyncio.run(hooks.KubeSpawner.pre_spawn_hook(elevated)) == elevated.user_options


def test_reviewed_dedicated_profile_is_kept_only_on_the_default_server():
    hook = load_hook().KubeSpawner.profile_list
    reviewed = asyncio.run(hook(spawner(owner="reviewed-user")))
    named = asyncio.run(hook(spawner(owner="reviewed-user", name="named")))
    assert reviewed[-1]["slug"] == "mujoco-desktop-exclusive"
    assert all(row["slug"] != "mujoco-desktop-exclusive" for row in named)
