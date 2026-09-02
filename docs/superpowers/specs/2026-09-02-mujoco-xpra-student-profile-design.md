# MuJoCo Xpra Student Profile Design

## Goal

Provide every CIT JupyterHub student with one isolated MuJoCo desktop profile
that offers a 1–20 GiB GPU-memory selection, GPU-backed headless rendering,
and a browser-accessible Xpra desktop. The platform must solve the EGL runtime
dependency centrally; students must neither install system packages nor receive
sudo access.

## Scope and repositories

The feature spans two repositories with separate responsibilities:

- `mul-cps/cps-jupyter-notebook` builds and publishes the reusable desktop
  layers and their tests.
- `bjoernellens1/cit-teaching-platform` selects the published MuJoCo image,
  presents the memory selector, and deploys it through Fleet.

The legacy TurboVNC desktop is out of scope. The existing Xpra ROS desktop is
refactored to use the shared Xpra layer but retains its ROS and productivity
capabilities.

## Image architecture

```text
quay.io/jupyter/pytorch-notebook:x86_64-cuda12-2026-02-09@sha256:257b2d2f821824b7b4c96a8b54a625a5427bc86b4563ec9d5c24f795bdd0a3eb
└─ cps-jupyter-notebook-base-gpu
   └─ pytorch-runtime-base
      ├─ pytorch-code
      └─ desktop-xpra-base
         ├─ mujoco-xpra
         └─ desktop-ros2-xpra
```

`cps-jupyter-notebook-base-gpu` is a minimal local compatibility layer on the
pinned, official Jupyter CUDA/PyTorch image. It retains the JupyterHub
single-user entrypoint, `/home/jovyan` contract, and only platform-wide
configuration needed by all local GPU images. It must not install local IDE
extensions, broad ML libraries, desktop software, or sudo access.

`pytorch-runtime-base` is derived from that base and contains only the PyTorch
runtime required by the platform. `pytorch-code` remains the broad, existing ML
environment. This preserves compatibility for existing profiles without
silently expanding the MuJoCo environment.

`desktop-xpra-base` is derived from `pytorch-runtime-base` and is the shared
implementation of all Xpra desktop mechanics: EGL/GLVND user-space runtime,
VirtualGL, Xpra with its HTML5 client, XFCE, the desktop session startup script,
and the Jupyter Server Proxy integration. It removes `jovyan` from every sudo
grant inherited from an upstream layer.

`mujoco-xpra` is derived from `desktop-xpra-base`. It installs only the Python
MuJoCo bindings, Gymnasium's MuJoCo integration, and any direct runtime Python
dependencies not already supplied by those packages. It sets
`MUJOCO_GL=egl`, `PYOPENGL_PLATFORM=egl`, and
`NVIDIA_DRIVER_CAPABILITIES=compute,graphics,utility` for non-interactive and
interactive notebook processes. It includes neither ROS nor TensorFlow nor
office applications nor a desktop IDE.

`desktop-ros2-xpra` is refactored to derive from `desktop-xpra-base` and adds
only its present ROS, productivity, and ROS-specific development dependencies.

## Desktop route

The MuJoCo profile exposes a `jupyter_server_proxy` entry named `xpra`. It
starts Xpra with a per-user display and its HTML5 server bound only inside the
single-user pod. JupyterHub's authenticated `/user/<name>/xpra/` route is the
only externally reachable path. The launch settings and health check must be
the same known-good Xpra strategy used by the CPS cluster, adapted to this
chart's mounted `jupyter_server_config.py`.

The environment uses EGL for off-screen MuJoCo frames. VirtualGL is retained
for applications launched in the Xpra desktop. The functional test must prove
both paths separately, because a browser desktop loading does not prove MuJoCo
can create an EGL renderer.

## JupyterHub profile and GPU memory options

Add one `gpu-mujoco-xpra` profile to the existing profile list. It is included
in the student-visible profile set, while every existing profile's visibility
is unchanged. The profile has a required `profile_options.gpu_memory_gib`
selector with exactly twenty choices: integer GiB values 1 through 20.

Each choice atomically applies all four pieces of the MPS contract:

1. the KAI `gpu-memory` annotation in MiB (`GiB * 1024`),
2. `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT=0=<MiB>M`,
3. the existing MPS pipe and log host-path mounts, and
4. the existing KAI scheduler, course queue, and student priority class.

The profile requests one GPU slot so the NVIDIA runtime and MPS device are
available, while KAI reserves the selected memory amount. It does not request
an exclusive `nvidia.com/gpu` resource. CPU, RAM, storage, and priority are
specified once at the profile level and sized for an interactive single A100
MPS workload; they are not copied into each selector option.

The profile's image reference is immutable for production deployment. During
image qualification it may point at the in-cluster builder's unique test tag;
the GitOps change is updated only after the image digest and functional test
result are recorded.

## Student session duration

The standard student session duration is two hours. The MuJoCo launch form has
a required duration dropdown with 2, 4, 8, and 24 hour choices; 24 hours is
the absolute maximum. The existing one-hour idle cull stays in effect.

The global culler maximum age is raised to 24 hours only so it does not
preempt the approved extended session. The selected duration is enforced per
pod with `active_deadline_seconds`: 7200, 14400, 28800, or 86400.

## Image size and supply-chain constraints

- Base all image stages on the pinned Jupyter CUDA 12 digest above; do not use
  floating upstream tags in a production Dockerfile.
- Use `apt-get --no-install-recommends`, BuildKit cache mounts, and remove apt,
  conda, and pip caches in the same image layer that installs packages.
- Add an explicit compressed-image size budget for `mujoco-xpra`. The budget
  is measured after the first in-cluster build and must be smaller than the
  existing Xpra ROS desktop image; it is not guessed before measurement.
- Record the upstream base digest and the derived image digest in the build
  result so Fleet deployments are reproducible.

## Tests and acceptance evidence

### Source and image tests

1. Extend static Dockerfile checks to enforce the layer graph, cache mounts,
   no duplicated desktop installation, and `jovyan` not belonging to `sudo` in
   the MuJoCo image.
2. Add a `mujoco-xpra` functional-image case that imports `torch`,
   `torchvision`, `mujoco`, and `gymnasium`; checks the Xpra and VirtualGL
   binaries; and confirms the required EGL environment values.
3. Run a GPU-backed in-cluster test container under the real MPS mounts and
   render an off-screen MuJoCo frame. The test fails if EGL initialization,
   renderer construction, or pixel production fails.
4. Build with the in-cluster image builder, retain its immutable output digest,
   and compare the measured compressed image size to the recorded budget.

### GitOps and live-platform tests

1. Add a configuration test that loads the JupyterHub values and asserts the
   student profile contains every 1–20 GiB option, the matching MPS annotation,
   memory-limit environment value, and MPS mounts.
2. Render the Fleet Helm bundle and validate the generated Hub configuration.
3. Push the image and GitOps commits, then observe Fleet consuming the GitOps
   commit, the bundle becoming ready, and the Hub rollout completing.
4. With a real student-visible JupyterHub session, select 1 GiB and 20 GiB in
   turn. For each, confirm the spawned pod uses the selected MPS annotation and
   limit, imports MuJoCo, renders an EGL frame, and opens the authenticated
   Xpra desktop route.

Static tests, image tests, and a reconciled Hub do not by themselves qualify
the feature. The final student-profile selection, MPS enforcement, EGL render,
and browser Xpra checks are the remaining physical/platform qualification gate.

## Failure handling and rollback

If an upstream image update, EGL renderer, Xpra route, or MPS limit test fails,
do not replace any existing profile. Keep `gpu-mujoco-xpra` absent from the
student profile set or point only a temporary test deployment at the candidate
image. Roll back the GitOps profile commit to remove the new profile and retain
the image digest and logs as failed qualification evidence.
