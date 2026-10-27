# Findings: the disc and the executable

Facts about the game's files, measured 2026-10-25 (Layer 0 of [PLAN.md](PLAN.md)) on the dump
below. Everything in this file applies to `SLUS_216.27` with SHA-256
`a6b5dd8013264f40a6af85b1461aa34647bb9a1848b7190d29f9426f90913701`. Strings quoted from the
binary are data about it, not instructions.

## The disc
| | |
|---|---|
| Dump | CHD v5 (chdman), Redump-verified, USA, 2,656,592,888 bytes. **CD-type CHD** (`CHT2`: one `MODE1` track, 2,033,392 frames, codecs cdlz/cdzl/cdfl), so `chdman extractdvd` writes 2448-byte raw frames with the 2048 user bytes first; `tools/iso9660.py toiso` turns that into a plain ISO (4,164,386,816 bytes, 2,033,392 sectors) |
| Volume ID | `JACKASS` |
| `SYSTEM.CNF` | `BOOT2 = cdrom0:\SLUS_216.27;1`, `VER = 1.01`, `VMODE = NTSC` |
| Game ID | **SLUS_216.27** (USA). Europe is SLES_546.33 |
| ELF | `SLUS_216.27`, 6,152,476 bytes, SHA-256 above |
| Files | 504 files in 90 directories, 2.6 GB extracted; full listing in `private/disc_listing.txt` (ignored) |
| `DISK.MAP` | 34 KB text: `count;` then `"\PATH;1",start_lba,end_lba,sectors,size;` per file, CRLF. The game's own file table (string `cdrom0:\DISK.MAP;1` in the ELF), so file reads are by LBA, not by ISO lookup |
| `IRX/` | `IOPRP300.IMG` (IOP replacement image, SDK 3.0.0: `cdvd_driver`, `cdvd_ee_driver`, `ROM_file_driver`), `SIO2MAN.IRX`, `PADMAN.IRX`, `MCMAN.IRX`, `MCSERV.IRX`, `LIBSD.IRX`, `FMODS.IRX` (FMOD's IOP side, 272 KB). Loaded from `cdrom0:\IRX\%s;1`; dev path was `host0:S:\common\ps2\iop\modules\%s` |
| `DATA/PS2/PKCMN.ZIP` | 65 MB common pack: 3,009 entries, deflate (minizip "unzip 1.01" in the ELF). Extensions: `.txd` 1531, `.xds` 625, `.rws` 426, `.xml` 199, `.luc` 100, `.anm` 69, `.uva` 10, `.mcb` 3, plus stray `.bat`, `.old`, `.png.asdf` dev files. Folders: `cameras characters database downloadablestunts effects font graphs hud menu physics resourcesets save scene scripts shared sounds ui` |
| `DATA/PS2/STUNTS/PK??.ZIP` | 37 per-stunt packs, 0.5–11.6 MB each (BB, BM, BW, BY, CJ, CW, DG, EG, EJ, EP, EU, FG, FR, GG, GR, GW, MM, NY, OS, P2, PB, PG, PP, PS, PT, RP, RR, RT, SB, SC, SF, SH, SJ, SW, WH, WT, WW) |
| `DATA/PS2/SOUNDS/` | FMOD `.FSB` sample banks under `CHAR/<char>/`, `MISC/`, `MUSIC/<id>/`, `PROPS/`, `STUNT/<letter>/<id>/` (`STFX*` effects, `*VO` voice, `STIN*` intros) |
| `DATA/PS2/MOVIES/` | 17 files, 2.1 GB, 8.3 names (`JA0BC7~1.NPS` ...). MPEG program streams (`00 00 01 BA`, pack header `44 00 04 00 04 01`), i.e. PS2 `.pss` with libipu IPU video + ADPCM. The ELF names them `movies/ja*.npss` / `.npsw` (standard / widescreen variants of `jaintro`, `jafmv01`–`07`, `jafmvfinal`, `jafoot01`–`12`) |
| Code overlays | **None found**: no second ELF on the disc, no ELF blobs inside any of the 38 ZIP packs, no `.rel`/overlay strings. The ELF has a `.relmain` section of size 0 (SN-style single-module link) |

## The executable
| | |
|---|---|
| Format | ELF32 MIPS (machine 8), little-endian, `e_flags 0x20924000`, entry `0x100008` |
| PCSX2 game CRC | `0204033A` (XOR of the ELF's 32-bit words, as PCSX2 and the Vnnc1 profile compute it) |
| Code hash | the ELF has no `.text`: all code and data are the `main` section, SHA-1 `caa85c7812765c4fe3025a7fa8db0014ef64105c` (0x5BFC80 bytes); whole-file SHA-1 `9ae23afc9cf256d533e3bf3d82a94bbc2fc9b0bd` |
| Segments | one `PT_LOAD`: file `0x80`, vaddr `0x100000`, size `0x5DDF00` (6.15 MB, RWX); a second empty `PT_LOAD` at `0x6DDF00` (the heap start) |
| Sections | `main` (`0x100000`, `0x5BFC80` bytes: all code and data in one section), `.relmain` (0), `heap` (`0x6DDF00`, 0), `.comment`, `.reginfo`, `.shstrtab`. **No `.symtab`: stripped** |
| Compiler | `.comment`: `MW MIPS C Compiler (2.4.1.01)` / `PlayStation2` → **Metrowerks CodeWarrior for PS2**, not GCC/ProDG. Matters for the recomp: MW's calling convention, prologue idioms, and C++ ABI (name mangling, vtables, exceptions) differ from ee-gcc; PS2Recomp's analyzer heuristics were likely tuned on GCC output |
| Code size | ~16,600 `jr $ra` sites, ~73,400 `jal` calls, 9,942 printable strings. **Ghidra 12.1.4 (r5900 extension) finds 13,768 functions** (`recomp/jackass_functions.csv`), total 4.48 MB of function bodies, average 326 bytes |
| Code / data layout of `main` | Code is dense from `0x100000` to about `0x53E000` (200–350 functions per 64 KB), a small island at `0x56Exxx` (9 functions) and the last 57 functions at `0x6A0000`–`0x6AF684` (the SDK's crt0/libc tail, entry `0x100008` sits at the start). **`0x540000`–`0x6A0000` is data**: zero pages at `0x57xxxx`–`0x59xxxx`, VIF/GIF tag tables (`000002ff` words) from `0x606000`, strings around `0x697F50`. PS2Recomp's own scan invents ~930 "functions" there (28k unhandled instructions in the first run); `recomp/jackass.toml` skips them |
| SDK functions located | 863 (`src/jackass/sdk_functions.inc`): 206 with runtime handlers and 601 other SDK entries from the PS2Recomp analyzer's SCE symbol database (built from Metrowerks 2.4.1.01 libraries, the same compiler), plus 56 kernel syscall wrappers at `0x1C0960`–`0x1C11D0` named by the Ghidra export. Libraries seen: libcdvd, libsif/RPC, libpad, libmc, libgraph (sceGs*), libdma, libipu/libmpeg, libdeci2, libfs (sceOpen/Read/Close), libsd remote |
| Engine | Sidhe's own **"Mab" engine** (484 `Mab*` strings: `MabCentral`, `MabStream`, `MabClump`, `MabClumpResource`, `MabWorldResource`, `MabTextureResource`, `MabAnimationBank`, `MabCameraUpdater`, `MabLuaResource`, `MabPS2ControllerManager`, ...). Game code prefix `JA*` (`JALua::ExecuteFile`) |
| Rendering data | RenderWare 3.7 binary stream format (`.rws` worlds, `.txd` texture dictionaries, `.anm`, `.uva`; chunk version stamp `0x1C020065`), but **no RenderWare library strings** in the ELF (no `RwEngine`/`RpWorld`): Mab reads the RW stream format with its own loader (`MabClump` = RW clump). Sony libgraph (`sceGs*`) drives the GS; VU1 use confirmed (`sceGsSyncPath: VU1 does not terminate`, `PS2AllMat...` cluster strings, i.e. VU1 microcode for materials) |
| Scripting | **Lua 5.0.2** (`lua_debug>`, `?;?.lua`), 100 precompiled `.luc` chunks (`\x1bLuaP` v0x50), e.g. `scripts/AutoExec.lua`, `scripts/flow/*.lua` (menus, replay). `scripts/key_sequence/*.txt` are the developers' input-replay test scripts (press start, main_to_episode, ...): a ready-made autopilot once the game boots |
| Physics | **ODE** (Open Dynamics Engine: `ODE Error`, `ODE INTERNAL ERROR`), plus `MCB` Mab collision files |
| Audio | **FMOD Ex-era FSOUND** (`FSOUND_Command_*`, `FMOD.IRX`/`FMOD.A` version check string, EE↔IOP SIF command packets), `.FSB` banks |
| Video | Sony `libipu` (`PsIIlibipu 3000`) + `sceMpeg*` for the `.pss` movies |
| Other Sony libs | libpad (`scePad*`), libmc (`sceMc*`), libcdvd (`sceCd*`), libsif RPC |
| Data format | `XDS!0303` serialized Mab objects (`.xds`, "DSD" versioned headers), XML for resource sets and the string database (`database/strings.xml`), `stunt_sign_public.key` (RSA public key for signed downloadable stunts) |
| Display | NTSC and PAL `VMODE`, `480P` option, `SetWidescreen`/`widescreen_on` menu toggle (the `.npsw` movies are the widescreen cuts). No multitap, no network (no DNAS/eenet) |
| Debug leftovers | `No space for debug heap!`, `lua_debug>`, physics statistics, `DebugBreak`, `host0:` dev paths |

## What this means for the plan
- **Single ELF, no overlays**: the plain `ran-j/PS2Recomp` pipeline applies; the boubou666
  overlay fork is not needed.
- **Metrowerks code**: expect the analyzer to miss or mis-split functions; the function list in
  `port/jackass.toml` will need checking against a disassembly (REA/Ghidra) early in Layer 2.
- **IOP side is small and known**: pad, memory card, cdvd, libsd and FMOD. FMOD's IOP module is
  the one non-Sony module; its EE↔IOP SIF command protocol must be HLE'd (Layer 6) and `.FSB`
  (PS2 ADPCM) decoded on the host.
- **Movies**: standard PS2 `.pss` (MPEG-2 IPU video + ADPCM). An IPU decoder or a host MPEG-2
  decoder with the IPU's output format is Layer 6 work; 2.1 GB of the disc is movies.
- **File I/O by LBA** (`DISK.MAP`): the host file layer can serve reads from the ISO or from
  `port/assets/` plus the map; keep the ISO path as the first implementation.
- **Lua 5.0.2 and the key-sequence scripts** give a built-in way to drive menus for smoke tests.
