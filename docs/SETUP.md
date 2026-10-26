# Setup: build Jackass PS2 Recompiled from your own disc (Linux)

Nothing is buildable yet (see [HANDOFF.md](HANDOFF.md)). This is the intended path; it is kept
current as the scripts land.

## Requirements
- Linux, x86-64 or ARM64 (Debian/Ubuntu, Arch and SteamOS are the tested targets once there are
  any). On Windows, WSL2 Ubuntu works for building; running the game wants a real Linux desktop
  or WSLg with Vulkan.
- `git`, `python3` (3.10+), `clang` 17+ (or the LLVM 20 that `tools/setup.sh` fetches), `cmake`
  3.25+, `ninja`, the Vulkan SDK or `libvulkan-dev` + `glslc`/`glslangValidator`, SDL3 (built by
  the project if not installed).
- `chdman` (from MAME: the `mame-tools` or `mame` package, or a MAME release) to convert your CHD
  to an ISO. A plain ISO/BIN dump works without it.
- Your own PS2 disc, dumped to CHD or ISO. Supported: the USA release (the build checks the
  ELF's SHA-256, recorded in [FINDINGS.md](FINDINGS.md)).
- Optional but recommended for development: PCSX2, the reference for every layer's test.

## Steps
```bash
git clone https://github.com/Juansolo457/jackass-ps2-recomp
cd jackass-ps2-recomp
tools/setup.sh                                   # pins PS2Recomp into third_party/, checks tools
tools/extract.sh /path/to/Jackass.chd            # CHD -> private/jackass.iso -> port/assets/
tools/build.sh -j 14                             # ps2xAnalyzer -> ps2xRecomp -> cmake
tools/launch.sh                                  # play
```

`tools/extract.sh` accepts an `.iso` too, and `tools/iso9660.py list <iso>` shows what is on the
disc without extracting it.

## What each step does
- **setup.sh**: clones `ran-j/PS2Recomp` at the pinned commit (`third_party/PS2Recomp.commit`),
  applies `tools/patches/*.patch`, builds its tools, and refuses to continue if a required
  program is missing. It never downloads anything that isn't listed in the script with its
  expected hash.
- **extract.sh**: `chdman extractdvd` into `private/`, then `tools/iso9660.py extract` into
  `port/assets/`, then hashes the ELF and compares it with FINDINGS.md.
- **build.sh**: runs the analyzer when `port/jackass.toml` is older than the ELF or missing,
  then the recompiler into `port/generated/`, then CMake + Ninja into `port/out/`.
- **launch.sh / smoke.sh**: run the built program; smoke runs headless for N seconds and writes
  `port/logs/`.

Never copy game files into tracked folders; `python3 -I tools/audit_repo.py` tells you if git
would publish any.
