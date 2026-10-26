# Steam Deck: what a test build needs

Written 2026-10-26, before anything is built. The goal: the user sees the build running on their Deck, as
the F.E.A.R. and GRAW 360 recomps do (those run as Windows builds through Proton; this one is a **native Linux
build**, so the path is different and simpler at run time, harder at packaging time).

## What the Deck is, for us
- SteamOS 3 (Arch-based, **read-only root**: no `pacman -S` into `/usr` without unlocking it; nothing we need
  should be installed system-wide). Zen 2 CPU, 4 cores / 8 threads, **x86-64 with SSE4.1 and AVX2**: the
  runtime's SSE4.1 code model is fine. RDNA 2 GPU with Mesa **RADV Vulkan**: what PCSX2's GS wants.
  1280×800 screen at up to 90 Hz (LCD) or OLED; `gamescope` compositor in Game Mode, KDE Plasma (Wayland) in
  Desktop Mode, both with **XWayland**, which the runtime's X11 window needs (Urban Reign's Linux build is X11
  only, XWayland on Wayland desktops).
- The user's Deck already runs the 360 recomps from `/home/deck/Games/` and `/home/deck/recomps/`, added as
  non-Steam games; SSH to it is an option the user has used before.

## The three things a Deck test needs
1. **A build that runs on SteamOS's libraries.** Urban Reign solved this for its Linux release: build inside the
   **Steam Linux Runtime 3.0 ("sniper")** container (g++ 14 there; glibc 2.31) with podman or docker
   (`python3 build.py release` → `.tar.gz`), so the binary runs on any glibc ≥ 2.31 distribution, SteamOS
   included. A WSL2 Ubuntu 26.04 build linked against its own glibc would **not** start on SteamOS
   (newer glibc symbols than the Deck has). So the Deck package comes from a container build, not the dev
   build. Alternatives, in order of preference:
   - a. Steam Runtime sniper container in WSL (`podman` is installable in Ubuntu; systemd is on) → portable
     tarball with `libpcsx2gs.so`, `libSDL3.so`, `libshaderc_shared.so.1` **bundled** next to the executable
     (RPATH `$ORIGIN` is already set in CMake). This is Urban Reign's recipe.
   - b. build **on the Deck** inside a `distrobox` Arch container (Desktop Mode; distrobox and podman are
     available on SteamOS without unlocking root): slow (4c/8t, the generated code is ~4 min on 12 fast
     threads, so maybe 15–20 min), but no glibc question at all. Good as a one-off check.
   - c. run the Deck test through the **Steam Linux Runtime** as the compatibility tool in Steam (Properties →
     Compatibility → "Steam Linux Runtime 3.0 (sniper)") with the sniper-built tarball: the same libraries
     the build saw, guaranteed.
2. **The game data next to the executable**: the extracted disc (`game/`, 2.6 GB) with the ELF at its root
   as the CD root, and a memory card file. Our rule stands: these go to the user's own Deck only, in a private
   package, never in a release ([[fear-release-source-only]]).
3. **A way to launch and look**: add the executable as a non-Steam game, START IN its folder, and the Deck's
   Performance Overlay (level 3 or 4) for fps and CPU/GPU load. Controls come through SDL3's Steam Deck
   HIDAPI driver in Desktop Mode and through Steam Input (as an Xbox-style pad) in Game Mode; both appear as
   one gamepad to the runtime. Logs come back over SSH or the SD card.

## Packaging plan (to build when the game boots on the PC)
`tools/deck/make_package.sh` (to write, modelled on fear360's `tools/steamdeck/make_package.py`):
1. Build in the sniper container (`podman run --rm -v $repo:/src registry.gitlab.steamos.cloud/steamrt/sniper/sdk
   ...` with the same CMake flags, `-DCMAKE_BUILD_TYPE=Release`), output `build/deck/`.
2. Tarball `JackassPS2-SteamDeck/`: the executable, `libpcsx2gs.so` + its `resources/` shaders, `libSDL3.so`,
   `libshaderc_shared.so.1` copied from the container, `game/` (the disc) or a `--programs` variant without
   it for updates, a `README-SteamDeck.txt` with the add-as-non-Steam-game steps, and a `run.sh` that sets
   `LD_LIBRARY_PATH=$ORIGIN`-equivalent and the runtime's env defaults (`PS2X_GS_WORKER=1`, renderer pcsx2).
3. Private: `private/steamdeck/JackassPS2-SteamDeck.zip` (ignored). Copy over SSH
   (`scp -r ... deck@steamdeck:/home/deck/Games/`) or on the SD card.

## Checklist for the user to run on the Deck now (Desktop Mode, Konsole)
These tell us which packaging route is needed and what is already there. Paste the output back.
```bash
cat /etc/os-release | head -3; uname -r                          # SteamOS version, kernel
ldd --version | head -1                                          # glibc (needs >= 2.31 for a sniper build)
vulkaninfo --summary 2>/dev/null | grep -E 'deviceName|driverName|apiVersion' | head -4   # RADV present?
ls /usr/lib/libshaderc* /usr/lib/libSDL3* 2>/dev/null            # which of these we must bundle (likely all)
echo $XDG_SESSION_TYPE; pgrep -a Xwayland | head -1              # XWayland available in Desktop Mode
df -h /home | tail -1                                            # free space (need ~5 GB: disc + build)
which podman distrobox toolbox 2>/dev/null                       # container tools for an on-Deck build (route b)
systemctl is-active sshd; id -un                                 # SSH on? (sudo systemctl enable --now sshd; passwd first)
steamos-readonly status 2>/dev/null                              # root read-only (expected: enabled; leave it)
python3 --version                                                # for the tools
```
If `libshaderc` is missing, PCSX2's GS cannot compile its Vulkan shaders on the Deck unless we ship the
library: that is the one dependency to watch (Urban Reign loads it with `dlopen`, trying two names).

## Expectations
- Performance: unknown until it runs. Urban Reign holds 60 fps at 8x internal resolution on a GTX 1660 desktop;
  the Deck is far weaker on both CPU (the EE thread, the VU1 worker and PCSX2's GS thread want three fast
  cores) and GPU. 1x–2x internal resolution is the realistic target; the game itself is 60 Hz NTSC
  (`VMODE = NTSC`, 480p option in the ELF).
- The first run compiles Vulkan shaders as the game uses them (hitches); the second run is the one to judge.
- Game Mode vs Desktop Mode: test in Desktop Mode first (a terminal, logs, Vulkan validation if needed), then
  as a non-Steam game in Game Mode for the real look.
