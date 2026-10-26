# References

What this project is modelled on and where to look things up. The God of War entries were read in
full on 2026-10-26 (README, AGENTS.md, ARQUITECTURA.md, COMPARACION_PCSX2.md, FMV_Y_AUDIO.md, the
recompiler TOML, the CI workflow and the file trees); the rest are search summaries. Note the
commit when copying anything.

## The model: God of War on PS2Recomp

The user pointed at **KIexster/god-of-war-recomp** as the example to follow.

- **KIexster/god-of-war-recomp**: https://github.com/KIexster/god-of-war-recomp (GPL-3.0, Windows
  x64 primary, Linux x64 for the test suite; docs in Spanish, README in EN/ES/PT-BR; listed on
  recomp.fyi and PlayPorted). Boots, menus, new game and the first fight play; native VU1 and IOP;
  exact game speed; 60 fps "in progress". Since 2026-10-15 its base is Waffle565's runtime.
  - **Repo layout** (what we copy): `config/funcmap.csv` (6,414 functions: `Name,Start,End,Size`,
    Ghidra-exported), `config/recomp.template.toml` (PS2Recomp config with `@ELF@/@MAP@/@OUT@`
    placeholders: `stubs = ["sceMpegCreate@0x0026F2F8", ...]` for Sony library functions the
    runtime implements natively, `entry_points` for vtable-only methods the analyzer missed,
    instruction patches), `src/gow_overrides.cpp` (game-function replacements and diagnostics,
    registered with `PS2_REGISTER_GAME_OVERRIDE` for the ELF + entry), `patches/` (one patch per
    topic over the pinned PS2Recomp, applied in the order `scripts/compilar.ps1` lists; CI fails if
    one doesn't apply), `scripts/` (numbered: install tools, build, run 60 s with logs), `tools/`
    (`iso_extract.py --layout`, `vu1/vu1n_gen.py`, `iop/iopn_gen.py`, CI validators, status map
    generator), `tests/` (game-independent), `docs/estado/datos.toml` → generated status map SVG.
  - **Pipeline**: clone `ran-j/PS2Recomp` at `c5a9d02573410a2085a4b4b831b0b68ba3515440`, apply
    `patches/ps2recomp-waffle-runtime.patch` (the diff `c5a9d02..runtime` of Waffle565's branch,
    2.5 MB) then small per-topic patches (GCC portability, VU0 VF0/VI0 constants, VU1 native leak,
    EGL on Linux), build `ps2_recomp`, fill the TOML, generate ~6,400 C++ files, copy them plus the
    overrides into `ps2xRuntime/src/runner/`, build `ps2EntryRunner` (unity build + PCH; LTCG off,
    linking 6,400 files with it is unworkable). Optional: dump the IRX modules once at run time
    (`PS2X_IOP_DUMP_MODULES`), then `iopn_gen.py` compiles them to C++ for the next build; VU1
    microcode likewise (`GOW_VU1_MICROCODIGO`, `vu1n_gen.py`).
  - **Conventions worth copying** (AGENTS.md): call the original for anything an override doesn't
    replace and respect checkpoint resumes (`ctx->pc` != entry); diagnostics behind env vars with
    a `[gow-xxx]` log tag, removed when solved; every runtime behaviour change ships a regression
    test in `ps2xTest/` that fails without it; a `// GOW-Port:` marker on every change to upstream
    code; the investigation log (`docs/ESTADO.md`) is never pruned, only corrected; a status map
    regenerated from TOML on push.
  - **PCSX2 as oracle** (COMPARACION_PCSX2.md): extract a frame's VIF1 DMA chain from a PCSX2
    savestate (`GS.bin` holds VRAM in the 4 MB before the last 0x54 bytes; VIF1 regs in
    `eeHwRegs.bin` at 0x3C00) and replay it through the runtime's VIF1/VU1/GS with no EE: a correct
    image proves the GS path, a wrong one with the port's own chain points at the EE data. This
    found a stubbed double-precision `sin` returning its argument (Sony's libm is software double:
    arg in `$a0`, result in `$v0`; the runtime's float stubs used `$f12/$f0`) and a missing
    scratchpad DMA chain mode. Lesson: **never stub libm, and verify every stub's calling
    convention.**
  - **FMV** (FMV_Y_AUDIO.md): the game demuxes the first PSS block (with the MPEG-2 sequence header)
    before `sceMpegCreate`; the runtime must keep it. Audio bugs were IOP-emulator bugs
    (`sceSifGetOtherData` not copying, `WaitSema` outside a thread faking success).
- **Waffle565/God-Of-War-Native-Port**: https://github.com/Waffle565/God-Of-War-Native-Port (no
  license file on `main`; the `runtime` branch is a PS2Recomp fork and keeps GPL-3.0). The runtime
  everyone now builds on. `main` holds docs, tools, overrides and the function map; `runtime` goes
  into `ext/PS2Recomp-kl/`. Native replacements: EE recompiled (6.4k functions); ~500 VU1
  microprograms compiled ahead of time to C++ "per instruction pair, verified against an
  interpreter A/B"; GS as an **OpenGL 4.3 render-target renderer** (real GPU render targets,
  paletted textures as index + palette textures, channel shuffles, aliased Z and CRTC merge
  reproduced natively; 2x internal resolution, 16:9); the 8 IRX modules compiled ahead of time
  (boot 95 s → 20 s); SPU2 as a native sound engine driven by LIBSD calls; native pad and memory
  card; DMA packets handed straight to VU1 and GS (the recompiler turns DMA register, timer and GS
  display register accesses into native calls); disc files served at their original sectors
  (`.disc_layout`); FMV via libmpeg2 with sound. 60 fps in all tested zones, exact game speed, save
  and load verified. Tools: `zones.py` (load every save slot, walk, capture, judge fps),
  `movies.py`, `savetest.py`, `dis.py`/`irxdis.py`, `gsdump_*.py`. Next target: Nintendo Switch.
  Developed with Claude as co-author.
- Other God of War forks: **igormcsouza** (https://github.com/igormcsouza/god-of-war-recomp, Linux,
  Vulkan compute GS, not read), **CodeAbhi826** (Android/Vulkan, not read), **YYOzcan/Tobiichi-Port**
  (Linux+Windows OpenGL 4.3; KIexster reviewed it in `docs/REVISION_TOBIICHI.md`).
- Related PS2Recomp ports named in KIexster's credits: **thiagordsfx/urban-reign-recomp** (shared
  GS integration reference), **LightVelox/PS2Recomp** at `ac9efa0` (Shadow of the Colossus runtime
  fork: OpenGL GS backend, command queue, EE fixes for FPU, 64-bit branches, LQ/SQ, tail jumps,
  VU0 macro mode, long DMA chains).

## Toolchain
- **PS2Recomp**, ran-j: https://github.com/ran-j/PS2Recomp. **GPL-3.0.** Experimental PS2 static
  recompiler. Pipeline: `ps2xAnalyzer` (ELF → TOML config), `ps2xRecomp`/`ps2_recomp` (TOML +
  ELF + function map → C++, one literal C++ statement per MIPS instruction; MMI and VU0 macro
  mode; stubs bound by address for stripped games), `ps2xRuntime` (memory, syscalls, hardware;
  `ps2EntryRunner` is the program), `ps2xIOP` (IOP interpreter and HLE), `ps2xTest` (the runtime
  suite, 550 tests at KIexster's pin, buildable on Linux with GCC: `-DPS2X_BUILD_STUDIO=OFF`,
  `-march=x86-64-v2`).
- **PS2Recomp fork with overlays**, boubou666: https://github.com/boubou666/PS2Recomp. Not needed:
  Jackass has no overlays (FINDINGS.md).

## PS2 decompilations (for how people read PS2 code, not for code)
- Sly Cooper: https://github.com/theonlyzac/sly1
- PaRappa the Rapper 2: https://github.com/raphaelthegreat/parappa2 (progress on decomp.dev)
- bigianb/darev: https://github.com/bigianb/darev

## Hardware references
- PCSX2: https://github.com/PCSX2/pcsx2. GPL-3.0: read for behaviour, don't copy (Waffle565's
  runtime already carries PCSX2's EE interpreter and VU ops in `ee_ref/` and `vu_pcsx2/`, under
  the GPL). Its savestates, GS dumps and EE/IOP console log are the traces each layer is tested
  against.
- Sony's EE User's Manual, EE Core Instruction Set Manual, GS User's Manual, VU User's Manual
  (widely mirrored; cite the section, don't copy the text into the repo).
- ps2tek: https://psi-rockin.github.io/ps2tek/ (community hardware notes).

## Our own
- graw360-recomp: https://github.com/Juansolo457/graw360-recomp (conventions, scripts, audit, handoff)
- fear360-recomp: https://github.com/Juansolo457/fear360-recomp (source-only release recipe)

## Listing
- recomp.fyi: https://recomp.fyi/ reads `.recomp.json` at the repo root daily (spec:
  https://recomp.fyi/spec); our row was created through
  https://github.com/neurocontrarian/recomp-board/issues/263. KIexster's manifest uses
  `"system": "PS2"`, `"original": {"region", "serial"}`, `"toolchain": "Ps2recomp"`, plus `links`
  and `help` lists.
- PlayPorted: https://playported.com/ (KIexster is listed there too).

## Game
- Wikipedia: https://en.wikipedia.org/wiki/Jackass:_The_Game (Sidhe for PS2/PSP, Red Mile
  publisher, NA PS2 release 2007-09-24).
- Developer Q&A, Worthplaying 2007-08-09:
  https://worthplaying.com/article/2007/8/9/interviews/44129-jackass-the-game-all-developer-qa/
