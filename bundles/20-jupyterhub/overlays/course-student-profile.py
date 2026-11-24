
import copy

from cps_compute.personal_fraction import SLUG as _course_fraction_slug
from cps_compute_hub.personal_exclusive import SLUG as _course_reviewed_slug, USERNAME as _course_reviewed_user

_course_previous_profiles = c.KubeSpawner.profile_list
_course_previous_pre = c.KubeSpawner.pre_spawn_hook
_course_memory_sizes = ('2', '5')
_course_default_memory = '5'
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
    fixed = copy.deepcopy(rows[fraction_index])
    memory = fixed["profile_options"]["gpu_memory_gib"]
    memory["choices"] = {
        size: {**memory["choices"][size], "default": size == _course_default_memory}
        for size in _course_memory_sizes
    }
    fixed["profile_options"] = {"gpu_memory_gib": memory}
    fixed.update(display_name="GPU Shared (2 or 5 GiB)",
                 description="Choose 2 or 5 GiB of shared A100 VRAM with PyTorch. Two-hour session.")
    if not await _course_standard_user(spawner):
        fixed.update(slug=_course_shared_slug, default=False)
        return [*rows[:fraction_index], fixed, *rows[fraction_index:]]
    reviewed = []
    if spawner.user.name == _course_reviewed_user and not spawner.name:
        reviewed = [row for row in rows if row.get("slug") == _course_reviewed_slug]
    return [row for row in rows if row.get("slug") == "cpu-small"] + [fixed] + reviewed

async def _course_pre(spawner):
    options = spawner.user_options
    slug = options.get("profile")
    if slug == _course_shared_slug:
        rows = await _course_previous_profiles(spawner)
        if not any(row.get("slug") == _course_fraction_slug for row in rows):
            raise ValueError("A shared GPU profile is unavailable for this server")
    if slug == _course_shared_slug or (slug == _course_fraction_slug and await _course_standard_user(spawner)):
        memory = options.get("gpu_memory_gib")
        options = {
            **options,
            "profile": _course_fraction_slug,
            "gpu_memory_gib": memory if memory in _course_memory_sizes else _course_default_memory,
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

