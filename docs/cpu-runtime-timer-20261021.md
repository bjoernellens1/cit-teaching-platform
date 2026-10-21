# CIT CPU runtime timer image

Future CPU Small/Large/XLarge servers, the default single-user image and the
chart's default image pre-pullers select
`ghcr.io/mul-cps/cit-jupyter-notebook@sha256:09380c3d17913064bd0c590c27a71d80a8995da5a0ed73e82cbd7cec8fae6218`.
This addon-only overlay retains the deployed CIT base
`sha256:6acd8bfe2b56968f7db0f9a033cdec329888a0e90cc73d4fa1e511f2561b18f9`;
it does not substitute the CPS notebook runtime. The canonical source previously
selected the mutable `latest-standard-cpu` tag; live6acd was pinned through the
separate reviewed consumer handover.

Root's publication receipt is
`O/cit-jupyterlab-server-runtime-20261021/publication.verified.private.json`, with
`O=/home/bjoern/.local/state/cps-full-project-20261013`. It binds config
`sha256:4efda15cc82a46534946198b31c1d0c28837f6a12325ebb57dc5511aae85dd78`,
addon source `5d15d2db497b2d96e16e981348cabe94910b9ae6`, and wheel
`a90b63abfa3fa64f64a4ec3f37edf54875cc0c08ad07d698904f231595c02eed`.
Installed verification matched all 10 wheel files and retained all 48 core
modules, 321 other distributions, UID1000/GID100, runtime configuration and base
layers. Lab discovery and the authenticated server-status probe passed. The
status start timestamp stayed stable and status polling did not update activity.
Browser timer display acceptance is separate.

The released Hub's `registered_cpu.configured_image` captures the trusted
`_original_profile_list` CPU Small image before installing its wrapper. Thus
the same immutable pin also serves registered CIT CPU workspaces. Interactive
CPU has no policy image allowlist; this change does not alter the signed GPU
cohort, D48, batch runner images, backend versions, resources or other profiles.

This commit is source preparation, not a deployment receipt. Root must capture
the actual CIT Hub Secret and current process/Service preimages, prepare an exact
CPU6acd-to-0938 whole-data UID/RV CAS and inverse, and preserve all other live
settings. Do not apply this entire older canonical Helm values file over live
configuration. Use guarded Hub-only maintenance, observer named-read
reconciliation, four fresh ACKs and unchanged writer journal validation before
restoring Source routes. Existing personal notebook Pods stay untouched; qualify
a newly started CPU server and its normal Stop separately.

GPU profile images and their pre-pullers are unchanged. In particular, the
separate CPS PyTorch6b6a runtime requires its own addon-only overlay before any
future image adoption. The current user-local timer installation and its running
Pod/container are outside this source change.
