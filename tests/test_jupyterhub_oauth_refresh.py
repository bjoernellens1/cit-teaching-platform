"""Declared OAuth request and auth-state persistence; no live login claims."""
from pathlib import Path
import yaml

VALUES=Path(__file__).parents[1]/'bundles/20-jupyterhub/values/jupyterhub-values.yaml'


def test_cit_hub_requests_offline_scope_without_replacing_identity_scopes():
    config=yaml.safe_load(VALUES.read_text())['hub']['config']
    oauth=config['GenericOAuthenticator']
    assert oauth['client_id']=='cit-jupyterhub'
    assert oauth['scope']==['openid','profile','email','groups','offline_access']
    assert oauth['authorize_url']=='https://dex.dshl.unileoben.ac.at/auth'
    assert oauth['token_url']=='https://dex.dshl.unileoben.ac.at/token'


def test_refresh_keeps_encrypted_auth_state_and_normal_refresh_gate():
    config=yaml.safe_load(VALUES.read_text())['hub']['config']
    assert config['Authenticator']['enable_auth_state'] is True
    assert config['GenericOAuthenticator']['enable_auth_state'] is True
    for name in ('Authenticator','OAuthenticator','GenericOAuthenticator'):
        section=config.get(name,{})
        assert section.get('auth_refresh_age',300)==300
        assert not section.get('refresh_user_hook')


def test_reviewable_live_delta_is_scope_only_and_matches_values():
    import json
    delta=json.loads((VALUES.parents[3]/'docs/auth/cit-hub-scope-delta.json').read_text())
    scopes=yaml.safe_load(VALUES.read_text())['hub']['config']['GenericOAuthenticator']['scope']
    assert delta['object']=={'kind':'Secret','namespace':'cit-jhub','name':'hub'}
    assert delta['decodedDataKey']=='values.yaml'
    assert delta['path']=='/hub/config/GenericOAuthenticator/scope'
    assert delta['expectedBefore']==[s for s in scopes if s!='offline_access']
    assert delta['after']==scopes and delta['liveApplied'] is False
    assert delta['requiresFreshExactBeforeImageAndCAS'] is True
