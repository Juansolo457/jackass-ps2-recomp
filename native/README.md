# native/

The Graphics Synthesizer replacement, in two steps ([../docs/PLAN.md](../docs/PLAN.md)):

1. `gs_soft/` (Layer 5): a software rasterizer of the GS register stream the game produces,
   checked against PCSX2's software renderer frame by frame. Stays as the oracle and the
   fallback for ever.
2. `gs_vulkan/` (Layer 7): the Vulkan renderer (compute rasterizer or hybrid), the one path that
   covers Linux, Windows and ARM64. Replaced pass by pass with golden-image checks against
   `gs_soft/`, never as a big-bang rewrite.

Empty until Layer 5.
