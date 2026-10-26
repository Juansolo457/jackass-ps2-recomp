# Findings: the disc and the executable

Facts about the game's files, each tied to the hash of the file it was measured on. Fill in at
Layer 0 ([PLAN.md](PLAN.md)). Nothing here yet has been measured; the "known from outside"
section is what public sources say and must be confirmed from the disc.

## The disc
| | |
|---|---|
| Dump | CHD (MAME chdman), Redump-verified, USA, 2,656,592,888 bytes |
| Game ID | `SLUS_xxx.xx` (to confirm from `SYSTEM.CNF`) |
| ELF SHA-256 | (to fill) |
| Media | DVD (size implies DVD-5) |
| Root listing | (to fill: `tools/iso9660.py list`) |
| IRX modules | (to fill) |
| Movies / audio | (to fill: `.pss` + IPU? ADPCM `.vag`? a packed archive?) |
| Code overlays | (to fill: yes/no, how loaded) |

## The executable
| | |
|---|---|
| Entry point | (to fill) |
| Segments | (to fill) |
| SDK / libraries | (to fill: `sce` version strings, libgraph, libdma, libvu0, libpad, libsd) |
| Function count (analyzer) | (to fill) |
| VU1 microprograms | (to fill: how many, how uploaded) |
| Middleware strings | (to fill: Havok? Bink/`.pss`? FMOD? a Sidhe engine name?) |

## Known from outside (unconfirmed)
- Developer Sidhe Interactive (New Zealand), publisher Red Mile Entertainment; North American
  PS2 release 2007-09-24. PSP and DS versions exist; the DS one is by Sensory Sweep. One review
  site lists an Xbox 360 version; other sources do not, so treat that as wrong.
- The European PS2 release is `SLES_546.33`. The USA ID was not found and must come from the disc.
