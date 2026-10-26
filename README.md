# Jackass PS2 Recompiled

The PlayStation 2 **Jackass: The Game** (Sidhe Interactive / Red Mile Entertainment, 2007, `SLUS-21627`),
statically recompiled to run natively on **Linux first** (x86-64, then ARM64), then Windows.

> Unofficial. **No game data included.** Bring your own PS2 disc. Releases, when there are any, are source
> only: you build from your own disc.

## What it is

A **static recompilation**: the game's Emotion Engine (MIPS R5900) code is translated to C++ ahead of time with
[PS2Recomp](https://github.com/ran-j/PS2Recomp), and a runtime stands in for the PS2. Not an emulator of the
CPU, not a decompilation. The runtime is the one the [Urban Reign PC port](https://github.com/thiagordsfx/urban-reign-recomp)
built on PS2Recomp: the game's own IRX modules (pad, memory card, FMOD sound) run on an R3000A interpreter,
VU1 microcode is recorded and compiled ahead of time, movies go through an emulated IPU, and the picture is
drawn by **PCSX2's hardware GS as a library**, on Vulkan on Linux, so internal resolution, filters and texture
packs work as in PCSX2. A native renderer is a later phase, pass by pass over that one.

The repository is shaped like [Vnnc1/gow-native-pc](https://github.com/Vnnc1/gow-native-pc): one
[game profile](games/jackass/game.toml) holds every game-specific value, the runtime is a pinned checkout
([engine/runtime.toml](engine/runtime.toml)) with numbered patches, and the conventions come from
[KIexster/god-of-war-recomp](https://github.com/KIexster/god-of-war-recomp) and our own Xbox 360 recomps,
[fear360-recomp](https://github.com/Juansolo457/fear360-recomp) and
[graw360-recomp](https://github.com/Juansolo457/graw360-recomp). The runtime is brought up **bottom up**: each
hardware layer is run on Jackass, compared with PCSX2, then patched, before the next one. Why these choices:
[docs/REFERENCES.md](docs/REFERENCES.md).

## Status

**Planned: recon done, nothing recompiled yet.** The USA disc is extracted and characterised in
[docs/FINDINGS.md](docs/FINDINGS.md): one stripped Metrowerks-built ELF with no code overlays, Sidhe's own
"Mab" engine on RenderWare-format data, Lua 5.0.2 scripts, ODE physics, FMOD audio on the IOP and Sony
`.pss` movies. Next: the runtime checkout and its first build, then the function map (Ghidra) and the Sony
SDK bindings. [docs/HANDOFF.md](docs/HANDOFF.md) is the current state;
[docs/PLAN.md](docs/PLAN.md) the layers and their exit criteria.

- [docs/SETUP.md](docs/SETUP.md): Linux toolchain and build from your own disc
- [docs/HANDOFF.md](docs/HANDOFF.md): current state, how things work, where things live
- [docs/PLAN.md](docs/PLAN.md): the bottom-up layers to the title screen, then play, then speed
- [docs/FINDINGS.md](docs/FINDINGS.md): what the disc and the executable are
- [docs/REFERENCES.md](docs/REFERENCES.md): every PS2 recomp this is modelled on, and the two runtime styles
- [docs/STEAMDECK.md](docs/STEAMDECK.md): what a Steam Deck test build needs

## Build and run (Linux)

[docs/SETUP.md](docs/SETUP.md) has the details. In short, once the pipeline exists:

```bash
tools/setup.sh                                  # runtime checkout + patches; builds ps2_recomp and libpcsx2gs.so
tools/extract.sh /path/to/your/Jackass.chd      # CHD or ISO -> game/
python3 -I tools/identify.py game               # is this the supported disc?
tools/generate.sh && tools/build.sh             # recompile, build (not written yet)
tools/launch.sh                                 # play (not written yet)
```

Supported disc: USA, `SLUS_216.27` (the profile records its CRC and code hash; `identify.py` checks them).

## Layout

```
games/jackass/   game.toml: every game-specific value (ELF, hashes, disc layout, middleware, optimize script)
engine/          runtime.toml (which runtime, pinned) + patches/NN-*.patch (our changes, with origin headers)
recomp/          PS2Recomp config and the Ghidra function map (to come)
src/             our host code: main, disc check, SDK HLE bindings, hooks (to come)
tools/           setup, extract, identify, profile, ISO/CHD readers, audit
docs/            setup, plan, handoff, findings, references
game/            your extracted disc (ignored)
engine/runtime/  the runtime checkout (ignored); generated/, data/, build/ (ignored)
private/         your disc images, traces and captures (ignored)
```

## Legal

- No assets, executables, generated code or proprietary code are distributed. Never attach builds or game files
  to a release. Before pushing, run `python3 -I tools/audit_repo.py` (CI runs it too).
- Our own tools, docs and glue: **MIT** ([LICENSE](LICENSE)). The runtime (Urban Reign port, PS2Recomp,
  PCSX2) is **GPL-3.0**, and so are our patches and host code on it and the program the build produces
  ([NOTICE](NOTICE), full text in [LICENSES/](LICENSES/)).
- Jackass is a trademark of MTV Networks / Paramount. Not affiliated with Paramount, Red Mile Entertainment,
  Sidhe or Sony Interactive Entertainment.

## Credits

- Sidhe Interactive and Red Mile Entertainment: the game
- ran-j and contributors: [PS2Recomp](https://github.com/ran-j/PS2Recomp)
- thiagordsfx: the [Urban Reign PC port](https://github.com/thiagordsfx/urban-reign-recomp), whose runtime and
  Linux build this stands on; the [PCSX2](https://github.com/PCSX2/pcsx2) team: the GS and the reference
- Waffle565, KIexster, YYOzcan, Vnnc1, drakolordx7: the God of War and Killzone ports this learned from
- Built with [Claude Code](https://claude.com/claude-code)
