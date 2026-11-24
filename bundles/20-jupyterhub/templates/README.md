# CIT notebook start page

The CIT `spawn.html` extends `cps-personal-spawn.html`. The parent is a
verbatim copy of the CPS Hub's mounted `spawn.html` from 2026-11-24.
Its SHA-256 is
`a7014c9a0be6b14d6fdba2888a84c789410a7b09f58ee5079480f83fe8e666b5`.
The parent supplies the stylesheet. The child uses the CIT form
controls for CPU Small, shared VRAM, permissions, and Notebook Help.

Both files mount read-only through the Hub's existing `files` volume
in `/usr/local/share/jupyterhub/shared-home-templates/`. When refreshing
the parent from CPS, verify the template inheritance and all four CIT
role fixtures before changing the immutable file reference.
