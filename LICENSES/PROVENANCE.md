# License texts: where they come from

The root `LICENSE` (MIT) covers this project's own files. Third-party license texts are added here the moment
third-party code or scaffolding is tracked or built against, with the upstream commit they were copied from;
`NOTICE` says which files each one covers.

| File | Copied verbatim from | Applies to |
|---|---|---|
| `GPL-3.0.txt` | `LICENSES/GPL-3.0.txt` of the sibling graw360-recomp (itself `LICENSE` of fear-nx at `acad80d`, from Project8Recomp); the standard GNU GPL v3 text | the Urban Reign port, PS2Recomp, PCSX2 (all GPL-3.0) in the `engine/runtime/` checkout, our patches and host code on them, and the built program |

To add when `tools/setup.sh` has run once: the checkout's `LICENSE` (the same GPL text; `setup.sh` warns if
it is not) and `docs/licenses/AC5-Recomp-APACHE-2.0.txt` from it, for the IPU code in
`runtime/ps2xRuntime/src/lib/ipu`.
