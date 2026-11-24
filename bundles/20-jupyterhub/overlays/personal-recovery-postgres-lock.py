"""Compatibility patch for the live CIT Hub image's personal recovery query."""
import hashlib
import inspect
import textwrap

from cps_compute_hub import personal_gpu


def _fix_cit_personal_recovery_lock():
    method = personal_gpu.PersonalHubBridge.reconcile_inactive
    source = inspect.getsource(method)
    scoped = "with_for_update(nowait=True, of=orm.Spawner)"
    if scoped in source:
        return
    expected = "02258af8d4e4445f022bd6ae076ab61cc903d5dc2b068c7a841040c4fbf0af2d"
    if hashlib.sha256(source.encode()).hexdigest() != expected:
        raise RuntimeError("Unexpected CIT personal recovery method")
    original = "with_for_update(nowait=True)"
    assert source.count(original) == 1
    edited = textwrap.dedent(source).replace(original, scoped)
    namespace = {}
    exec(compile(edited, inspect.getsourcefile(method) or "<cit-personal-recovery>", "exec"), vars(personal_gpu), namespace)
    personal_gpu.PersonalHubBridge.reconcile_inactive = namespace["reconcile_inactive"]


_fix_cit_personal_recovery_lock()
