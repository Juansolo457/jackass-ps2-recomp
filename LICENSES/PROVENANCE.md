# License texts: where they come from

The root `LICENSE` (MIT) covers this project's own files. Third-party license texts are added here the moment
third-party code or scaffolding is tracked or built against, with the upstream commit they were copied from;
`NOTICE` says which files each one covers.

| File | Copied verbatim from | Applies to |
|---|---|---|
| `AC5-Recomp-APACHE-2.0.txt` | `docs/licenses/AC5-Recomp-APACHE-2.0.txt` of the Urban Reign checkout at `20b30fd` | `runtime/ps2xRuntime/src/lib/ipu` in the checkout: the Ace Combat 5 static recompilation's IPU (Apache-2.0) |
| `GPL-3.0.txt` | `LICENSES/GPL-3.0.txt` of the sibling graw360-recomp (itself `LICENSE` of fear-nx at `acad80d`, from Project8Recomp); the standard GNU GPL v3 text | the Urban Reign port, PS2Recomp, PCSX2 (all GPL-3.0) in the `engine/runtime/` checkout, our patches and host code on them, and the built program |

The checkout's own `LICENSE` is the GPL v3 text in Markdown form (checked by `tools/setup.sh` on 2026-10-27).
