# Jackass PS2 Recompiled

The PlayStation 2 **Jackass: The Game** (Sidhe Interactive / Red Mile Entertainment, 2007),
statically recompiled to run natively on **Linux first** (x86-64 and ARM64), then Windows, with a
native renderer in place of the Graphics Synthesizer.

> Unofficial. **No game data included.** Bring your own PS2 disc. Releases, when there are any,
> are source only: you build from your own disc.

## What it is

A **static recompilation**: the game's Emotion Engine (MIPS R5900) code is translated to C++
ahead of time with [PS2Recomp](https://github.com/ran-j/PS2Recomp), and a game-specific runtime
stands in for the PS2's hardware (EE memory map and kernel, VU0/VU1, VIF/GIF DMA, GS, IOP, SPU2,
pad, memory card). Not an emulator, not a decompilation. The model is the 2026 wave of
**God of War** PS2 native ports built on PS2Recomp
([Waffle565/God-Of-War-Native-Port](https://github.com/Waffle565/God-Of-War-Native-Port) and its
forks: [KIexster](https://github.com/KIexster/god-of-war-recomp),
[igormcsouza](https://github.com/igormcsouza/god-of-war-recomp) with a Linux Vulkan compute GS,
[CodeAbhi826](https://github.com/CodeAbhi826/God-Of-War-Recomp) for Android/Vulkan,
[YYOzcan/Tobiichi-Port](https://github.com/YYOzcan/Tobiichi-Port)); the project conventions come
from our own Xbox 360 recomps, [fear360-recomp](https://github.com/Juansolo457/fear360-recomp)
and [graw360-recomp](https://github.com/Juansolo457/graw360-recomp).

The runtime is built **bottom up**, one hardware layer at a time, each verified against PCSX2
before the next is started: memory and ELF loading, the recompiled EE code and kernel syscalls,
DMA and the VIF/GIF paths, the GS (first a software rasterizer for correctness, then Vulkan), the
IOP side (CD-ROM, SPU2, pad), and only then the title screen. [docs/PLAN.md](docs/PLAN.md) has
the layers and their exit criteria.

## Status

**Phase 0: recon.** Nothing boots yet. The disc is in hand (USA, CHD, Redump-verified); the next
steps are to extract it, identify the executable (`SLUS_xxx.xx`), its IRX modules and any code
overlays, and run PS2Recomp's analyzer over it. [docs/HANDOFF.md](docs/HANDOFF.md) is the
current state.

- [docs/SETUP.md](docs/SETUP.md): Linux toolchain and build from your own disc
- [docs/HANDOFF.md](docs/HANDOFF.md): current state, how things work, where things live
- [docs/PLAN.md](docs/PLAN.md): the bottom-up layers to the title screen, then play, then speed
- [docs/FINDINGS.md](docs/FINDINGS.md): what the disc and the executable are
- [docs/REFERENCES.md](docs/REFERENCES.md): the projects and documents this is modelled on

## Build and run (Linux)

[docs/SETUP.md](docs/SETUP.md) has the details. In short, once the pipeline exists:

```bash
tools/setup.sh                                      # PS2Recomp (pinned), clang, CMake, Ninja, chdman, Vulkan SDK
tools/extract.sh /path/to/your/Jackass.chd          # CHD -> ISO -> port/assets/
tools/build.sh                                      # analyze, recompile, build
tools/launch.sh                                     # play
```

Supported disc: USA (`SLUS_xxx.xx`; the ELF's SHA-256 is recorded in
[docs/FINDINGS.md](docs/FINDINGS.md) once extracted and the build checks it).

## Layout

```
port/        the PS2Recomp project: port/assets/ (your disc, ignored), port/jackass.toml (analyzer
             config: function hints, stubs, overlays), port/src/ our host code, port/generated/ (ignored)
native/      the native renderer (GS replacement): software rasterizer first, then Vulkan
tools/       setup, extract, build, launch, smoke, analysis tools, audit
docs/        setup, plan, handoff, findings, references
third_party/ the pinned PS2Recomp checkout and other sources tools/setup.sh fetches (ignored)
private/     your disc images, captures and logs (ignored)
```

## Legal

- No assets, executables, generated code or proprietary code are distributed. Never attach
  builds or game files to a release. Before pushing, run `python3 -I tools/audit_repo.py`
  (CI runs it too).
- Our own tools, docs and glue: **MIT** ([LICENSE](LICENSE)). Third-party code this repository
  carries or patches keeps its own terms, listed file by file in [NOTICE](NOTICE), full texts in
  [LICENSES/](LICENSES/).
- Jackass is a trademark of MTV Networks / Paramount. Not affiliated with Paramount, Red Mile
  Entertainment, Sidhe or Sony Interactive Entertainment.

## Credits

- Sidhe Interactive and Red Mile Entertainment: the game
- ran-j and contributors: [PS2Recomp](https://github.com/ran-j/PS2Recomp)
- Waffle565 and the God of War recomp forks: the runtime and renderer approach this follows
- The [PCSX2](https://github.com/PCSX2/pcsx2) team: the reference for every PS2 hardware question
- Built with [Claude Code](https://claude.com/claude-code)
