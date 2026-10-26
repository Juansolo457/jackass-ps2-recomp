# Jackass (PS2) static recompilation: a bottom-up plan to a native Linux build

Goal: run the PlayStation 2 **Jackass: The Game** natively on Linux (x86-64, then ARM64), with
the game's own code recompiled and a native renderer, and reach the **title screen** with
everything beneath it verified. Windows comes after Linux; speed, resolution and polish after
the game plays.

Written 2026-10-25 before recon. The build/run detail and the current state live in
[HANDOFF.md](HANDOFF.md); facts about the disc in [FINDINGS.md](FINDINGS.md).

## Why bottom up

The 360 recomps ([graw360-recomp](https://github.com/Juansolo457/graw360-recomp),
[fear360-recomp](https://github.com/Juansolo457/fear360-recomp)) reached a menu in days because
ReXGlue ships a Xenia-derived runtime that already understands the console. PS2Recomp does not
have that: its runtime is memory, syscalls and hardware **stubs**, and every God of War port had
to write the GS, VU and IOP sides itself. Starting from "make the menu show" on a stubbed runtime
means debugging five unverified layers at once. So each layer below is built, tested against
PCSX2 on the same game, and only then built upon. PCSX2 is the oracle throughout: it can dump
the EE register state, the GIF packets and the frame at any point, and our layer must match.

## The two models and what we take from each

| | God of War native ports (Waffle565 and forks, PS2Recomp) | fear360 / graw360 (ours, ReXGlue) |
|---|---|---|
| Translator | PS2Recomp: `ps2xAnalyzer` writes a TOML of functions, `ps2xRecomp` emits one C++ function per MIPS function (very literal, one C++ statement per instruction; MMI and VU0 macro supported; stubs bound by address for stripped games) | ReXGlue codegen from a manifest |
| Runtime | `ps2xRuntime` (memory, syscalls, hardware stubs) + `ps2xIOP` (IOP HLE), with each port's own GS: OpenGL render-target renderer at 2x (Waffle565, KIexster), Vulkan compute rasterizer (igormcsouza, Linux), Vulkan 1.1 (CodeAbhi826, Android) | Xenia-derived runtime and GPU plugin |
| What we copy | The pipeline and the TOML-first workflow; the renderer split (correctness first, then speed); their list of what broke (overlays, VU1 microprograms, IOP modules) | Repo conventions, scripts, audit, handoff discipline, source-only releases |
| Where it hurts | Each port is one game's hand-written hardware; little is reusable without reading it | n/a here |

**Decision:** PS2Recomp (ran-j, pinned commit recorded by `tools/setup.sh`), its runtime used as a
starting point but every hardware layer treated as ours to write and verify. Vulkan is the one
renderer path that covers Linux, Windows and ARM64, so the native renderer is Vulkan; a software
GS rasterizer comes first as the oracle and fallback.

## Layers (each with its exit test)

### Layer 0: dump and recon
Extract the CHD (`chdman extractdvd`), list the ISO, identify `SYSTEM.CNF` → the `SLUS_xxx.xx`
ELF, the IRX modules it loads, movie (`.pss`) and audio formats, and any code overlays (second
ELFs or relocatable code blobs loaded into fixed RAM slots; the boubou666 PS2Recomp fork exists
because God of War needed this). Record the ELF SHA-256, entry point, segments, and the SDK
version string (`sceSif`, libgraph revision) in FINDINGS.md. Run PCSX2 once to confirm the game
boots on the dump and to capture a reference title-screen frame and the EE/IOP console log.
**Exit:** FINDINGS.md filled; the ELF loads in a Ghidra/REA session; function count known.

### Layer 1: memory map and ELF loading (host, no game code yet)
A 32 MB EE RAM, scratchpad, the hardware register window, the ELF segments mapped, host-side
load of the ELF with PCSX2's loader semantics (`.bss` zeroed, args as the PS2 kernel passes
them). **Exit:** a unit test loads the ELF and compares the first 64 KB of each segment with
PCSX2's memory dump at the entry point.

### Layer 2: EE recompilation and kernel syscalls
`ps2xAnalyzer` → `port/jackass.toml` → `ps2xRecomp` → `port/generated/`. Build it with clang on
Linux. Implement the kernel syscalls the game uses (threads, semaphores, `RFU`, `SifRpc`
stubs, `FlushCache`, `GsPutIMR`, VSync handlers) with PCSX2's `ps2_sysmem`/BIOS HLE as the
reference. **Exit:** the game runs from entry to its first `SifLoadModule`/first GIF transfer
with an EE register trace that matches PCSX2's at each syscall (a trace-diff tool in `tools/`).

### Layer 3: DMA, VIF and GIF paths (the data plumbing)
DMAC channels the game uses (VIF0/1, GIF, SIF, IPU), VIF unpack to VU memory, VU1 microprogram
upload, GIF PATH1/2/3 packetisation into a GS register stream. Record the stream, don't draw it.
**Exit:** the first frame's GIF packet stream (register writes in order) matches a PCSX2 GIF dump
of the same frame.

### Layer 4: VU1 (and VU0 macro mode)
How the game's VU1 microprograms get executed: PS2Recomp's VU0 macro support covers inline
VU0; VU1 microprograms must be recompiled per program (static, from the uploaded microcode, as
the GoW ports do) or interpreted. Start with an interpreter (oracle), recompile the hot programs
after measurement. **Exit:** the Layer-3 test still passes with VU1-generated geometry.

### Layer 5: GS, software first
A software rasterizer of the GS register stream (PRIM, XYZ2, UV/ST, TEX0, FRAME, ZBUF, ALPHA,
TEST, CLUT paths the game uses), producing the frame buffer. **Exit:** golden-image match against
PCSX2's software renderer for the boot frames and the title screen, pixel-tolerant.

### Layer 6: IOP side: CD-ROM, SPU2, pad, memory card
HLE of the IRX modules the game loads (cdvd reads from `port/assets/`, `sceSif` RPC, pad, SPU2 to
SDL audio, memory card to a host file), with the IOP modules themselves not executed. **Exit:**
the title screen appears and responds to a controller; intro movie audio plays (IPU/`.pss`
decode is its own sub-step).

### Layer 7: the Vulkan GS
Port the software GS to Vulkan (compute rasterizer like igormcsouza's, or a hybrid of hardware
triangles plus compute for the GS's blend/CLUT oddities), with the software path kept as the
fallback and the oracle. Internal resolution scaling, then 60 fps. **Exit:** same golden images
as Layer 5, measured frame time at 1080p on the user's machine and on the Steam Deck.

### Later phases, in order
1. Gameplay end to end on Linux x86-64 (per-event bugs, save/load, movies).
2. ARM64 Linux (the recompiled C++ is portable; the runtime must avoid x86 intrinsics or guard
   them; test on a Pi 5/Ampere/Deck-class ARM box or QEMU).
3. Windows (same Vulkan renderer, SDL3; MSVC or clang-cl).
4. Speed and quality: measured, incremental ([[incremental-over-rewrite]]), widescreen, high
   frame rate only if the game's timing allows.
5. Source-only release with a build-from-your-own-disc guide, as fear360 and graw360 do.

## Open questions (decide at Layer 0)
- **Linux build host.** The PC has no WSL distribution. Options: WSL2 Ubuntu (needs the user's
  OK to install), the Steam Deck over SSH, or a cross-compile from Windows with a Linux CI run.
- **PS2Recomp's actual state** at the pinned commit (its README says experimental): how much of
  the kernel and DMA layer exists versus is stubbed, and whether its generated code builds with
  clang on Linux and ARM64 out of the box.
- **Overlays.** Whether Jackass loads code at run time; if so the boubou666 overlay fork or an
  equivalent patch is needed before Layer 2 is complete.
- **Game ID.** The USA ID is `SLUS_xxx.xx` until the disc is extracted; don't guess it.
