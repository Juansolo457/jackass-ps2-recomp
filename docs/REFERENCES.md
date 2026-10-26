# References

What this project is modelled on and where to look things up. Found 2026-10-25 by web search;
the READMEs were not yet read in full, so the one-line descriptions are what their search
summaries say. Read each before copying an idea from it, and note the commit.

## Toolchain
- **PS2Recomp**, ran-j: https://github.com/ran-j/PS2Recomp. Experimental PS2 static recompiler.
  Pipeline: `ps2xAnalyzer` (ELF → TOML config), `ps2xRecomp` (TOML + ELF → C++, one literal C++
  statement per MIPS instruction; MMI and VU0 macro mode; stubs bound by address for stripped
  games), `ps2xRuntime` (memory, syscalls, hardware stubs), `ps2xIOP` (IOP and HLE fallbacks).
  Updated October 2026.
- **PS2Recomp fork with overlays**, boubou666: https://github.com/boubou666/PS2Recomp. Adds
  overlay-module support (code overlays loaded into fixed RAM slots recompiled separately).
  Needed if Jackass uses overlays (PLAN.md, Layer 0).

## God of War (PS2, SCUS-97399) native ports on PS2Recomp
- **Waffle565/God-Of-War-Native-Port**: https://github.com/Waffle565/God-Of-War-Native-Port.
  The base of the family: EE code recompiled to C++, PS2 hardware replaced by native code, an
  OpenGL render-target renderer at 2x internal resolution.
- **KIexster/god-of-war-recomp**: https://github.com/KIexster/god-of-war-recomp. Since October
  2026 based on Waffle565's runtime; GPL-3.0 per recompsoftware.com
  (https://recompsoftware.com/p/god-of-war-recomp/).
- **igormcsouza/god-of-war-recomp**: https://github.com/igormcsouza/god-of-war-recomp. Native
  **Linux** port; the GS rasterized by a **Vulkan compute** backend; milestones listed as 60 fps
  gameplay and 1080p. The closest model for our Layer 7.
- **CodeAbhi826/God-Of-War-Recomp**: https://github.com/CodeAbhi826/God-Of-War-Recomp. Linux/PC
  reference build plus **Android**, Vulkan 1.1 GS backend in progress. Relevant for ARM64.
- **YYOzcan/Tobiichi-Port**: https://github.com/YYOzcan/Tobiichi-Port. Linux and Windows,
  OpenGL 4.3 renderer.

## PS2 decompilations (for how people read PS2 code, not for code)
- Sly Cooper: https://github.com/theonlyzac/sly1
- PaRappa the Rapper 2: https://github.com/raphaelthegreat/parappa2 (progress on decomp.dev)
- bigianb/darev: https://github.com/bigianb/darev

## Hardware references
- PCSX2: https://github.com/PCSX2/pcsx2. GPL-3.0: read for behaviour, don't copy. Its GS dump
  (`.gs` files) and the EE/IOP console log are the traces each layer is tested against.
- Sony's EE User's Manual, EE Core Instruction Set Manual, GS User's Manual, VU User's Manual
  (widely mirrored; cite the section, don't copy the text into the repo).
- ps2tek: https://psi-rockin.github.io/ps2tek/ (community hardware notes).

## Our own
- graw360-recomp: https://github.com/Juansolo457/graw360-recomp (conventions, scripts, audit, handoff)
- fear360-recomp: https://github.com/Juansolo457/fear360-recomp (source-only release recipe)

## Game
- Wikipedia: https://en.wikipedia.org/wiki/Jackass:_The_Game (Sidhe for PS2/PSP, Red Mile
  publisher, NA PS2 release 2007-09-24).
- Developer Q&A, Worthplaying 2007-08-09:
  https://worthplaying.com/article/2007/8/9/interviews/44129-jackass-the-game-all-developer-qa/
