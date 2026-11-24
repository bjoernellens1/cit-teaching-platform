
import copy

from cps_compute.personal_fraction import SLUG as _course_fraction_slug
from cps_compute_hub.personal_exclusive import SLUG as _course_reviewed_slug, USERNAME as _course_reviewed_user

_course_previous_profiles = c.KubeSpawner.profile_list
_course_previous_pre = c.KubeSpawner.pre_spawn_hook
_course_memory_sizes = ('2', '5')
_course_default_memory = '5'

async def _course_standard_user(spawner):
    state = await spawner.user.get_auth_state()
    groups = set((state or {}).get("oauth_user", {}).get("groups", []))
    return not groups.intersection({"jhub-admins", "jhub-powerusers"})

async def _course_profiles(spawner):
    rows = await _course_previous_profiles(spawner)
    slugs = {row.get("slug") for row in rows}
    if not {"cpu-small", _course_fraction_slug}.issubset(slugs) or not await _course_standard_user(spawner):
        return rows
    fixed = copy.deepcopy(next(row for row in rows if row.get("slug") == _course_fraction_slug))
    memory = fixed["profile_options"]["gpu_memory_gib"]
    memory["choices"] = {
        size: {**memory["choices"][size], "default": size == _course_default_memory}
        for size in _course_memory_sizes
    }
    fixed["profile_options"] = {"gpu_memory_gib": memory}
    fixed.update(display_name="GPU Shared (2 or 5 GiB)",
                 description="Choose 2 or 5 GiB of shared A100 VRAM with PyTorch. Two-hour session.")
    reviewed = []
    if spawner.user.name == _course_reviewed_user and not spawner.name:
        reviewed = [row for row in rows if row.get("slug") == _course_reviewed_slug]
    return [row for row in rows if row.get("slug") == "cpu-small"] + [fixed] + reviewed

async def _course_pre(spawner):
    options = spawner.user_options
    if options.get("profile") == _course_fraction_slug and await _course_standard_user(spawner):
        memory = options.get("gpu_memory_gib")
        options["gpu_memory_gib"] = memory if memory in _course_memory_sizes else _course_default_memory
        options["session_duration_hours"] = "2"
    return await _course_previous_pre(spawner)

c.KubeSpawner.profile_list = _course_profiles
c.KubeSpawner.pre_spawn_hook = c.Spawner.pre_spawn_hook = _course_pre

