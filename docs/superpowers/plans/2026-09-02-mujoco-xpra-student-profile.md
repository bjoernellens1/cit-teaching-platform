# MuJoCo Xpra Student Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a small, GPU-rendering MuJoCo Xpra notebook image and make it available to all CIT students with a 1–20 GiB MPS selector.

**Architecture:** `cps-jupyter-notebook` changes its GPU image family to a pinned Jupyter CUDA/PyTorch upstream base followed by shared local `base-gpu`, `pytorch-runtime-base`, and `desktop-xpra-base` layers. `mujoco-xpra` and the refactored ROS Xpra image derive from the shared desktop layer. This repository consumes the validated immutable image digest in a student-visible JupyterHub profile and lets Fleet deploy it.

**Tech Stack:** Docker BuildKit, `quay.io/jupyter/pytorch-notebook`, PyTorch, MuJoCo, Gymnasium, EGL/GLVND, VirtualGL, Xpra/XFCE, Jupyter Server Proxy, KubeSpawner, KAI MPS scheduling, Helm/Fleet, Kubernetes.

**Spec:** `docs/superpowers/specs/2026-09-02-mujoco-xpra-student-profile-design.md`

## Global Constraints

- Pin the upstream base to `quay.io/jupyter/pytorch-notebook:x86_64-cuda12-2026-02-09@sha256:257b2d2f821824b7b4c96a8b54a625a5427bc86b4563ec9d5c24f795bdd0a3eb`.
- The MuJoCo profile is student-visible; its image must not grant `jovyan` sudo.
- Every 1–20 GiB choice must set annotation, MPS limit, pipe/log mounts, and KAI routing together.
- Student sessions default to 2 hours; dropdown choices are 2, 4, 8, and 24 hours only.
- Build through the in-cluster BuildKit/image-builder path; push only a validated image and record its immutable digest before changing Fleet production configuration.
- Do not alter existing profile visibility or the legacy TurboVNC desktop.

---

### Task 1: Establish the upstream-derived image layer graph

**Repository:** `/home/bjoern/git/cps-jupyter-notebook` in a new isolated `feat/mujoco-xpra` worktree.

**Files:**
- Modify: `docker/Dockerfile.base-gpu`
- Create: `docker/Dockerfile.pytorch-runtime-base`
- Create: `docker/Dockerfile.desktop-xpra-base`
- Modify: `docker/tests/structural_checks.py`
- Modify: `.github/workflows/docker-publish.yml`

**Interfaces:**
- Produces `ghcr.io/mul-cps/cps-jupyter-notebook-base-gpu:<immutable-build-tag>`, `...:pytorch-runtime-base-<tag>`, and `...:desktop-xpra-base-<tag>`.
- The desktop base exports `/usr/local/bin/start-xpra-desktop.sh`, `/usr/local/bin/_vglwrap`, the enabled `jupyter_server_proxy` extension, and the environment needed by child images.

- [ ] **Step 1: Add a failing structural assertion for the required bases**

Extend `CONSOLIDATED_VARIANTS` and add checks that fail unless the first image
in each Dockerfile follows the requested graph:

```python
CONSOLIDATED_VARIANTS.update({
    "Dockerfile.pytorch-runtime-base": "ghcr.io/mul-cps/cps-jupyter-notebook-base-gpu",
    "Dockerfile.desktop-xpra-base": "ghcr.io/mul-cps/cps-jupyter-notebook:pytorch-runtime-base",
})
```

Also assert that `Dockerfile.desktop-xpra-base` contains `xpra-html5`,
`jupyter_server_proxy`, and `gpasswd -d "${NB_USER}" sudo` (with a harmless
fallback if the group is absent).

- [ ] **Step 2: Run the structural test and verify the expected red result**

Run: `python3 docker/tests/structural_checks.py`

Expected: non-zero, naming the missing `pytorch-runtime-base` and
`desktop-xpra-base` Dockerfiles.

- [ ] **Step 3: Implement the minimal upstream-derived bases**

Make `Dockerfile.base-gpu` begin with the pinned upstream image and retain only
the platform-wide JupyterHub compatibility setup. Add `pytorch-runtime-base`
as the narrow PyTorch compatibility layer. Extract the current Xpra-only EGL,
VirtualGL, Xpra HTML5, XFCE, session script, and server-proxy enablement from
`Dockerfile.desktop-ros2-xpra` into `desktop-xpra-base`; do not move ROS,
LibreOffice, code-server desktop, TensorFlow, or broad ML packages into it.
Remove inherited sudo membership as the final privilege operation in the shared
desktop base.

- [ ] **Step 4: Order and publish the new stages in CI**

Add the three stages to `.github/workflows/docker-publish.yml` so dependencies
are built and pushed in order: base GPU, PyTorch runtime, desktop Xpra base,
then their children. Point the buildx driver at the in-cluster BuildKit pool
for the validation/publish workflow using the existing cluster pattern:

```sh
docker buildx create --name ci-pool --driver remote \
  tcp://buildkit-pool.ci.svc.cluster.local:1234 --use
```

Use unique revision tags for validation; only the later promotion step may add
the stable image tag.

- [ ] **Step 5: Run structural tests and commit**

Run: `python3 docker/tests/structural_checks.py`

Expected: `All structural checks passed.`

Run: `git diff --check`

Commit: `refactor(images): derive GPU desktop layers from Jupyter upstream`

### Task 2: Build the minimal MuJoCo Xpra image and preserve ROS Xpra

**Repository:** `/home/bjoern/git/cps-jupyter-notebook` feature worktree.

**Files:**
- Create: `docker/Dockerfile.mujoco-xpra`
- Modify: `docker/Dockerfile.desktop-ros2-xpra`
- Modify: `docker/tests/functional_checks.sh`
- Modify: `docker/tests/size_budgets.yaml`
- Modify: `.github/workflows/docker-publish.yml`

**Interfaces:**
- Produces `ghcr.io/mul-cps/cps-jupyter-notebook:<revision>-mujoco-xpra`.
- `mujoco-xpra` must support `import torch, torchvision, mujoco, gymnasium` and a MuJoCo EGL renderer.

- [ ] **Step 1: Write the failing MuJoCo Xpra functional case**

Add a `mujoco-xpra` branch to `functional_checks.sh`:

```sh
check_cmd "torch is importable" python3 -c "import torch, torchvision"
check_cmd "MuJoCo is importable" python3 -c "import mujoco, gymnasium"
check_cmd "Xpra binary present" sh -c "command -v xpra"
check_cmd "VirtualGL binary present" sh -c "command -v vglrun"
check_cmd "EGL environment is configured" sh -c '[ "$MUJOCO_GL" = egl ] && [ "$PYOPENGL_PLATFORM" = egl ]'
check_cmd "jovyan has no sudo" sh -c '! id jovyan | grep -qw sudo'
```

- [ ] **Step 2: Run against the current image and verify red**

Run: `sh docker/tests/run_functional_checks.sh ghcr.io/mul-cps/cps-jupyter-notebook:latest-pytorch-code mujoco-xpra`

Expected: non-zero because MuJoCo/Xpra is absent and/or `jovyan` retains sudo.

- [ ] **Step 3: Implement the two child images**

Create `Dockerfile.mujoco-xpra` from `desktop-xpra-base`, using one cached pip
layer to install MuJoCo and Gymnasium. Configure:

```dockerfile
ENV MUJOCO_GL=egl \
    PYOPENGL_PLATFORM=egl \
    NVIDIA_DRIVER_CAPABILITIES=compute,graphics,utility
```

Refactor `Dockerfile.desktop-ros2-xpra` to start from `desktop-xpra-base` and
keep all of its current ROS/productivity behavior in the child. Add both child
images to the CI matrix and pre-publish tests. Do not make a stable tag here.

- [ ] **Step 4: Run source tests and submit an in-cluster validation build**

Run: `python3 docker/tests/structural_checks.py`

Submit the revision-tagged `mujoco-xpra` build through the cluster image-builder
or the BuildKit-pool-backed workflow, capture the Job/run URL, final image
digest, and compressed size. The build must push the revision tag only after it
completes successfully.

- [ ] **Step 5: Run image and GPU rendering checks**

Run the functional script against the pushed revision image. Then start a
disposable MPS-wired GPU pod with the image, MPS pipe/log mounts, and a 1 GiB
limit. Execute:

```python
import mujoco
xml = "<mujoco><worldbody><geom type='sphere' size='.1'/></worldbody></mujoco>"
renderer = mujoco.Renderer(mujoco.MjModel.from_xml_string(xml), 64, 64)
assert renderer.render().shape == (64, 64, 3)
```

Expected: exit zero and a 64×64×3 pixel frame. Remove the disposable pod after
collecting logs.

- [ ] **Step 6: Record size and promote only after validation**

Set the `mujoco-xpra` compressed-size budget to the measured value plus a 10%
margin, and assert it is lower than the measured ROS Xpra image. Push the
validated image digest and promote the stable `latest-mujoco-xpra` tag to that
same digest. Do not push/publish a stable tag if either functional or GPU test
failed.

- [ ] **Step 7: Commit and push the image repository branch**

Run: `git diff --check && python3 docker/tests/structural_checks.py`

Commit: `feat(images): add upstream-based MuJoCo Xpra desktop`

Push the verified branch and retain the immutable digest for Task 3.

### Task 3: Add the student MuJoCo profile and exact MPS selector

**Repository:** `/home/bjoern/git/cit-teaching-platform/.worktrees/mujoco-xpra-profiles`.

**Files:**
- Modify: `bundles/20-jupyterhub/values/jupyterhub-values.yaml`
- Create: `tests/test_jupyterhub_mujoco_profile.py`

**Interfaces:**
- Produces student-visible profile `gpu-mujoco-xpra`.
- Its `profile_options.gpu_memory_gib` has keys `1` through `20` and uses the validated immutable image digest from Task 2.
- Its `profile_options.session_duration_hours` has choices 2, 4, 8, and 24 mapped to `active_deadline_seconds`.

- [ ] **Step 1: Write the failing configuration test**

Load the YAML and extract the Python profile-list source. Assert that the
source defines `gpu-mujoco-xpra`, includes it in `student_profiles`, uses the
validated image digest, and generates exactly these MiB values:

```python
expected_mib = {gib: gib * 1024 for gib in range(1, 21)}
assert expected_mib == {1: 1024, 2: 2048, 3: 3072, 4: 4096, 5: 5120,
                        6: 6144, 7: 7168, 8: 8192, 9: 9216, 10: 10240,
                        11: 11264, 12: 12288, 13: 13312, 14: 14336,
                        15: 15360, 16: 16384, 17: 17408, 18: 18432,
                        19: 19456, 20: 20480}
```

The test must additionally require the MPS annotation, CUDA MPS limit, both
MPS mounts, `kai-scheduler`, course queue, and course priority class for each
choice. It must require `{2: 7200, 4: 14400, 8: 28800, 24: 86400}`, default
to 2 hours, and assert both `cull.maxAge` and `cull.timeout` are 86400 so a
disconnected training run is bounded by its selected pod deadline rather than
browser activity.

- [ ] **Step 2: Run the test and verify red**

Run: `pytest -q tests/test_jupyterhub_mujoco_profile.py`

Expected: FAIL because neither profile nor test target exists.

- [ ] **Step 3: Implement the profile and Xpra server proxy**

Add the Xpra `ServerProxy.servers` entry to `singleuser.extraFiles` and add the
single MuJoCo profile to `_original_profile_list`. Use KubeSpawner
`profile_options` with a generated/explicit twenty-choice mapping so each
choice overrides the full MPS contract atomically. Add `gpu-mujoco-xpra` to
`student_profiles`; do not add any other GPU profile there. Add a session
duration dropdown that sets `active_deadline_seconds` to 7200, 14400, 28800,
or 86400; set both `cull.maxAge` and `cull.timeout` to 86400. Label the 8 and
24 hour options as training sessions.

- [ ] **Step 4: Verify green and render the chart**

Run: `pytest -q tests/test_jupyterhub_mujoco_profile.py`

Run: `helm repo add jupyterhub https://hub.jupyter.org/helm-chart/ && helm template cit-jupyterhub jupyterhub/jupyterhub --version 4.3.2 -f bundles/20-jupyterhub/values/jupyterhub-values.yaml >/tmp/cit-jupyterhub-mujoco-rendered.yaml`

Expected: both commands exit zero; the rendered ConfigMap includes the Xpra
server-proxy configuration.

- [ ] **Step 5: Commit and push Fleet configuration**

Run: `git diff --check`

Commit: `feat(jupyterhub): add student MuJoCo Xpra GPU profile`

Push the feature branch only after the image digest is validated and fixed in
the values file.

### Task 4: Reconcile Fleet and conduct live qualification

**Repositories:** image branch from Task 2 and this GitOps feature branch.

**Files:** none unless testing reveals a defect; retain command output in the PR/commit notes.

- [ ] **Step 1: Confirm the image is pushed and immutable**

Inspect the registry manifest for the digest in the GitOps profile and compare
it to Task 2's successful GPU-test digest. Refuse to proceed if the digest is
missing, differs, or only a floating tag is present.

- [ ] **Step 2: Observe Fleet reconciliation**

Push the GitOps branch through the approved merge path, then watch the
`cit-jupyterhub` BundleDeployment, Helm release revision, Hub deployment, and
Hub logs until the desired revision is Ready. Do not patch the live Hub.

- [ ] **Step 3: Qualify both selector boundaries with a student session**

Log in as a non-privileged student. Spawn `gpu-mujoco-xpra` at 1 GiB and 20
GiB separately. For each pod, prove its `gpu-memory` annotation, MPS limit,
MPS mounts, no sudo group, MuJoCo import, 64×64 EGL frame, and authenticated
`/user/<name>/xpra/` desktop route. Capture the pod name, image digest, and
Hub/singleuser logs.

- [ ] **Step 4: Verify cleanup and report the remaining gate**

Delete only the two test servers/pods created for this qualification, not
other users' servers. Confirm they are gone and finish with `podman ps` for
any locally-owned test containers. If the student browser session cannot be
provided, report the configuration/image results as complete but leave live
student Xpra qualification explicitly open.
