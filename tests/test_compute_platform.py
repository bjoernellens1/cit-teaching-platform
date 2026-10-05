import copy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compute',ROOT/'scripts/validate_compute_platform.py')
compute=importlib.util.module_from_spec(spec);spec.loader.exec_module(compute)
CONFIG=json.loads((ROOT/'staging/compute-platform/config.json').read_text())
POLICY=json.loads((ROOT/'staging/compute-platform/policy.json').read_text())
def test_disabled_stage_is_valid(): assert compute.validate(CONFIG,POLICY)==POLICY['policyHash']
def test_activation_requires_gates():
 config=copy.deepcopy(CONFIG);config['enabled']=True
 with pytest.raises(ValueError,match='gates'):compute.validate(config,POLICY)
def test_modified_policy_is_rejected():
 policy=copy.deepcopy(POLICY);policy['version']='9.0.0'
 with pytest.raises(ValueError,match='hash'):compute.validate(CONFIG,policy)
def test_group_replacement_waits_for_seeding():
 config=copy.deepcopy(CONFIG);config['authenticatorGroupReplacement']='console-owned'
 with pytest.raises(ValueError,match='migration'):compute.validate(config,POLICY)
def test_live_auth_and_chart_are_preserved():
 text=(ROOT/'bundles/20-jupyterhub/values/jupyterhub-values.yaml').read_text()
 assert 'manage_groups: true' in text
 assert 'username_claim: preferred_username' in text
 assert 'version: 4.4.2' in (ROOT/'bundles/20-jupyterhub/fleet.yaml').read_text()

def test_adapter_import_is_guarded_and_unwatched():
 text=(ROOT/"staging/compute-platform/hub-values.yaml").read_text()
 assert 'CPS_COMPUTE_ENABLED: "0"' in text
 assert text.index('if os.environ.get("CPS_COMPUTE_ENABLED"') < text.index("from cps_compute.hub import configure_hub")
 assert "staging/" not in (ROOT/"bundles/20-jupyterhub/fleet.yaml").read_text()
