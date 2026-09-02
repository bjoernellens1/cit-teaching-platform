from pathlib import Path


VALUES = Path(__file__).parents[1] / "bundles/20-jupyterhub/values/jupyterhub-values.yaml"
FLEET = Path(__file__).parents[1] / "bundles/20-jupyterhub/fleet.yaml"


def test_mujoco_student_profile_declares_gpu_and_session_options():
    text = VALUES.read_text()

    assert '"slug": "gpu-mujoco-xpra"' in text
    assert '"gpu-mujoco-xpra"' in text
    assert '"profile_options"' in text
    assert '"gpu_memory_gib"' in text
    assert '"session_duration_hours"' in text
    assert "for gib in range(1, 21)" in text
    assert 'f"{gib} GiB"' in text
    assert "str(gib * 1024)" in text
    assert 'f"0={gib * 1024}M"' in text
    assert "for hours in (2, 4, 8, 24)" in text
    assert '"active_deadline_seconds": hours * 3600' in text
    assert "active_deadline_seconds" in text
    assert "gpu-memory" in text
    assert "CUDA_MPS_PINNED_DEVICE_MEM_LIMIT" in text
    assert "mps-pipe" in text
    assert "mps-log" in text
    assert "# Cull after 24 hours of inactivity." in text
    assert "timeout: 86400" in text
    assert "maxAge: 86400" in text


def test_xpra_proxy_config_is_mounted_in_the_jupyter_config_path():
    text = VALUES.read_text()

    assert "mountPath: /usr/local/etc/jupyter/jupyter_server_config.py" in text
    assert '"xpra": {' in text
    assert '"xpra", "desktop", ":100"' in text
    assert '"launcher_entry": {"title": "Desktop (Xpra)"}' in text
    assert '"--xvfb=env __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json "' in text
    assert '"Xorg -noreset +extension GLX +extension RANDR +extension RENDER +extension Composite "' in text
    assert '"-config /etc/xpra/xorg.conf -nolisten tcp -dpi 96 -auth $XAUTHORITY"' in text
    assert '"--resize-display=auto"' in text
    assert '"--systemd-run=no"' in text
    assert '"--file-transfer=yes"' in text
    assert '"--file-size-limit=1G"' in text
    assert '"--open-files=no"' in text
    assert '"--clipboard=yes"' in text


def test_mps_profile_overrides_merge_with_chart_managed_storage():
    text = VALUES.read_text()

    assert 'def append_volume_mount(volume_spec, mount_spec):' in text
    assert 'if isinstance(spawner.volumes, dict):' in text
    assert '_mps_volumes = {' in text
    assert '_mps_volume_mounts = {' in text
    assert '"volumes": _mps_volumes' in text
    assert '"volume_mounts": _mps_volume_mounts' in text
    assert "dynamic home PVC" in text


def test_jupyterhub_chart_is_on_the_current_supported_patch_line():
    assert "version: 4.4.2" in FLEET.read_text()
