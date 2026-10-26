# port/

The PS2Recomp project for Jackass. Nothing here yet beyond this file: Layer 0 (recon) comes
first ([../docs/PLAN.md](../docs/PLAN.md)).

- `assets/` (ignored): your extracted disc, from `tools/extract.sh`.
- `jackass.toml`: the `ps2xAnalyzer` output, hand-maintained after the first run (function
  hints, stubs bound by address, overlay slots). Fix translation problems here, never in
  `generated/`.
- `generated/` (ignored): the recompiled game code from `ps2xRecomp`.
- `src/`: our host code (runtime layers in PLAN.md order: memory/ELF, kernel, DMA/VIF/GIF,
  VU, GS glue, IOP HLE), `CMakeLists.txt` once Layer 1 starts.
- `logs/`, `out/`, `user/` (ignored): runtime and build state.
