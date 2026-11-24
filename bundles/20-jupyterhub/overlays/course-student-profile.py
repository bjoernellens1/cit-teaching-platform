
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
_course_student_memory = '2'
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
          model needs more memory. The shared session limit is two hours. If a framework selector
          is visible, choose the image required by your course.</dd>
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
       the server running.</p>
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

_course_form_template = """{% if user_options and user_options.profile not in (profile_list | map(attribute='slug') | list) %}
{% set user_options = {} %}
{% endif %}
{% if profile_list and profile_list[0].cit_access is defined %}
{% set cpu = profile_list[0] %}
<style>
.cit-spawn-page > .row:first-child { display: none; }
.cit-spawn-page { margin-top: clamp(1rem, 4vw, 2.5rem); }
.cit-spawn-page > .row > .col-md-8 { width: min(100%, 960px); }
.cit-spawn { font-family: var(--bs-font-sans-serif, system-ui, sans-serif); }
.cit-spawn h1 { display: none; font-size: clamp(1.5rem, 3vw, 1.85rem); margin-bottom: .4rem; }
.cit-spawn-page .cit-spawn h1 { display: block; }
.cit-spawn h2 { font-size: 1rem; font-weight: 600; }
.cit-spawn .cit-meta { display: flex; align-items: baseline; justify-content: space-between;
  gap: .6rem 1rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.cit-spawn .cit-access { color: var(--bs-secondary-color, #535f6b); margin: 0; }
.cit-spawn .cit-card, .cit-spawn details { border: 1px solid var(--bs-border-color, #d8dee4); border-radius: .75rem; }
.cit-spawn .cit-card { display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: 1rem 1.25rem; box-shadow: 0 1px 3px rgb(0 0 0 / 7%); }
.cit-spawn .cit-card h2 { margin-bottom: .3rem; }
.cit-spawn .cit-card p { margin: 0; color: var(--bs-secondary-color, #535f6b); }
.cit-spawn .cit-card button { min-width: 7rem; border-radius: .4rem; }
.cit-spawn .cit-shared { border-left: 3px solid var(--bs-primary, #2573b8); border-radius: .25rem;
  padding: .7rem 1rem; margin: 1rem 0; background: var(--bs-tertiary-bg, #f5f6f7); }
.cit-spawn .cit-meta a, .cit-spawn .cit-shared a { color: var(--bs-link-color, #1769aa); }
.cit-spawn details > summary { padding: 1rem; font-weight: 600; cursor: pointer; }
.cit-spawn .cit-options { padding: 0 1rem 1rem; }
.cit-spawn .cit-section-heading { margin: 1.25rem 0 .6rem; }
.cit-spawn .cit-options .js-profile-label { border: 1px solid var(--bs-border-color, #d8dee4);
  border-radius: .55rem; margin: 0 0 .5rem; padding: .75rem; }
.cit-spawn .cit-options .js-profile-label:has(input[name=profile]:checked) {
  border-color: var(--bs-primary, #2573b8); background: var(--bs-primary-bg-subtle, #f2f7fc);
}
.cit-spawn .cit-options .js-profile-label h3 { font-size: 1.05rem; }
.cit-spawn .feedback-container { margin-top: 1rem; }
.cit-spawn :focus-visible { outline: 2px solid var(--bs-primary, #2573b8); outline-offset: 3px; }
@media (max-width: 575px) {
  .cit-spawn .cit-card { align-items: stretch; flex-direction: column; }
}
</style>
<div class="cit-spawn" id="cit-spawn">
  <h1>Start your personal server</h1>
  <div class="cit-meta">
    <p class="cit-access" id="cit-notebook-access">Notebook access <strong>{{ cpu.cit_access | e }}</strong></p>
    <a href="{{ cpu.cit_help_url | e }}">Notebook help</a>
  </div>
  <section class="cit-card" aria-labelledby="cit-quick-name">
    <div>
      <h2 id="cit-quick-name">{{ cpu.display_name | e }}</h2>
      <p>{{ cpu.description | e }}</p>
    </div>
    <button type="button" id="cit-start-cpu" class="btn btn-jupyter" aria-label="Start CPU Small" hidden>Start</button>
  </section>
  <div class="cit-shared">
    <strong>Need a GPU for your lecture?</strong><br>
    <a id="cit-open-shared" href="#profile-item-{{ profile_list[1].slug | e }}">Choose a shared GPU notebook with 2 or 5 GiB</a>
  </div>
  <details id="cit-profile-options" open>
    <summary>Change profile</summary>
    <div class="cit-options">
{% include 'form.html' %}
    </div>
  </details>
</div>
<script>
document.addEventListener("DOMContentLoaded", () => {
  const layout = document.getElementById("cit-spawn");
  const form = layout && layout.closest("form");
  if (!form) return;
  const container = form.closest(".container");
  if (container) container.classList.add("cit-spawn-page");
  const options = layout.querySelector("details");
  const footer = form.querySelector(".feedback-container");
  const submit = footer && footer.querySelector("button[type=submit]");
  const cpu = form.querySelector("#profile-item-cpu-small");
  const start = layout.querySelector("#cit-start-cpu");
  if (cpu && submit && form.requestSubmit) {
    const spacer = footer.previousElementSibling;
    if (spacer && spacer.tagName === "BR") spacer.remove();
    layout.querySelector(".cit-options").appendChild(footer);
    submit.textContent = "Start selected profile";
    options.open = Boolean(form.parentElement.querySelector(".spawn-error-msg"));
    start.hidden = false;
    start.addEventListener("click", () => {
      cpu.checked = true;
      form.requestSubmit(submit);
    });
  }
  layout.querySelector("#cit-open-shared").addEventListener("click", event => {
    const shared = document.getElementById(event.currentTarget.hash.slice(1));
    if (!shared) return;
    event.preventDefault();
    options.open = true;
    shared.focus({ preventScroll: true });
    shared.scrollIntoView({ block: "nearest" });
  });
  const sectionStarts = [
    {%- for profile in profile_list %}
    {%- if profile.cit_section and loop.changed(profile.cit_section) %}
    [{{ profile.slug | tojson }}, {{ profile.cit_section | tojson }}],
    {%- endif %}
    {%- endfor %}
  ];
  for (const [slug, title] of sectionStarts) {
    const option = document.getElementById('profile-item-' + slug);
    const row = option && option.closest('.js-profile-label');
    if (!row) continue;
    const heading = document.createElement('h2');
    heading.className = 'cit-section-heading';
    heading.textContent = title;
    row.before(heading);
  }
});
</script>
{% else %}
{% include 'form.html' %}
{% endif %}
"""

async def _course_groups(spawner):
    state = await spawner.user.get_auth_state()
    return set((state or {}).get("oauth_user", {}).get("groups", []) or [])

async def _course_standard_user(spawner):
    return not (await _course_groups(spawner)).intersection({"jhub-admins", "jhub-powerusers"})

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
        size: {**memory["choices"][size], "default": size == _course_student_memory}
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
    fixed.update(display_name="GPU Shared (2 or 5 GiB)", default=not standard, cit_section="Student profiles",
                 description=f"Choose 2 or 5 GiB of shared A100 VRAM with {framework_description}. Two-hour session.")
    cpu = [
        {**row, "default": standard, "cit_section": "Student profiles", "cit_access": access,
         "cit_help_url": url_path_join(spawner.hub.base_url, _course_help_route)}
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
    standard = slug in (_course_shared_slug, _course_fraction_slug) and await _course_standard_user(spawner)
    if slug == _course_shared_slug or (slug == _course_fraction_slug and standard):
        memory = options.get("gpu_memory_gib")
        options = {
            **options,
            "profile": _course_fraction_slug,
            "gpu_memory_gib": memory if memory in _course_memory_sizes else _course_student_memory,
            "session_duration_hours": "2",
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

