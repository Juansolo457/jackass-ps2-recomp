# References

What this project is modelled on and where to look things up. Read in full on 2026-10-26 unless
marked otherwise (READMEs, agent guides, architecture docs, patch indexes, build scripts and file
trees). Note the commit when copying anything; everything in the PS2Recomp family is GPL-3.0.

## The PS2Recomp family, and which one fits Jackass

Every PS2 native port of 2026 is built on **ran-j/PS2Recomp** (https://github.com/ran-j/PS2Recomp,
GPL-3.0: `ps2xAnalyzer` ELF → TOML, `ps2xRecomp`/`ps2_recomp` TOML + ELF + function map → one C++
function per MIPS function, `ps2xRuntime` + `ps2EntryRunner` the program, `ps2xIOP` the IOP
interpreter/HLE, `ps2xTest` the suite). They split into two runtime styles:

| | **Native-hardware runtime** (God of War family) | **PCSX2-as-library runtime** (Urban Reign, Killzone) |
|---|---|---|
| GS | Waffle565's OpenGL 4.3 render-target renderer, shaped by God of War's draws | PCSX2's hardware GS built as a library (`pcsx2gs.dll` / `libpcsx2gs.so`): DX11 on Windows, **Vulkan on Linux**; upscaling, filters, HD texture packs, GameIndex fixes for free |
| VU1 | microcode recorded at run time, compiled ahead of time to C++; interpreter for unseen code | same capture + AOT (`vu1_recomp`); Killzone also links PCSX2's microVU for VU0 |
| IOP | the game's IRX modules compiled ahead of time to C++ (dumped on a first run) | **the original IRX modules interpreted** on an R3000A core (Urban Reign runs NUSOUND, CRI ADX, PADMAN, MCMAN); Killzone adds PCSX2's SPU2 |
| Sound | a native sound engine driven by the game's LIBSD / 989snd calls | the IRX sound driver itself, SPU2 emulated |
| Movies | libmpeg2 (or FFmpeg) behind `sceMpeg*` HLE | emulated IPU (Urban Reign's Sofdec videos) or libmpeg HLE (Killzone) |
| Linux | Tobiichi (raylib/GLFW GL window, EGL patch), Vnnc1 is Windows only | Urban Reign: done, `.deb` and `.tar.gz` releases, Clang build in ~4 min |
| Fit for Jackass | needs FMOD's SIF protocol HLE'd, a GS shaped by another game, GCC-shaped function maps | FMOD's IRX just runs; libipu `.pss` movies on the emulated IPU; SDK 3.0 signatures already solved; Metrowerks map via Ghidra |

**Recommendation (2026-10-26, pending the user's choice):** follow **Urban Reign** for the runtime
(PS2Recomp + PCSX2 GS on Vulkan + IOP interpreter), **Vnnc1** for the repository shape (per-game
profile, numbered patches with origin headers, disc identify/prepare), and **KIexster/Waffle565**
for conventions and the PCSX2 verification method. A native renderer stays a later phase, as it
did for GRAW: the emulated GS first, measured, then replaced pass by pass if the hardware is the
limit ([[incremental-over-rewrite]]).

## Urban Reign PC port (thiagordsfx), the closest model
https://github.com/thiagordsfx/urban-reign-recomp (GPL-3.0; Windows + Linux; 1.4.0 released,
60 fps 8-fighter brawls at up to 8x; SLUS-21209, SDK 2.8). Read: README, docs/LINUX.md,
docs/ADVANCED.md, thirdparty/README.md, tools/find_sdk_functions.py, tools/ghidra_functions.py,
tools/linux/install_deps.sh, the tree.
- **Layout**: `src/` the port (`main.cpp`, disc check by ELF SHA-256, SDK HLE bindings, hooks,
  profilers), `recomp/` (`urban.toml`, `urban_functions.csv` from Ghidra), `runtime/` (PS2Recomp's
  recompiler, runtime, IOP and tools with the port's changes, documented in `runtime/README.md`),
  `thirdparty/pcsx2` (only the GS files PCSX2's build needs, at commit `2954ebe`, layout preserved
  so a newer PCSX2 copies over) + `thirdparty/pcsx2-gs` (their wrapper with a C API
  `include/pcsx2gs_api.h`, host stubs, shaders, shader cache), `tools/` (Ghidra headless function
  export, SDK finder, VU disassembler, VIF chain decoder, GS VRAM to PNG, autotest driver that
  recognises screens and navigates to a fight, PINE client for PCSX2 RAM), `docs/status/data.toml`
  → status map SVG of every Sony library and hardware component, `docs/PROGRESS.md` (log),
  `docs/ROADMAP.md`, `docs/ENV.md`.
- **Function map**: `tools/ghidra_functions.py` imports the ELF headless into Ghidra 12 with the
  **ghidra-emotionengine-reloaded** extension (language `r5900:LE:32:default`), exports with
  PS2Recomp's `ExportPS2Functions.java`, keeps only `FUN_*` (drops ~33k code labels), drops starts
  in delay slots and known bad splits. The recompiler merges its own function finder with the map.
- **SDK functions in a stripped ELF**: `tools/find_sdk_functions.py` matches normalized instruction
  sequences (jump targets and 16-bit immediates masked) against **Shadow of the Colossus's
  symbol-bearing SDK 3.0 ELF**: exact unique match, then fuzzy near predicted neighbours (libraries
  keep object order), then in-order fill between anchors, then libcdvd by RPC command number;
  syscall wrappers by number. Output `sdk_functions.inc` → HLE bindings at start-up. **Jackass is
  SDK 3.0 (IOPRP300), the same as the reference: this should match better than it did for Urban
  Reign's 2.8.**
- **Linux** (docs/LINUX.md, seven phases, all done): Clang + LLD + Ninja into `build/linux`;
  MSVC code model flags on every target (`-msse4.1 -fno-strict-aliasing -fwrapv -ffp-contract=off`,
  generated code `-w`, `register_functions.cpp` at `-O0`); raylib/GLFW X11 window (XWayland on
  Wayland), SDL3 for controllers only; `libpcsx2gs.so` on Vulkan with shaders compiled by shaderc
  at run time (`libshaderc_shared.so.1` or Debian's `libshaderc.so.1`), rendered into an X11 child
  window; 16 MB thread stacks via `pthread_setattr_default_np`; crash backtraces; mods via
  `dlopen`; MTVU on with PCSX2's GS. Without `libpcsx2gs.so` the software GS is a stand-in at 2–3
  images/s. No host vsync lock on Linux yet. Release built in the Steam Runtime (g++ 14) with
  podman/docker: `python3 build.py release`. Whole generated code compiles in ~4 min with Clang 19
  on 12 threads (over an hour with MSVC). Dependencies: `tools/linux/install_deps.sh`
  (clang lld ccache, X11 headers, libgl, libvulkan-dev vulkan-tools libshaderc-dev, libpng-dev).
- **Movies**: Sofdec on the emulated IPU (`URBAN_FFMPEG=OFF` on Linux). **Progressive scan** forced
  (480p) for 60 fps. Widescreen: the game's own 16:9 mode. Save states F5/F9. PCSX2-compatible
  memory card.

## Killzone (drakolordx7), the other PCSX2-as-library port
https://github.com/drakolordx7/KillzoneRecomp (GPL-3.0; Windows only; binary releases; SCUS-97402
and SCES-52893; 120+ fps, mouse aim, ultrawide). Read: README, patches/README.md, docs/findings.md.
- `ext/PS2Recomp` = their `killzone` branch of ran-j at `75d729c` with 12+ documented patches;
  `ext/kzgs`, `ext/kzvu`, `ext/kzipu`, `ext/kzspu2` = **PCSX2's GS renderer, microVU, IPU and SPU2
  as libraries** behind shims (PCSX2 at `646df006a4`); FFmpeg for libmpeg HLE. 20,000 generated
  C++ files; Ghidra's export names 65k standalone blocks `entry_*` (patch 0001 fixes their resume
  points).
- **Patch index is a bug catalogue every PS2 port hits**: `sceSifGetOtherData` a no-op, `WaitSema`
  / `WaitEventFlag` outside a thread faking success, VIF1 DIRECT → IMAGE continuation shifting
  uploads by 8 bytes (garbled fonts), LQ/SQ not forcing quadword alignment (QFSRV idiom), `SQRT.S`
  reading the wrong register, `RSQRT.S` as 1/sqrt, MMI lane errors (PEXEW, PEXEH, PEXCH, PEXCW,
  PREVH, PMULTH, PMFHL.SH), VIF1 UNPACK semantics (WL=0, fill mode, V2/V3/V4-5, STMOD 3, masks),
  DMA chains cut at 4096 tags, scratchpad chain-mode DMA, SPR bit in addresses, PS2 float semantics
  (no Inf/NaN, x/0 = ±max, CVT.W.S truncates), VCALLMSR start address, yield/return confusion in
  `dispatchGuestBranch` (random crashes, `PS2X_STRESS_YIELD` reproduces), runtime arena inside the
  game's heap, IOP import decode cache, IOP batched advance. `PS2X_HEADLESS=1` with periodic PNG
  shots for automated runs. `docs/findings.md` shows the reverse-engineering style: frame timer
  fields, vblank handlers, instruction patches for high refresh, PINE savestate comparisons.

## God of War family (native-hardware runtime)
- **Vnnc1/gow-native-pc**: https://github.com/Vnnc1/gow-native-pc (GPL-3.0, created 2026-10-25,
  Windows x64 only, AVX2). Not a runtime: an **installer launcher (Qt 6) + one-click pipeline +
  multi-game profiles** over the Tobiichi runtime, pinned in `engine/runtime.toml`
  (YYOzcan/Tobiichi-Port `471c831`, 2026-10-16) with `engine/patches/01`–`16` applied in name
  order, each headed by what/why/origin (origins: Waffle565 CPU speed-ups, the God of War II port's
  GS upscaling fixes, Killzone's `0017` "register locals" codegen (−22 % EE time) and `0028` IOP
  heap reuse, rac-rs's VU clean-operand analysis, their own clang/llvm-mingw build (15 min vs
  45–60 MSVC, PGO), VU1 block chaining, hidden-window recording runs). Read: README, AGENTS.md,
  CREDITS.md, docs/adding-a-game.md, docs/architecture.md, engine/README.md,
  docs/research/ps2-ports-review-2026-10-25.md, docs/tested-hardware.md, games/gow1/game.toml,
  tools/disc/{identify,discfs,prepare}.py.
  - **`games/<id>/game.toml`** is the one place for game-specific values: `[executable]` name,
    serial, PCSX2 CRC (XOR of the ELF's 32-bit words), `.text` SHA-1 (editions whose code matches
    recompile to the same program); `[runtime]` paths of the template TOML, function map,
    overrides, VU1/IOP generators, VU1 heads file; `[disc]` TOC/PAK names, IOP module dir, text
    files, movie extensions; `[optimize]` a timed pad script that reaches gameplay for the VU1/IOP
    recording run; `[[editions]]` and `language_hints` for fan translations.
  - **docs/adding-a-game.md** is the recipe for a new game, in order: identify the disc (CRC,
    `.text` SHA-1) → function map (Ghidra + PS2Recomp's analyzer + Waffle565's
    `find_functions.py`) → recompiler config (stubs, MMIO tables, patches) → overrides (God of
    War's: ~2,000 lines for IPU/MPEG, pad, memory card, VBlank waits, widescreen) → runtime fixes
    as patches → disc layout → optimize script → `status = "playable"` only when a scripted run
    reaches gameplay on AMD and NVIDIA. God of War II is `planned` there with nothing of steps 2–5.
  - Contracts worth copying: pipeline output protocol (`=== step ===`, `@@progress`, `@@status`),
    overrides registered by ELF file name with the ELF's folder as CD root and `mc0/` the card,
    `.disc_layout` listing every file by sector.
  - Their review of the other ports (docs/research/ps2-ports-review-2026-10-25.md) is a ranked
    performance backlog: sound mixer in blocks, COP0 Count on the EE clock (a stalled `mfc0 Count`
    made a per-frame budget loop do all work at once), IOP heap reuse, VU1 superblocks,
    `/fp:precise` A/B, clang builds.
- **YYOzcan/Tobiichi-Port**: https://github.com/YYOzcan/Tobiichi-Port (GPL-3.0; **Linux and
  Windows**; the full runtime checked in under `PS2Recomp/`, Waffle565's + KIexster's work merged,
  LightVelox's SotC OpenGL backend; Qt 6 launcher; widescreen Hor+; cheats; mouse lock-on;
  `android/` and `vita/` folders exist). Read: README, instalar.sh, run_gow.sh, the runtime CMake.
  `instalar.sh` is the Linux pipeline in one file: extract with `--layout`, `IOP_MOD/` copies of the
  IRX, configure (`PS2X_BUILD_STUDIO/ANALYZER/TEST=OFF`, unity batch 8, LTO jobs by RAM), build
  `ps2_recomp`, fill the template, copy generated code into `ps2xRuntime/src/runner/`, build
  `ps2EntryRunner`, then a 240 s scripted run with `GOW_VU1_CAPTURA` + `PS2X_IOP_DUMP_MODULES`
  and a rebuild with the native VU1/IOP. raylib window, `PS2X_GS_WORKER=1`. Measured on Linux:
  RTX 4050 laptop 2x 60 fps, Radeon 680M 1x 50–60 fps.
- **KIexster/god-of-war-recomp**: https://github.com/KIexster/god-of-war-recomp (GPL-3.0). The
  pipeline that first reached gameplay; since 2026-10-15 Waffle565's runtime as a 2.5 MB patch
  over ran-j `c5a9d02`, then per-topic patches; CI builds the runtime suite on Linux (GCC,
  `-DPS2X_BUILD_STUDIO=OFF -march=x86-64-v2`). Conventions (AGENTS.md): overrides call the
  original for anything not replaced and respect checkpoint resumes; diagnostics behind env vars
  with a log tag, removed when solved; a regression test per runtime change; `// GOW-Port:`
  markers; an investigation log never pruned; status map from TOML. **PCSX2 as oracle**
  (docs/COMPARACION_PCSX2.md): replay a frame's VIF1 chain from a savestate (`GS.bin` VRAM = the
  4 MB before the last 0x54 bytes; VIF1 regs in `eeHwRegs.bin` at 0x3C00) through the runtime's
  VIF1/VU1/GS with no EE. Found: a stubbed software-double `sin` returning its argument (Sony's
  libm: arg `$a0`, result `$v0`; **never stub libm**), scratchpad chain DMA missing, the first PSS
  block demuxed before `sceMpegCreate`.
- **Waffle565/God-Of-War-Native-Port**: https://github.com/Waffle565/God-Of-War-Native-Port
  (`main` docs/tools/overrides; `runtime` branch = the GPL runtime). Native GS (render targets,
  paletted textures as index + palette, channel shuffles, aliased Z, CRTC merge), ~500 VU1
  microprograms AOT "per instruction pair, verified against an interpreter A/B", 8 IRX AOT (boot
  95 s → 20 s), native sound/pad/card, libmpeg2 movies, 60 fps all zones, exact speed. Tools:
  `zones.py`, `movies.py`, `savetest.py`, `find_functions.py`, `dis.py`/`irxdis.py`, `gsdump_*`.
  Next: Switch (title 25 fps, gameplay 9–12 on Cortex-A57: a data point for ARM64).
- Others: igormcsouza (Linux, Vulkan compute GS; not read), CodeAbhi826 (Android; not read),
  cxldsakeb/GoW2-nativo-PS2 + DaniSBR1/PS2Recomp `godofwar2` (GS upscaling fixes), LightVelox
  SotC fork `ac9efa0` (OpenGL GS, EE fixes), sal063 Ace Combat 5.

## Other PS2 ports
- **AsobiCodes/rac-rs**: https://github.com/AsobiCodes/rac-rs (GPL-3.0). Ratchet & Clank in
  **Rust**: static recompilation to Rust on a Rust PS2 CPU core, native everything else, playable
  start to credits with modern graphics options; tests play the same frames on both versions and
  compare memory. Windows only. Its `tools/vu/vuclean.py` (clean-operand analysis) was adopted by
  Vnnc1. A different toolchain; a model for test discipline, not for code.

## PS2 decompilations (for how people read PS2 code, not for code)
- Sly Cooper: https://github.com/theonlyzac/sly1
- PaRappa the Rapper 2: https://github.com/raphaelthegreat/parappa2 (progress on decomp.dev)
- bigianb/darev: https://github.com/bigianb/darev

## Hardware references and tools
- PCSX2: https://github.com/PCSX2/pcsx2 (GPL-3.0). The oracle: savestates, GS dumps, PINE
  (`tools/pine.py` in Urban Reign and Killzone read game RAM live), EE/IOP console log.
- Ghidra 12 + JDK 21 + https://github.com/chaoticgd/ghidra-emotionengine-reloaded (R5900
  language) for the function map; PS2Recomp ships `ExportPS2Functions.java`.
- Sony's EE / EE Core ISA / GS / VU manuals (cite sections, don't copy); ps2tek
  https://psi-rockin.github.io/ps2tek/.

## Our own
- graw360-recomp: https://github.com/Juansolo457/graw360-recomp (conventions, scripts, audit,
  handoff; the "emulated renderer first, native D3D12 later with a fallback" path this plan copies)
- fear360-recomp: https://github.com/Juansolo457/fear360-recomp (source-only release recipe)

## Listing
- recomp.fyi: https://recomp.fyi/ reads `.recomp.json` at the repo root daily (spec:
  https://recomp.fyi/spec); our row was created through
  https://github.com/neurocontrarian/recomp-board/issues/263.
- PlayPorted: https://playported.com/ (KIexster is listed there too).

## Game
- Wikipedia: https://en.wikipedia.org/wiki/Jackass:_The_Game (Sidhe for PS2/PSP, Red Mile
  publisher, NA PS2 release 2007-09-24).
- Developer Q&A, Worthplaying 2007-08-09:
  https://worthplaying.com/article/2007/8/9/interviews/44129-jackass-the-game-all-developer-qa/
