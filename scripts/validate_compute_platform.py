#!/usr/bin/env python3
"""Validate CIT staging integration without rendering or deploying live workloads."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def validate(config,policy):
    raw={k:v for k,v in policy.items() if k!='policyHash'}
    digest='sha256:'+hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    if policy['policyHash'] != digest or config['policyHash'] != digest: raise ValueError('policy artifact hash mismatch')
    if config['hub'] != 'cit' or config['owner'] != 'cit': raise ValueError('CIT console owns CIT records only')
    admin=config['adminConsole']
    if admin['replicas'] != 1 or admin['database'] != 'sqlite:///data/cit-console.sqlite': raise ValueError('CIT console requires one persistent SQLite database')
    secrets=[admin[k] for k in ['oauthSecretName','hubServiceSecretName','policyServiceSecretName','databaseBackupSecretName']]
    if len(set(secrets)) != len(secrets) or any(not s.startswith('cit-course-admin-') for s in secrets): raise ValueError('CIT service credentials must be distinct and CIT owned')
    if admin['moodleEnabled'] or config['hub6']['enabled']: raise ValueError('unfinished providers and Hub 6 are disabled')
    if config['authenticatorGroupReplacement'] != 'preserve-until-seeded' and not config['qualification']['existingGrantsSeeded']: raise ValueError('grant migration must precede group ownership change')
    if config['enabled']:
        if not all(config['qualification'].values()) or not config['canonicalIdentityMapping']: raise ValueError('identity, grant, storage, backup and release gates required')
        for image in config['images'].values():
            if not image or not re.fullmatch(r'[^\s@]+@sha256:[a-f0-9]{64}',image): raise ValueError('released immutable images required')
        if not policy['approvedImages']: raise ValueError('reviewed approved image catalog required')
    return digest
if __name__=='__main__':
    path=ROOT/'staging/compute-platform'
    print(validate(json.loads((path/'config.json').read_text()),json.loads((path/'policy.json').read_text())))
