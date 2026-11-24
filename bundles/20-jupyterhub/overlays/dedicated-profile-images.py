from cps_compute_hub.personal_gpu import cit_bridge

_dedicated_previous_profiles = c.KubeSpawner.profile_list


async def _dedicated_pinned_profiles(spawner):
    rows = await _dedicated_previous_profiles(spawner)
    bridge = cit_bridge(spawner)
    if bridge is None or bridge.config is None:
        return rows

    # KubeSpawner reloads the chosen profile after the Hub's pre-spawn hook.
    # Keep that reload on the same immutable image as the reservation policy.
    profiles = bridge.config["profiles"]
    result = []
    for row in rows:
        profile = profiles.get(row.get("slug"))
        if profile is not None:
            overrides = {**row.get("kubespawner_override", {}), "image": profile["image"]}
            row = {**row, "kubespawner_override": overrides}
        result.append(row)
    return result


c.KubeSpawner.profile_list = _dedicated_pinned_profiles
