"""Validate CIT's operator-owned CPU consumers without executing Hub hooks."""
import ast
from pathlib import Path

import yaml

VALUES = Path(__file__).parents[1] / 'bundles/20-jupyterhub/values/jupyterhub-values.yaml'
IMAGE = ('ghcr.io/mul-cps/cit-jupyter-notebook@sha256:'
         '09380c3d17913064bd0c590c27a71d80a8995da5a0ed73e82cbd7cec8fae6218')


def cpu_profiles():
    code = yaml.safe_load(VALUES.read_text())['hub']['extraConfig']['profile_list_hook']
    table = next(node.value for node in ast.parse(code).body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == '_original_profile_list'
                         for target in node.targets))
    result = {}
    for row in table.elts:
        slug = next(ast.literal_eval(value) for key, value in zip(row.keys, row.values)
                    if isinstance(key, ast.Constant) and key.value == 'slug')
        if slug.startswith('cpu-'):
            result[slug] = ast.literal_eval(row)['kubespawner_override']
    return result


def test_all_three_effective_cpu_profiles_use_the_verified_cit_overlay():
    rows = cpu_profiles()
    assert set(rows) == {'cpu-small', 'cpu-large', 'cpu-xlarge'}
    assert all(row['image'] == IMAGE for row in rows.values())


def test_default_and_chart_prepuller_select_the_same_immutable_cpu_bytes():
    image = yaml.safe_load(VALUES.read_text())['singleuser']['image']
    assert image['name'] + '@' + image['tag'].split('@', 1)[-1] == IMAGE


def test_cit_overlay_is_scoped_to_the_three_cpu_rows():
    code = yaml.safe_load(VALUES.read_text())['hub']['extraConfig']['profile_list_hook']
    assert code.count(IMAGE) == 3
