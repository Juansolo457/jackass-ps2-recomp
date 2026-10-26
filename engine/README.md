# engine/

- `runtime.toml`: which runtime to fetch (repository + pinned commit). **Required**: the Urban Reign PC port's
  checkout, which carries PS2Recomp with that port's runtime changes and PCSX2's GS as a library.
  `tools/setup.sh` clones it into `engine/runtime/` (git-ignored) and builds the recompiler and the GS.
- `patches/NN-*.patch`: this project's changes to that checkout, applied in name order by `tools/setup.sh`.
  Each starts with a few lines saying what it changes, why, and where it came from (`git apply` skips them).
  Lines a patch adds carry a `// JA-Port:` marker. A runtime behaviour change ships a regression test.

| Patch | What | Origin |
|---|---|---|
| (none yet) | | |

To make one: edit inside `engine/runtime/`, then from the repo root
`git -C engine/runtime diff > engine/patches/NN-name.patch` and add the header lines. Check the later
patches still apply (`tools/setup.sh` re-applies the whole stack).
