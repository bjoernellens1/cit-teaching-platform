# CIT Hub OAuth refresh

Status: source configuration qualified; not deployed or tested with real refresh.

The CIT Hub uses the Dex static client `cit-jupyterhub`. Its existing encrypted
auth-state storage is required for OAuthenticator to retain a refresh token.
The Hub now requests `offline_access` alongside the existing identity scopes.
OAuthenticator can exchange a stored refresh token after access-token failure;
when neither token works it requires interactive login. The normal 300-second
authentication refresh gate is retained. [OAuthenticator refresh documentation](https://oauthenticator.readthedocs.io/en/latest/how-to/refresh.html)

There are two independent OAuth exchanges. Dex issues its own downstream refresh
token only when the Hub requests offline access. Dex's OIDC connector separately
needs `offline_access` in its upstream scopes to request an Authentik refresh
token. Its default scopes contain profile and email, while OpenID is added by
Dex. [Dex tokens](https://dexidp.io/docs/configuration/tokens/),
[Dex 2.44.0 connector source](https://github.com/dexidp/dex/blob/v2.44.0/connector/oidc/oidc.go)

The paired cluster-repository change adds that upstream scope only to the `cit`
connector. Authentik's existing provider for the Dex broker must also select its
existing `offline_access` scope mapping. This is a provider mapping update, not a
new client, redirect URI, client secret or token-validity change. Authentik has
required both the requested scope and provider mapping since2024.2.
[Authentik OAuth provider](https://docs.goauthentik.io/add-secure-apps/providers/oauth2/)

The CPS upstream connector is unchanged by this bounded CIT-path fix. Choosing
CPS at Dex is a separate activation gate: verify its Authentik provider and
upstream offline-access configuration before claiming that route refreshes.

## Deployment and acceptance

The live Hub also has separately qualified image, profile, identity and neutral
workspace settings. Apply the semantic delta in `cit-hub-scope-delta.json` to a
fresh, exact before-image using the existing controlled configuration process.
Do not replace the live values Secret with this repository's older whole-file
baseline or assume a Fleet merge is inert. A configuration render does not prove
that a running Hub has loaded the new scope. Keep all current image pins,
roles/groups, profiles, storage, credentials and refresh limits intact.

After the reviewed Authentik mapping and Dex/Hub configuration changes, existing
users need one new interactive authorization/consent flow. Their old auth state
cannot gain a refresh token through a scope edit. Do not delete auth state,
rotate credentials, disable authentication refresh or extend validity to avoid
that login. No user session or server was modified by the source fix.

Use a normal controlled account for acceptance. Confirm the actual authorization
request asks for offline access; then inspect only stored-auth-state keys and
refresh-token presence. Prove a normal OAuthenticator refresh against the real
Dex/upstream provider succeeds and persists any rotated refresh token, with
current user identity and permissions preserved. Check revocation or denied
refresh still requires login. Keep token values private. A fresh login alone,
Helm render or a mocked refresh is insufficient to claim end-to-end renewal.
