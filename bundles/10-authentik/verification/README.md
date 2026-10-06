# Optional email verification

Sign in to the existing Authentik account, then open:

https://auth.dshl.unileoben.ac.at/if/flow/cps-email-verification/

The flow sends to the account's current directory email. It does not accept a
replacement address. Open the email in a browser signed into the same account
and press the confirmation button. Empty directory addresses require an
administrator to correct the directory first. Initial requests have a
60-second database-backed cooldown; links expire after 15 minutes (Authentik
adds its standard rounding minute). Accounts are never activated by this flow.

This is optional. The flow is not bound to authentication, source enrollment,
provider authorization, or existing user settings. Existing OIDC email mappings
remain unchanged, and the CPS/CIT canonical-person maps remain inactive.

## Proof and future linkage

Completion writes `cps/email-verification` in user attributes. The value is a
Django-signed object under salt `cps.email-verification.v1`, containing version1,
the immutable Authentik user primary key, the exact verified directory address,
and verification time. Native user-update auditing records the mutation. The
native email consent stage consumes the token before proof is recorded; merely
opening an unconfirmed link cannot create proof.

Future consumers must verify the signature and version, match the user primary
key and exact current address, and validate the timestamp. A copied attribute,
a forged signature, or a proof for a different current address is insufficient.
Do not treat attribute presence as verification. Restore the matching Authentik
secret key with the database; changing that key invalidates existing proofs.
Email normalization/collision review and explicit aliases to stable person IDs
remain separate gates before cross-Hub linkage. This flow changes no homes,
usernames, groups, permissions or allowances.

## Deployment and qualification

`../authentik-optional-email-verification.yaml` wraps the native blueprint in a
ConfigMap. Worker Helm values mount it read-only in `/blueprints/cps` for the
native Authentik blueprint loader. The adjacent `.blueprint` file is the exact
same content; update both together. Owned identifiers use `cps-email-verification`.

`qualify.py` runs inside the installed Authentik `ak shell`, with `BLUEPRINT`
set to the file content. It imports the blueprint and creates temporary test
users/tokens inside a rollback-only transaction. It sends no messages, performs
no human login, and does not retain fixture accounts or proofs. It checks native
policy evaluation, native confirmation token consumption, native serialization,
expiry, replay, account/address mismatch, signed proofs, initial throttling and
unchanged bindings outside the optional flow.

The initial native checks passed on Authentik2025.12.4. Real user interaction
with the verification email still requires confirmation; ordinary SMTP delivery
has already been confirmed separately. Do not enable linkage from fixture tests.
