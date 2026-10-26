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

**Decision (2026-10-25):** PS2Recomp (ran-j, pinned commit recorded by `tools/setup.sh`), its
runtime used as a starting point but every hardware layer treated as ours to write and verify.
Vulkan is the one renderer path that covers Linux, Windows and ARM64, so the native renderer is
Vulkan; a software GS rasterizer comes first as the oracle and fallback.

**Revision after reading the God of War repos (2026-10-26, REFERENCES.md):** the user pointed at
KIexster/god-of-war-recomp as the example. What it shows changes the "write every layer ourselves"
part, not the bottom-up verification:

- The working runtime is **Waffle565's `runtime` branch** (a GPL-3.0 fork of PS2Recomp at
  `c5a9d02`, carried by KIexster as `patches/ps2recomp-waffle-runtime.patch`). It already has what
  Layers 1–7 below describe: native kernel, DMA/VIF/GIF handed straight to VU1 and GS, VU1
  microcode and IRX modules compiled ahead of time to C++, an OpenGL 4.3 render-target GS with
  2x internal resolution, native pad/memory card/sound, libmpeg2 movies, files served at their
  original disc sectors. KIexster builds its test suite on Linux (GCC) and has an EGL patch for
  the GS, so Linux is a patch away, not a port away.
- So the layers stay, but each one becomes **"take Waffle565's component, run Jackass through it,
  verify against PCSX2, patch what Jackass needs"** instead of "write it". This matches the user's
  preference for measured, incremental work over rewrites ([[incremental-over-rewrite]]). The
  Vulkan renderer moves to a later phase, only if OpenGL 4.3 fails on a target (ARM64 Linux has
  GL 4.3 through Mesa on most SoCs; Android would not).
- **Everything built on that runtime is GPL-3.0.** Our own tools and docs can stay MIT, but the
  runtime patches, overrides and the built program are GPL (NOTICE). KIexster chose GPL-3.0 for
  the whole repo for simplicity; our NOTICE keeps the split as graw360-recomp does.
- Their PCSX2 method is exactly our oracle: replay a frame's VIF1 chain from a savestate through
  the runtime's VIF1/VU1/GS to split GS bugs from EE bugs (REFERENCES.md, "PCSX2 as oracle").
- Their hard-won rules: never stub Sony's software-double libm (`sin` returning its argument broke
  every animation), verify each stub's calling convention, keep the first PSS block for
  `sceMpegCreate`, one patch per topic with a regression test, overrides call the original for
  anything not replaced.
- **Risk for Jackass:** Waffle565's runtime is shaped by God of War (Santa Monica's engine, 989snd
  audio, GCC-built). Jackass is Metrowerks-built with FMOD on the IOP, ODE, Lua and RenderWare
  data. The IRX ahead-of-time compiler should cover `FMODS.IRX` the same way it covers GoW's 8
  modules, which removes the FMOD HLE concern from Layer 6; the Metrowerks function boundaries and
  the Sony-library stub addresses are the first things to establish (Layer 2).

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

## Open questions
Settled at Layer 0 (2026-10-25, see FINDINGS.md):
- **Linux build host:** WSL2 Ubuntu 26.04 on this PC (the user's choice).
- **Overlays:** none. Plain PS2Recomp; the boubou666 fork is not needed.
- **Game ID:** `SLUS_216.27`.

Still open:
- **Which base to pin.** Options: (a) `ran-j/PS2Recomp` at KIexster's `c5a9d02` plus KIexster's
  patch stack (Waffle565's runtime as a patch, then GCC/EGL/VU fixes: proven to build on Linux);
  (b) Waffle565's `runtime` branch checked out directly (the upstream of that patch, moving);
  (c) ran-j's current HEAD (updated October 2026, may have absorbed some of this). Recommended:
  (a), because its CI proves the Linux build and its patch order is documented
  (`tools/ci/parches.py`). `tools/setup.sh` defaults to the `c5a9d02` pin; the patch stack is
  fetched by `tools/setup.sh` from KIexster's repo at a recorded commit (GPL-3.0, NOTICE).
- **Whether the generated code builds with clang** (KIexster uses MSVC on Windows and GCC on
  Linux). Check at the first `tools/build.sh`.
- **Metrowerks output.** The game was built with CodeWarrior MIPS 2.4.1, not GCC. How well does
  `ps2xAnalyzer` find function boundaries and switch tables in it? Check against a REA/Ghidra
  disassembly at Layer 2 before trusting the TOML.
- **FMOD on the IOP.** FMOD's EE↔IOP SIF command protocol (`FSOUND_Command_*`) has to be HLE'd
  and `.FSB` ADPCM decoded on the host: is there enough in the FMOD 3.x PS2 headers (public at
  the time) to do that without running the IRX?
- **Movies.** 2.1 GB of `.pss`: host MPEG-2 decode (FFmpeg) matching the IPU's output, or an
  IPU implementation. Decide at Layer 6; not needed for the title screen if the intro can be
  skipped.
