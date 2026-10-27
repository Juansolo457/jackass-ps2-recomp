#!/bin/bash
# Package the release build for YOUR OWN Steam Deck: private/steamdeck/JackassPS2-SteamDeck.zip. It contains your
# disc image, so it is private: never upload or share it (README.md, "Legal"; the zip is under private/, ignored).
#   JA_RELEASE_OUT=~/jackass-out/release tools/deck/make_package.sh
# Layout of the zip:
#   JackassPS2-SteamDeck/run.sh                 the launcher (add it to Steam as a non-Steam game, no Proton)
#   JackassPS2-SteamDeck/README-SteamDeck.txt
#   JackassPS2-SteamDeck/bin/                   jackass + libpcsx2gs.so + libSDL3.so.0 + libshaderc_shared.so.1 +
#                                               libpng16.so.16 + resources/ (PCSX2's GS shaders and fonts)
#   JackassPS2-SteamDeck/game/jackass.iso       your disc image
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
out=${JA_RELEASE_OUT:-$HOME/jackass-out/release}
bin=$out/build/bin
iso=${JA_ISO:-$root/private/jackass.iso}
for f in "$bin/jackass" "$bin/libpcsx2gs.so" "$out/deps/shaderc/lib/libshaderc_shared.so.1" "$iso"; do
  [ -e "$f" ] || { echo "package: missing $f (tools/deck/release.sh --build, tools/extract.sh)" >&2; exit 1; }
done
stage=$out/package/JackassPS2-SteamDeck
rm -rf "$out/package"
mkdir -p "$stage/bin" "$stage/game"
cp -L "$bin/jackass" "$bin/libpcsx2gs.so" "$stage/bin/"
cp -L "$bin"/libSDL3.so.0 "$stage/bin/"
cp -L "$out/deps/shaderc/lib/libshaderc_shared.so.1" "$out/deps/libpng/libpng16.so.16" "$stage/bin/"
cp -r "$bin/resources" "$stage/bin/"
[ -d "$bin/shadercache_pcsx2" ] && cp -r "$bin/shadercache_pcsx2" "$stage/bin/"
strip --strip-debug "$stage/bin/jackass" "$stage/bin/libpcsx2gs.so" 2>/dev/null || true
ln "$iso" "$stage/game/jackass.iso" 2>/dev/null || cp "$iso" "$stage/game/jackass.iso"

cat > "$stage/run.sh" <<'RUN'
#!/bin/bash
# Jackass PS2 Recompiled: Steam Deck / Linux launcher. Native Linux: no Proton.
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$here/user" "$here/logs"
export JA_USER_DIR="$here/user"                      # memory card, shader cache, settings
export LD_LIBRARY_PATH="$here/bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
log="$here/logs/jackass-$(date +%Y%m%d-%H%M%S).log"
cd "$here/bin"
./jackass --iso "$here/game/jackass.iso" "$@" > "$log" 2>&1
code=$?
echo "exit code $code" >> "$log"
exit $code
RUN
chmod +x "$stage/run.sh" "$stage/bin/jackass"

cat > "$stage/README-SteamDeck.txt" <<'TXT'
Jackass PS2 Recompiled - Steam Deck test build (native Linux, NO Proton)
=====================================================================

This is an early boot test: it shows the logo, the loading screen and the opening video, then goes as far as the
port currently goes. It contains your own disc image: keep it on your own Deck, never share it.

Setup (Desktop Mode)
  1. Extract the zip, e.g. to /home/deck/Games/  (Dolphin: right-click > Extract > Extract archive here).
     You get /home/deck/Games/JackassPS2-SteamDeck/
  2. Optional first check in Konsole:   cd ~/Games/JackassPS2-SteamDeck && ./run.sh
     (a window opens; close it or press Ctrl+C in Konsole). The log is in logs/.
  3. Steam > Games > "Add a Non-Steam Game to My Library" > Browse > select run.sh > Add.
     (Show "All files" in the file picker if run.sh is not listed.)
  4. In the library, right-click the new entry > Properties:
       - Compatibility: leave "Force the use of a specific Steam Play compatibility tool" OFF (no Proton).
         If it does not start, try ticking it and choosing "Steam Linux Runtime 3.0 (sniper)".
       - Shortcut > START IN: the folder of run.sh, e.g. "/home/deck/Games/JackassPS2-SteamDeck/"
  5. Rename it (e.g. "Jackass PS2") and start it from Game Mode.

Performance overlay: Quick Access (...) > Performance > Performance Overlay Level 3 or 4.
The first run compiles Vulkan shaders as they appear (short hitches); the second run is the one to judge.

Logs: logs/jackass-<date>.log, one per run. Copy the newest back to the PC for a read.
Controls: the Deck's controls act as a PS2 pad (Steam Input, Xbox layout).
TXT

zip_dir=$root/private/steamdeck
mkdir -p "$zip_dir"
rm -f "$zip_dir/JackassPS2-SteamDeck.zip"
# -0 for the disc image (does not compress), deflate for the rest; zip64 is automatic above 4 GB.
(cd "$out/package" && zip -q -r -9 "$zip_dir/JackassPS2-SteamDeck.zip" JackassPS2-SteamDeck -x 'JackassPS2-SteamDeck/game/*' \
   && zip -q -0 "$zip_dir/JackassPS2-SteamDeck.zip" JackassPS2-SteamDeck/game/jackass.iso)
ls -la "$zip_dir/JackassPS2-SteamDeck.zip"
echo "package: done (private: your disc image is inside)"
