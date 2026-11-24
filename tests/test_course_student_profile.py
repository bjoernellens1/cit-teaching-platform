import asyncio
from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import patch

import pytest
from traitlets.config import Config


HOOK = Path(__file__).parents[1] / "bundles/20-jupyterhub/overlays/course-student-profile.py"
FRACTION = "gpu-mujoco-xpra"
SHARED = "gpu-shared-lecture"
PROFILES = [
    {"slug": "cpu-small"},
    {"slug": "gpu-large-pytorch"},
    {"slug": "gpu-mujoco-admin"},
    {"slug": "mujoco-desktop-exclusive"},
    {"slug": FRACTION, "profile_options": {
        "gpu_memory_gib": {"choices": {str(i): {"display_name": f"{i} GiB", "default": i == 1}
                                       for i in range(1, 21)}},
        "session_duration_hours": {"choices": {"2": {}, "4": {}}},
    }},
]


async def original_profiles(spawner):
    groups = set((await spawner.user.get_auth_state())["oauth_user"]["groups"])
    return [row for row in PROFILES if
            (row["slug"] != "gpu-mujoco-admin" or "jhub-admins" in groups)
            and (row["slug"] != "mujoco-desktop-exclusive"
                 or spawner.user.name == "reviewed-user" and not spawner.name)]


async def original_pre(spawner):
    return dict(spawner.user_options)


def load_hook(tensorflow_enabled=False):
    container = SimpleNamespace(KubeSpawner=SimpleNamespace(profile_list=original_profiles,
                                pre_spawn_hook=original_pre), Spawner=SimpleNamespace(), JupyterHub=Config())
    modules = {
        "jupyterhub.handlers.base": SimpleNamespace(BaseHandler=object),
        "jupyterhub.utils": SimpleNamespace(url_path_join=lambda base, path: base.rstrip("/") + "/" + path.lstrip("/")),
        "cps_compute.personal_fraction": SimpleNamespace(SLUG=FRACTION),
        "cps_compute.personal_gpu": SimpleNamespace(CIT_ADMIN_MUJOCO="gpu-mujoco-admin"),
        "cps_compute_hub.personal_gpu": SimpleNamespace(
            cit_bridge=lambda spawner: SimpleNamespace(fraction_config={"tensorflowImage": "qualified"}) if tensorflow_enabled else None,
        ),
        "cps_compute_hub.personal_exclusive": SimpleNamespace(SLUG="mujoco-desktop-exclusive", USERNAME="reviewed-user"),
    }
    with patch.dict(sys.modules, modules):
        exec(compile(HOOK.read_text(), str(HOOK), "exec"), {"c": container})
    return container


def spawner(owner="student", groups=(), name="", **options):
    async def get_state():
        return {"oauth_user": {"groups": list(groups)}}
    user = SimpleNamespace(name=owner, get_auth_state=get_state)
    return SimpleNamespace(user=user, name=name, user_options=options, hub=SimpleNamespace(base_url="/hub/"))


def test_student_menu_has_only_two_shared_sizes_and_cpu():
    hooks = load_hook()
    rows = asyncio.run(hooks.KubeSpawner.profile_list(spawner()))
    assert [row["slug"] for row in rows] == ["cpu-small", FRACTION]
    assert rows[0]["cit_access"] == "Student"
    choices = rows[1]["profile_options"]["gpu_memory_gib"]["choices"]
    assert rows[1]["kubespawner_override"]["image_pull_secrets"] == ["harbor-cps-users-pull"]
    assert set(choices) == {"2", "5"}
    assert choices["2"]["default"] and not choices["5"]["default"]
    assert rows[0]["default"] and not rows[1]["default"]
    assert "session_duration_hours" not in rows[1]["profile_options"]
    assert len(PROFILES[-1]["profile_options"]["gpu_memory_gib"]["choices"]) == 20


def test_student_choices_use_canonical_fraction_with_two_hour_limit():
    hook = load_hook().KubeSpawner.pre_spawn_hook
    for requested, expected in (("2", "2"), ("5", "5"), ("20", "2"), (None, "2"), (["2"], "2")):
        result = asyncio.run(hook(spawner(profile=FRACTION, gpu_memory_gib=requested, session_duration_hours="24")))
        assert result["profile"] == FRACTION
        assert result["gpu_memory_gib"] == expected
        assert result["session_duration_hours"] == "2"


def test_poweruser_and_admin_keep_original_profiles_and_see_the_shared_choice():
    hooks = load_hook()
    for group in ("jhub-admins", "jhub-powerusers"):
        elevated = spawner(groups=(group,), profile=FRACTION, gpu_memory_gib="20", session_duration_hours="24")
        rows = asyncio.run(hooks.KubeSpawner.profile_list(elevated))
        original = asyncio.run(original_profiles(elevated))
        assert {row["slug"] for row in rows} == {row["slug"] for row in original} | {SHARED}
        original_fraction, = [row for row in rows if row["slug"] == FRACTION]
        assert original_fraction["profile_options"] == PROFILES[-1]["profile_options"]
        assert original_fraction["kubespawner_override"]["image_pull_secrets"] == ["harbor-cps-users-pull"]
        matches = [row for row in rows if row["slug"] == SHARED]
        assert len(matches) == 1
        assert matches[0]["kubespawner_override"]["image_pull_secrets"] == ["harbor-cps-users-pull"]
        assert matches[0]["display_name"] == "GPU Shared (2 or 5 GiB)"
        assert matches[0]["default"]
        assert matches[0]["profile_options"]["gpu_memory_gib"]["choices"]["2"]["default"]
        assert set(matches[0]["profile_options"]["gpu_memory_gib"]["choices"]) == {"2", "5"}
        assert asyncio.run(hooks.KubeSpawner.pre_spawn_hook(elevated)) == elevated.user_options


def test_elevated_shared_selection_is_persisted_under_the_canonical_profile():
    hook = load_hook().KubeSpawner.pre_spawn_hook
    for selected, expected in (("2", "2"), ("5", "5"), ("20", "2"), (None, "2")):
        s = spawner(groups=("jhub-admins",), profile=SHARED, gpu_memory_gib=selected,
                    session_duration_hours="24")
        s.orm_spawner = SimpleNamespace(user_options=dict(s.user_options))
        result = asyncio.run(hook(s))
        assert result == {"profile": FRACTION, "gpu_memory_gib": expected, "session_duration_hours": "2"}
        assert s.orm_spawner.user_options == result


def test_reviewed_dedicated_profile_is_kept_only_on_the_default_server():
    hook = load_hook().KubeSpawner.profile_list
    reviewed = asyncio.run(hook(spawner(owner="reviewed-user")))
    named = asyncio.run(hook(spawner(owner="reviewed-user", name="named")))
    assert reviewed[-1]["slug"] == "mujoco-desktop-exclusive"
    assert all(row["slug"] != "mujoco-desktop-exclusive" for row in named)



def test_framework_selector_is_available_on_the_course_choice_for_all_roles_when_enabled():
    for group in (None, "jhub-admins", "jhub-powerusers"):
        session = spawner(groups=(group,) if group else ())
        enabled = asyncio.run(load_hook(tensorflow_enabled=True).KubeSpawner.profile_list(session))
        shared, = [r for r in enabled if r.get("display_name") == "GPU Shared (2 or 5 GiB)"]
        choices = shared["profile_options"]["gpu_framework"]["choices"]
        assert set(choices) == {"pytorch", "tensorflow"}
        assert choices["pytorch"]["default"] is True
        assert choices["tensorflow"]["display_name"] == "TensorFlow 2.20.0"
        if group:
            full_menu, = [r for r in enabled if r.get("slug") == FRACTION]
            assert "gpu_framework" not in full_menu["profile_options"]

    disabled = asyncio.run(load_hook().KubeSpawner.profile_list(spawner()))
    assert "gpu_framework" not in disabled[-1]["profile_options"]



@pytest.mark.parametrize("login", ["m0000000", "p0000000"])
def test_student_choices_are_the_first_section_for_admin_accounts(login):
    profile_list = load_hook(tensorflow_enabled=True).KubeSpawner.profile_list
    student = asyncio.run(profile_list(spawner(owner=login)))
    administrator = asyncio.run(profile_list(spawner(owner=login, groups=("jhub-admins",))))
    assert [row["slug"] for row in administrator[:2]] == ["cpu-small", SHARED]
    assert administrator[0]["cit_access"] == "Administrator"
    assert [row["cit_section"] for row in administrator] == [
        "Student profiles", "Student profiles", "Research and power-user profiles",
        "Research and power-user profiles", "Administrator-only profiles",
    ]
    assert student[1]["profile_options"] == administrator[1]["profile_options"]
    assert [row["default"] for row in administrator].count(True) == 1
    assert administrator[-1]["slug"] == "gpu-mujoco-admin"


def test_poweruser_has_student_and_research_sections_without_admin_only_choices():
    profile_list = load_hook().KubeSpawner.profile_list
    rows = asyncio.run(profile_list(spawner(groups=("jhub-powerusers",))))
    assert rows[0]["cit_access"] == "Power user"
    assert set(row["cit_section"] for row in rows) == {
        "Student profiles", "Research and power-user profiles",
    }
    assert not any(row["slug"] == "gpu-mujoco-admin" for row in rows)
