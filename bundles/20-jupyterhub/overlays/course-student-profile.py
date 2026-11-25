import copy

from jupyterhub.handlers.base import BaseHandler
from jupyterhub.utils import url_path_join

from cps_compute.personal_fraction import SLUG as _course_fraction_slug
from cps_compute.personal_gpu import CIT_ADMIN_MUJOCO as _course_admin_slug
from cps_compute_hub.personal_exclusive import SLUG as _course_reviewed_slug, USERNAME as _course_reviewed_user
from cps_compute_hub.personal_gpu import cit_bridge as _course_cit_bridge

_course_previous_profiles = c.KubeSpawner.profile_list
_course_previous_pre = c.KubeSpawner.pre_spawn_hook
_course_memory_sizes = ('2', '5')
_course_default_memory = '2'
_course_session_hours = 24
_course_shared_slug = 'gpu-shared-lecture'
_course_help_route = '/notebook-help'

_course_help_template = """{% extends "page.html" %}
{% block main %}
<main class="container py-4" style="max-width: 960px">
  <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
    <h1 class="h3 mb-0">CIT notebook help</h1>
    <a href="{{ spawn_url }}">Server Options</a>
  </div>
  <section class="border rounded-3 p-3 mb-3" aria-labelledby="choose-profile">
    <h2 class="h5" id="choose-profile">Choose a profile</h2>
    <dl class="mb-0">
      <dt>CPU Small</dt>
      <dd>Start here for Python exercises, data analysis, and notebooks that do not require CUDA.</dd>
      <dt>GPU Shared, 2 or 5 GiB</dt>
      <dd>Use 2 GiB for small CUDA exercises. Select 5 GiB when the course asks for it or your
          model needs more memory. TensorFlow 2.20.0 is the default. Select PyTorch when your course
          requires it. Both frameworks have a 24-hour session limit. CIT also checks for idle
          servers every five minutes and stops them after 24 hours of inactivity.</dd>
      <dt>Research and administrator profiles</dt>
      <dd>These sections show the additional options available to your account. Full-device
          profiles request one or two A100s and depend on current capacity.</dd>
    </dl>
  </section>
  <section class="border rounded-3 p-3 mb-3" aria-labelledby="check-gpu">
    <h2 class="h5" id="check-gpu">Check GPU access in your notebook</h2>
    <p>Run <code>nvidia-smi</code> in a JupyterLab terminal, or use the check for your framework
       in a Python cell. A shared profile uses the memory allowance selected in Server Options.</p>
    <h3 class="h6">PyTorch</h3>
    <pre class="bg-body-tertiary rounded p-3"><code>import torch
print(torch.cuda.is_available())</code></pre>
    <h3 class="h6">TensorFlow</h3>
    <pre class="bg-body-tertiary rounded p-3 mb-0"><code>import tensorflow as tf
print(tf.config.list_physical_devices("GPU"))</code></pre>
  </section>
  <section class="border rounded-3 p-3 mb-3" aria-labelledby="finish-session">
    <h2 class="h5" id="finish-session">Save your work and release the GPU</h2>
    <p class="mb-0">Save files in your home directory. Open <strong>File → Hub Control Panel</strong>
       in JupyterLab and select <strong>Stop My Server</strong>. Closing the browser tab leaves
       the server running. Your home files are kept when your server stops.</p>
  </section>
  <section class="border rounded-3 p-3 mb-3" aria-labelledby="get-help">
    <h2 class="h5" id="get-help">Get help with sign-in or startup</h2>
    <ul class="mb-0">
      <li>Choose <strong>CIT</strong> at sign-in and use your federated university account.</li>
      <li>If startup fails, open the spawn <strong>Event log</strong> for the exact error.</li>
      <li>Send course staff the profile, GPU memory and framework you selected, the time of
          the attempt, and the error text. Keep tokens and passwords out of reports.</li>
    </ul>
  </section>
  <section class="border rounded-3 p-3" aria-labelledby="official-resources">
    <h2 class="h5" id="official-resources">Official documentation</h2>
    <ul class="mb-0">
      <li><a href="https://docs.jupyter.org/en/latest/">Project Jupyter documentation</a></li>
      <li><a href="https://jupyterlab.readthedocs.io/en/stable/user/interface.html">JupyterLab interface guide</a></li>
      <li><a href="https://jupyterhub.readthedocs.io/en/stable/">JupyterHub documentation</a></li>
    </ul>
  </section>
</main>
{% endblock main %}
"""

class _CourseNotebookHelp(BaseHandler):
    def get_template(self, name, sync=False):
        if name != "cit-notebook-help":
            return super().get_template(name, sync=sync)
        env = self.settings["jinja2_env_sync" if sync else "jinja2_env"]
        return env.from_string(_course_help_template)

    async def get(self):
        self.finish(await self.render_template(
            "cit-notebook-help", spawn_url=url_path_join(self.hub.base_url, "spawn"),
        ))

_course_form_template = """{% set slugs = profile_list | map(attribute='slug') | list %}
{% if user_options and user_options.cit_shared_lecture and 'gpu-shared-lecture' in slugs %}
{% set user_options = dict(user_options, profile='gpu-shared-lecture') %}
{% endif %}
{% if user_options and user_options.profile not in slugs %}
{% set user_options = {} %}
{% endif %}
{% if profile_list and profile_list[0].cit_access is defined %}
  <div id="cit-profile-context" data-access="{{ profile_list[0].cit_access | e }}"
       data-shared="{{ profile_list[1].slug | e }}" hidden>
    {% for profile in profile_list %}
      {% if profile.cit_section and loop.changed(profile.cit_section) %}
      <span data-profile="{{ profile.slug | e }}" data-section="{{ profile.cit_section | e }}"></span>
      {% endif %}
    {% endfor %}
  </div>
{% endif %}
{% include 'form.html' %}
"""


async def _course_groups(spawner):
    state = await spawner.user.get_auth_state()
    return set((state or {}).get("oauth_user", {}).get("groups", []) or [])

async def _course_standard_user(spawner):
    return not (await _course_groups(spawner)).intersection({"jhub-admins", "jhub-powerusers"})

def _course_tensorflow_enabled(spawner):
    bridge = _course_cit_bridge(spawner)
    return bool(bridge is not None and (bridge.fraction_config or {}).get("tensorflowImage"))

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
    groups = await _course_groups(spawner)
    access = "Student"
    if "jhub-admins" in groups:
        access = "Administrator"
    elif "jhub-powerusers" in groups:
        access = "Power user"
    standard = access == "Student"
    memory = fixed["profile_options"]["gpu_memory_gib"]
    memory["choices"] = {
        size: {**memory["choices"][size], "default": size == _course_default_memory}
        for size in _course_memory_sizes
    }
    fixed["profile_options"] = {"gpu_memory_gib": memory}
    framework_description = "PyTorch"
    if _course_tensorflow_enabled(spawner):
        fixed["profile_options"]["gpu_framework"] = {
            "display_name": "Framework",
            "choices": {
                "tensorflow": {"display_name": "TensorFlow 2.20.0", "default": True},
                "pytorch": {"display_name": "PyTorch"},
            },
        }
        framework_description = "TensorFlow 2.20.0 (default) or PyTorch"
    fixed["kubespawner_override"].setdefault("extra_pod_config", {})["activeDeadlineSeconds"] = (
        _course_session_hours * 3600
    )
    fixed.update(display_name="GPU Shared (2 or 5 GiB)", default=not standard, cit_section="Student profiles",
                 description=f"Choose 2 or 5 GiB of shared A100 VRAM with {framework_description}. {_course_session_hours}-hour session.")
    cpu = [
        {**row, "default": standard, "cit_section": "Student profiles", "cit_access": access}
        for row in rows if row.get("slug") == "cpu-small"
    ]
    assigned = []
    if spawner.user.name == _course_reviewed_user and not spawner.name:
        assigned = [
            {**row, "default": False, "cit_section": "Assigned profiles"}
            for row in rows if row.get("slug") == _course_reviewed_slug
        ]
    if standard:
        return cpu + [fixed] + assigned

    fixed["slug"] = _course_shared_slug
    elevated = [
        {**row, "default": False, "cit_section": "Research and power-user profiles"}
        for row in rows if row.get("slug") not in {"cpu-small", _course_admin_slug, _course_reviewed_slug}
    ]
    admin = [
        {**row, "default": False, "cit_section": "Administrator-only profiles"}
        for row in rows if row.get("slug") == _course_admin_slug
    ]
    return cpu + [fixed] + elevated + admin + assigned

async def _course_pre(spawner):
    options = spawner.user_options
    slug = options.get("profile")
    if slug == _course_shared_slug:
        rows = await _course_previous_profiles(spawner)
        if not any(row.get("slug") == _course_fraction_slug for row in rows):
            raise ValueError("A shared GPU profile is unavailable for this server")
    if slug == _course_shared_slug or (
        slug == _course_fraction_slug
        and (options.get("cit_shared_lecture") is True or await _course_standard_user(spawner))
    ):
        memory = options.get("gpu_memory_gib")
        options = {
            **options,
            "profile": _course_fraction_slug,
            "gpu_memory_gib": memory if memory in _course_memory_sizes else _course_default_memory,
            "session_duration_hours": str(_course_session_hours),
            "gpu_framework": options.get(
                "gpu_framework", "tensorflow" if _course_tensorflow_enabled(spawner) else "pytorch",
            ),
            "cit_shared_lecture": True,
        }
        spawner.user_options = options
        # The gateway compares the pending Hub server model to the reservation.
        orm_spawner = getattr(spawner, "orm_spawner", None)
        if orm_spawner is not None:
            orm_spawner.user_options = options
    return await _course_previous_pre(spawner)

c.KubeSpawner.profile_list = _course_profiles
c.KubeSpawner.profile_form_template = _course_form_template
c.KubeSpawner.pre_spawn_hook = c.Spawner.pre_spawn_hook = _course_pre
_course_handlers = [row for row in c.JupyterHub.get("extra_handlers", []) if row[0] != _course_help_route]
c.JupyterHub.extra_handlers = [*_course_handlers, (_course_help_route, _CourseNotebookHelp)]
