
import copy

from cps_compute.personal_fraction import SLUG as _course_fraction_slug
from cps_compute_hub.personal_exclusive import SLUG as _course_reviewed_slug, USERNAME as _course_reviewed_user
from cps_compute_hub.personal_gpu import cit_bridge as _course_cit_bridge

_course_previous_profiles = c.KubeSpawner.profile_list
_course_previous_pre = c.KubeSpawner.pre_spawn_hook
_course_memory_sizes = ('2', '5')
_course_student_memory = '2'
_course_elevated_memory = '5'
_course_shared_slug = 'gpu-shared-lecture'

async def _course_standard_user(spawner):
    state = await spawner.user.get_auth_state()
    groups = set((state or {}).get("oauth_user", {}).get("groups", []))
    return not groups.intersection({"jhub-admins", "jhub-powerusers"})

async def _course_profiles(spawner):
    rows = await _course_previous_profiles(spawner)
    slugs = {row.get("slug") for row in rows}
    if not {"cpu-small", _course_fraction_slug}.issubset(slugs):
        return rows
    fraction_index, = (i for i, row in enumerate(rows) if row.get("slug") == _course_fraction_slug)
    rows = list(rows)
    rows[fraction_index] = copy.deepcopy(rows[fraction_index])
    overrides = rows[fraction_index].setdefault("kubespawner_override", {})
    overrides.setdefault("image_pull_secrets", ["harbor-cps-users-pull"])
    fixed = copy.deepcopy(rows[fraction_index])
    standard = await _course_standard_user(spawner)
    default_memory = _course_student_memory if standard else _course_elevated_memory
    memory = fixed["profile_options"]["gpu_memory_gib"]
    memory["choices"] = {
        size: {**memory["choices"][size], "default": size == default_memory}
        for size in _course_memory_sizes
    }
    fixed["profile_options"] = {"gpu_memory_gib": memory}
    framework_description = "PyTorch"
    bridge = _course_cit_bridge(spawner)
    if bridge is not None and (bridge.fraction_config or {}).get("tensorflowImage"):
        fixed["profile_options"]["gpu_framework"] = {
            "display_name": "Framework",
            "choices": {
                "pytorch": {"display_name": "PyTorch", "default": True},
                "tensorflow": {"display_name": "TensorFlow 2.20.0"},
            },
        }
        framework_description = "PyTorch or TensorFlow 2.20.0"
    fixed.update(display_name="GPU Shared (2 or 5 GiB)", default=standard,
                 description=f"Choose 2 or 5 GiB of shared A100 VRAM with {framework_description}. Two-hour session.")
    if not standard:
        fixed["slug"] = _course_shared_slug
        return [*rows[:fraction_index], fixed, *rows[fraction_index:]]
    reviewed = []
    if spawner.user.name == _course_reviewed_user and not spawner.name:
        reviewed = [row for row in rows if row.get("slug") == _course_reviewed_slug]
    cpu = [{**row, "default": False} for row in rows if row.get("slug") == "cpu-small"]
    return cpu + [fixed] + reviewed

async def _course_pre(spawner):
    options = spawner.user_options
    slug = options.get("profile")
    if slug == _course_shared_slug:
        rows = await _course_previous_profiles(spawner)
        if not any(row.get("slug") == _course_fraction_slug for row in rows):
            raise ValueError("A shared GPU profile is unavailable for this server")
    standard = slug in (_course_shared_slug, _course_fraction_slug) and await _course_standard_user(spawner)
    if slug == _course_shared_slug or (slug == _course_fraction_slug and standard):
        memory = options.get("gpu_memory_gib")
        default_memory = _course_student_memory if standard else _course_elevated_memory
        options = {
            **options,
            "profile": _course_fraction_slug,
            "gpu_memory_gib": memory if memory in _course_memory_sizes else default_memory,
            "session_duration_hours": "2",
        }
        spawner.user_options = options
        # The gateway compares the pending Hub server model to the reservation.
        orm_spawner = getattr(spawner, "orm_spawner", None)
        if orm_spawner is not None:
            orm_spawner.user_options = options
    return await _course_previous_pre(spawner)

c.KubeSpawner.profile_list = _course_profiles
c.KubeSpawner.pre_spawn_hook = c.Spawner.pre_spawn_hook = _course_pre

