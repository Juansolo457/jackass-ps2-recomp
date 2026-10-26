# Setup: build Jackass PS2 Recompiled from your own disc (Linux)

Nothing plays yet (see [HANDOFF.md](HANDOFF.md)). This is the intended path; it is kept current as the pieces
land. The build follows the Urban Reign PC port's Linux build (its `docs/LINUX.md`), whose checkout is the
runtime here.

## Requirements
- Linux, x86-64 (ARM64 later). On Windows, WSL2 Ubuntu builds everything; playing wants a Linux desktop or WSLg
  with Vulkan. What the development machine uses (Ubuntu 26.04 under WSL2):
  ```bash
  sudo apt install clang lld cmake ninja-build ccache pkg-config python3 git mame-tools \
       libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev libxext-dev libxfixes-dev libgl-dev \
       libvulkan-dev vulkan-tools libshaderc-dev libshaderc1 libpng-dev libasound2-dev
  ```
  (the X11 and GL headers are for raylib's GLFW window, Vulkan and shaderc for PCSX2's GS, libpng for texture
  packs; `mame-tools` gives `chdman`, only needed for CHD dumps.) Python 3.11+ for `tools/profile.py`.
- Your own PS2 disc, dumped to CHD or ISO. Supported: the USA release (`SLUS_216.27`; `tools/identify.py`
  checks the executable against [`games/jackass/game.toml`](../games/jackass/game.toml)).
- About 12 GB free: the ISO (4.2 GB), the extracted disc (2.6 GB), the runtime checkout and the build.
- For development: PCSX2 (the oracle every layer is checked against) and Ghidra 12 with the
  ghidra-emotionengine-reloaded extension (the function map).

## Steps
```bash
git clone https://github.com/Juansolo457/jackass-ps2-recomp
cd jackass-ps2-recomp
tools/setup.sh                                   # runtime checkout (engine/runtime.toml) + patches; builds ps2_recomp and libpcsx2gs.so
tools/extract.sh /path/to/Jackass.chd            # CHD -> private/jackass.iso -> game/
python3 -I tools/identify.py game                # which disc this is, and whether the port is for it
# not written yet:
tools/generate.sh                                # ps2_recomp with recomp/jackass.toml -> generated/
tools/build.sh                                   # cmake --build build/linux (the game + libpcsx2gs.so)
tools/launch.sh                                  # play
```

`tools/extract.sh` accepts an `.iso` too, and `tools/iso9660.py list <image>` shows what is on the disc
without extracting it. CD-type CHDs (made from a cue/bin, as Redump-verified PS2 dumps often are) come out of
`chdman extractdvd` as raw 2448-byte frames; the script detects that and rewrites them as a plain ISO
(`tools/iso9660.py toiso`). About 7 GB is needed while it runs; the raw file is deleted at the end.

## What each step does
- **setup.sh**: clones the Urban Reign checkout at the pinned commit into `engine/runtime/`, applies
  `engine/patches/*.patch` in name order (refuses to continue if one does not apply), then configures this
  repository's `CMakeLists.txt` (Clang, LLD, Ninja, `build/linux`) and builds the recompiler (`ps2_recomp`)
  and PCSX2's GS (`libpcsx2gs.so`). Downloads: the git clone and the runtime's own CMake FetchContent
  dependencies (raylib, SDL3, fmt, toml11, ...).
- **extract.sh**: `chdman extractdvd` into `private/`, then `tools/iso9660.py extract` into `game/`, then
  hashes the ELF and compares it with FINDINGS.md.
- **identify.py**: SYSTEM.CNF → profile; the ELF's PCSX2 CRC → edition; the SHA-1 of the profile's code section
  (`main` for this Metrowerks-linked ELF) → compatible or not.
- **generate.sh** (to write): fills `recomp/jackass.toml` (`@ELF@`, `@MAP@`, `@OUT@`) and runs `ps2_recomp`
  into a staging folder, then copies only changed files into `generated/` so rebuilds stay incremental (as
  Urban Reign's `tools/generate.py` does).
- **build.sh / launch.sh** (to write): `cmake --build build/linux`; the game runs with the ELF's folder
  (`game/`) as the CD root and a PCSX2-compatible memory card next to it.

Steam Deck: [STEAMDECK.md](STEAMDECK.md) (a container build for SteamOS's libraries, bundled `.so`s, the
private package).

Never copy game files into tracked folders; `python3 -I tools/audit_repo.py` tells you if git would publish
any.
