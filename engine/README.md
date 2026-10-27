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
| 04-pmfhl-pipeline1 | `pmfhl.*`/`pmthl.lw` with LO1/HI1 (the R5900's second multiply pipeline), correct word order. Metrowerks `__muldi3` (mult, multu1, madd, pmfhl.lw, pcpyud) returned 0, so `strtol("505")` gave 5 and the DISK.MAP table stopped at 5 files. Recompiler + macros: rebuild `ps2_recomp`, regenerate, full rebuild. Test: `tests/pmfhl_muldi3_test.cpp` | this project (same class of bug as Killzone's 0010) |
| 05-sif-ee-to-iop-commands | EE `sceSifSendCmd` reaches the IOP: the IOP sifcmd `sceSifAddCmdHandler`/`RemoveCmdHandler`/`SetCmdBuffer`/`SetSysCmdBuffer` are implemented (were no-ops), and the EE call reads args 5/6 from `t0`/`t1`, DMAs the extra data into IOP RAM, fills the SIF header and runs `handler(packet, data)` on the emulated IOP (as EE-to-IOP RPC does). FMOD.IRX's EE<->IOP channel never answered before: the game waited on its reply semaphore under the loading bar | this project |

To make one: edit inside `engine/runtime/`, then from the repo root
`git -C engine/runtime diff > engine/patches/NN-name.patch` and add the header lines. Check the later
patches still apply (`tools/setup.sh` re-applies the whole stack).
