from pathlib import Path
from types import SimpleNamespace
import os
from unittest.mock import patch
import pytest


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
    assert '_proxy_servers["xpra"] = {' in text
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


def _mounted_jupyter_config_source():
    lines = VALUES.read_text().splitlines()
    start = next(
        i for i, line in enumerate(lines)
        if line.strip() == "stringData: |" and "jupyter-server-config:" in lines[i - 2]
    )
    source = []
    for line in lines[start + 1 :]:
        if line and not line.startswith("        "):
            break
        source.append(line[8:] if line.startswith("        ") else "")
    return "\n".join(source)


class _ConfigSection(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


def _evaluate_mounted_config(tmp_path, unavailable_path=None, non_executable_path=None):
    required_paths = (
        "/usr/bin/xpra",
        "/usr/bin/Xorg",
        "/usr/bin/dbus-launch",
        "/usr/bin/xfce4-session",
        "/usr/local/bin/start-xpra-desktop.sh",
        "/etc/xpra/xorg.conf",
        "/usr/share/xpra/www/index.html",
    )
    for path in required_paths:
        fixture_path = tmp_path / path.lstrip("/")
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text("fixture")
        if path in required_paths[:5]:
            fixture_path.chmod(0o755)
    if unavailable_path is not None:
        (tmp_path / unavailable_path.lstrip("/")).unlink()
    if non_executable_path is not None:
        (tmp_path / non_executable_path.lstrip("/")).chmod(0o644)

    def image_path(path):
        return tmp_path / path.lstrip("/")

    c = SimpleNamespace(
        ServerApp=_ConfigSection(),
        ServerProxy=_ConfigSection(servers={"other": {"port": 9000}}),
    )
    real_access = os.access
    with patch("os.path.isfile", lambda path: image_path(path).is_file()), patch(
        "os.access", lambda path, mode: real_access(image_path(path), mode)
    ):
        exec(_mounted_jupyter_config_source(), {"c": c})
    return c.ServerProxy.servers


def test_xpra_launcher_is_registered_for_a_compatible_desktop_image(tmp_path):
    servers = _evaluate_mounted_config(tmp_path)

    assert servers["other"] == {"port": 9000}
    assert servers["xpra"]["launcher_entry"] == {"title": "Desktop (Xpra)"}
    command = servers["xpra"]["command"](23500)
    assert command[:4] == ["xpra", "desktop", ":100", "--bind-tcp=127.0.0.1:23500"]
    assert "--start-child=/usr/local/bin/start-xpra-desktop.sh" in command


@pytest.mark.parametrize(
    "unavailable_path",
    (
        "/usr/bin/xpra",
        "/usr/bin/Xorg",
        "/usr/bin/dbus-launch",
        "/usr/bin/xfce4-session",
        "/usr/local/bin/start-xpra-desktop.sh",
        "/etc/xpra/xorg.conf",
        "/usr/share/xpra/www/index.html",
    ),
)
def test_xpra_launcher_is_omitted_when_image_lacks_required_runtime(
    tmp_path, unavailable_path
):
    servers = _evaluate_mounted_config(tmp_path, unavailable_path=unavailable_path)

    assert "other" in servers
    assert "xpra" not in servers


def test_xpra_launcher_is_omitted_when_start_script_is_not_executable(tmp_path):
    servers = _evaluate_mounted_config(
        tmp_path, non_executable_path="/usr/local/bin/start-xpra-desktop.sh"
    )

    assert "other" in servers
    assert "xpra" not in servers


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
