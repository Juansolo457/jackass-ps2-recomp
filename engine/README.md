# engine/

- `runtime.toml`: which runtime to fetch (repository + pinned commit). **Required**: the Urban Reign PC port's
  checkout, which carries PS2Recomp with that port's runtime changes and PCSX2's GS as a library.
  `tools/setup.sh` clones it into `engine/runtime/` (git-ignored) and builds the recompiler and the GS.
- `patches/NN-*.patch`: this project's changes to that checkout, applied in name order by `tools/setup.sh`.
  Each starts with a few lines saying what it changes, why, and where it came from (`git apply` skips them).
  Lines a patch adds carry a `// JA-Port:` marker. A runtime behaviour change ships a regression test.

| Patch | What | Origin |
|---|---|---|
| 01-setupthread-boot-args | `SetupThread` fills crt0's args block (argc, argv) when `PS2X_BOOT_ARGV0` is set; `PS2X_BOOT_ARGS` adds more. Jackass's `main` checks `argv[0]` for `cdrom0:` to use its disc paths instead of its development-kit `host0:` paths. Opt-in, so other games keep the runtime's behaviour | this project |
| 02-tty-stubs | libkernel TTY: `sceTtyInit`/`sceResetttyinit` succeed, `sceTtyWrite` logs and returns its length, `sceTtyRead` returns 0 (they were placeholders that stop the program; Jackass calls `sceTtyInit` at start-up) | this project |
| 03-iop-module-arena | IOP kernel heap base 0x80000 → 0xC0000: IRX modules get 704 KB (FMODS.IRX, 272 KB, did not fit after the first five), the heap keeps 1.2 MB | this project |

To make one: edit inside `engine/runtime/`, then from the repo root
`git -C engine/runtime diff > engine/patches/NN-name.patch` and add the header lines. Check the later
patches still apply (`tools/setup.sh` re-applies the whole stack).
