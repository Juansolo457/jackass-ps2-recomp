# Handoff: Jackass (PS2) native Linux port (2026-10-25)

Read [PLAN.md](PLAN.md) for the layers and exit criteria and [FINDINGS.md](FINDINGS.md) for the
disc and executable facts. This file is the state, the build/run detail and where things live.
Update it at the end of every session; the next model starts here, not from chat history.

## Where it stands
**Layer 0 (recon) done 2026-10-25, except the PCSX2 reference run.** The disc is extracted,
the executable identified and characterised (FINDINGS.md). Nothing is recompiled or built yet.

The user's decisions so far:
- Native **Linux** port first, then ARM64, then Windows.
- Build **bottom up**: each hardware layer verified against PCSX2 before the next (PLAN.md).
- Toolchain: PS2Recomp, following the God of War native ports; repo conventions from
  graw360-recomp and fear360-recomp.
- Linux build host: **WSL2 Ubuntu 26.04** on this PC (installed 2026-10-25, distro `Ubuntu`,
  user `jj`, default; systemd on). The repo is reached at
  `/mnt/c/Users/JJ-PC/source/repos/jackass-ps2-recomp`. Installed there: clang 21.1.8, lld,
  cmake, ninja, python3, mame-tools (chdman 0.285), libvulkan-dev, vulkan-tools, glslc,
  libsdl3-dev 3.4.2, p7zip. Run things with `wsl.exe -d Ubuntu -u jj -- bash -c '...'`.
- The CHD stays in the user's Downloads folder (read-only). The user OK'd reading it and
  extracting it with chdman (2026-10-25).
- The repo is **public** at https://github.com/Juansolo457/jackass-ps2-recomp (published
  2026-10-26 at the user's request). At each stopping point, update the project's row on
  **recomp.fyi**: editing `.recomp.json` at the root is enough, the board reads it daily. The
  row was requested through the manifest form, issue
  https://github.com/neurocontrarian/recomp-board/issues/263 (2026-10-26).

| Piece | State |
|---|---|
| `private/jackass.iso` (ignored) | plain 2048-byte ISO, 4.16 GB, from the CHD via `tools/extract.sh` |
| `port/assets/` (ignored) | 504 files, 2.6 GB, the whole disc; `SLUS_216.27` SHA-256 matches FINDINGS.md |
| `private/disc_listing.txt` (ignored) | `tools/iso9660.py list` output |
| `tools/audit_repo.py` | works; run on every commit so far |
| `tools/setup.sh` | rewritten for Route B (Urban Reign checkout, patches, builds `ps2_recomp` + `pcsx2gs`); **never run** |
| `CMakeLists.txt` | written, untested (see "Route B chosen") |
| `games/jackass/game.toml`, `tools/profile.py`, `tools/identify.py` | work; identify matched `game/` and the ISO |
| `tools/extract.sh` | **ran end to end** in WSL (chdman 1m37s + toiso/extract 1m05s). Handles CD-type CHDs |
| `tools/iso9660.py` | works: list/extract/cat/toiso, detects 2048/2352/2448-byte frame layouts |
| `tools/chd_info.py` | works (CHD v5 header + metadata) |
| `tools/build.sh`, `launch.sh`, `smoke.sh` | not written (need a PS2Recomp pin first) |
| `port/jackass.toml` | not written (output of `ps2xAnalyzer`, Layer 2) |
| `native/` | empty |

## What Layer 0 found that changes the plan (details in FINDINGS.md)
- **Single stripped ELF, no overlays** → plain PS2Recomp, no overlay fork.
- **Metrowerks CodeWarrior MIPS 2.4.1** compiler, not GCC → check the analyzer's function
  splitting against a disassembly early.
- **Sidhe "Mab" engine** reading RenderWare 3.7 stream files with its own loader; **Lua 5.0.2**
  scripts (precompiled `.luc`), **ODE** physics, **FMOD** audio (its own IOP module, SIF command
  protocol to HLE), Sony **libipu/sceMpeg** `.pss` movies (2.1 GB of the disc), libgraph GS
  path with VU1 microcode.
- File I/O goes through the game's own `DISK.MAP` (LBA table), so a host cdvd layer can serve
  reads straight from the ISO.
- `scripts/key_sequence/*.txt` are the developers' own input-replay scripts: the future
  autopilot for smoke tests.

## Blockers / needs the user
1. **PCSX2** for the oracle traces (not installed; its install needs an OK). Needed before
   Layer 1's exit test, not before the analyzer run.
2. Every build, codegen or run still needs an OK first.

## Model repo read (2026-10-26)
The user pointed at KIexster/god-of-war-recomp. Read in full; the lessons are in
[REFERENCES.md](REFERENCES.md) and the plan revision at the top of [PLAN.md](PLAN.md). Short
version: build on **Waffle565's runtime** (GPL-3.0, OpenGL 4.3, native VU1/IOP/sound/movies,
Linux via KIexster's EGL and GCC patches) and patch it for Jackass, layer by layer with PCSX2
checks; don't write the hardware again. `tools/setup.sh` now pins PS2Recomp at `c5a9d02` and
clones KIexster's repo as the patch source. NOTICE and LICENSES carry the GPL.

## Route B chosen and the repo reshaped (2026-10-26)
The user chose **Route B**: the Urban Reign PC port's runtime (PS2Recomp + PCSX2 GS on Vulkan, IRX
interpreted), with Vnnc1's repository shape. Done the same day, nothing built:
- `engine/runtime.toml` pins thiagordsfx/urban-reign-recomp `20b30fd` (2026-10-23); `engine/patches/` is empty.
- `games/jackass/game.toml`: the profile (ELF, CRC `0204033A`, `main` SHA-1, disc layout, middleware).
  `tools/profile.py` reads it; `tools/identify.py` matched both `game/` and the ISO to it.
- `CMakeLists.txt`: adds the checkout's `runtime/` and `thirdparty/pcsx2-gs` (maps `JA_*` options onto
  `URBAN_*`/`PS2X_*`), and `src/` once `src/CMakeLists.txt` exists. **Untested**: the checkout's CMake files
  may use paths relative to their own top level; the first `tools/setup.sh` run will tell, and any fix goes
  in as an `engine/patches/` patch.
- `tools/setup.sh` rewritten: tools check, clone + pin + patches, configure, build `ps2_recomp` and `pcsx2gs`.
- `port/` and `native/` are gone; the disc is in `game/` (the ELF's folder is the CD root, as the runtime
  expects); `.gitignore` and the audit cover `game/`, `data/`, `generated/`, `engine/runtime/`, `.NPS`,
  `.FSB`, `DISK.MAP`.

## Second model-repo pass (2026-10-26)
The user then pointed at Vnnc1/gow-native-pc. Read in full, plus what it credits: Tobiichi-Port,
Urban Reign PC port, Killzone recomp, rac-rs (REFERENCES.md). Result: a route decision is open
(PLAN.md, "Second revision"): **A** God of War native runtime, or **B** Urban Reign's
PCSX2-as-library runtime (recommended: Linux done, FMOD IRX interpreted as shipped, PCSX2 GS on
Vulkan, SDK 3.0 signature finder). Either way the repo takes Vnnc1's shape (per-game profile,
numbered patches with origin headers). `tools/setup.sh` still pins the Route A base (`c5a9d02` +
KIexster); it changes once the route is chosen.

Identifiers for the profile (computed 2026-10-26): PCSX2 CRC and the code-section SHA-1 are in
FINDINGS.md ("The executable").

## Steam Deck (2026-10-26)
The user wants to see the build on their Deck. [STEAMDECK.md](STEAMDECK.md): a native Linux build must be
made in the Steam Linux Runtime "sniper" container (or on the Deck in distrobox) so it runs on SteamOS's
glibc; bundle `libpcsx2gs.so`, SDL3 and shaderc; package like fear360's `tools/steamdeck/`. A checklist of
commands for the user to run on the Deck is in that doc; their output decides the packaging route.

## Next steps
1. `tools/setup.sh` in WSL (needs the user's OK: it clones and builds). Expect CMake fixes for the
   checkout's `runtime/` and `pcsx2-gs` built from our top level; each fix becomes
   `engine/patches/01-...patch`. Install the X11/Vulkan/shaderc dev packages from SETUP.md first.
2. Ask the user to install PCSX2 (the oracle) and Ghidra 12 + ghidra-emotionengine-reloaded (the
   function map).
3. Function map and SDK bindings (Layer 2): adapt the checkout's `tools/ghidra_functions.py` to
   `game/SLUS_216.27` → `recomp/jackass_functions.csv`; run its `tools/find_sdk_functions.py` with
   a symbol-bearing SDK 3.0 reference (Shadow of the Colossus's, as Urban Reign does; Jackass is SDK
   3.0 too) → `src/jackass/sdk_functions.inc`. Watch Metrowerks idioms the Ghidra pass may split
   wrongly; compare the count with the ~16.6k `jr $ra` sites.
4. `recomp/jackass.toml` modelled on the checkout's `recomp/urban.toml` (`auto_stub_by_name = false`,
   `direct_tail_calls = false`, Ghidra map merged); `tools/generate.sh` like their `generate.py`
   (staging dir, copy only changed files). First `ps2_recomp` run; count functions and "No exact
   recompiled function" cases.
5. `src/`: a `main.cpp` modelled on the checkout's `src/main.cpp` + `urban/game_disc.cpp` +
   `hle_bindings.cpp`, for Jackass; `src/CMakeLists.txt` from their `src/CMakeLists.txt`. First
   boot attempt with the software GS, then `libpcsx2gs.so`.
4. PCSX2 once installed: boot the ISO, save the title-screen frame and the EE/IOP log to
   `private/reference/`.
5. Layer 1 (memory map + ELF loader) with its test.

## How it is built and run
Not yet. The intended loop, once the scripts exist (all inside WSL):
```
tools/extract.sh /mnt/c/.../Jackass.chd     # done once; re-run only to redo port/assets
tools/setup.sh                              # PS2Recomp pin + build
tools/build.sh [-j 14]                      # analyze → recompile → cmake build
tools/smoke.sh                              # headless boot, log in port/logs/
tools/launch.sh                             # play (WSLg or a Linux desktop)
```

## Where things live
- `docs/`: this file, PLAN.md, FINDINGS.md, SETUP.md, REFERENCES.md.
- `tools/`: scripts above; `tools/patches/` for PS2Recomp patches (none yet).
- `port/`: the PS2Recomp project (assets, toml, src, generated).
- `native/`: the GS replacement (software rasterizer, then Vulkan).
- `private/` (ignored): the ISO, disc listing, later PCSX2 traces and captures.
- Sister repos: `../graw360-recomp` (scripts and docs to copy from), `../fear360-recomp`.
