# Handoff: Jackass (PS2) native Linux port (2026-10-25)

Read [PLAN.md](PLAN.md) for the layers and exit criteria and [FINDINGS.md](FINDINGS.md) for the
disc and executable facts. This file is the state, the build/run detail and where things live.
Update it at the end of every session; the next model starts here, not from chat history.

## Where it stands
**Layer 0 (recon) not started; repository scaffolded 2026-10-25.** Nothing has been built or
run. The user's decisions so far:
- Native **Linux** port first, then ARM64, then Windows.
- Build **bottom up**: each hardware layer verified against PCSX2 before the next (PLAN.md).
- Toolchain: PS2Recomp, following the God of War native ports; repo conventions from
  graw360-recomp and fear360-recomp.
- The CHD stays where it is for now (the user's Downloads folder, read-only, Redump-verified
  USA dump, 2.66 GB). It has **not** been opened: a header-parsing run on it was declined by the
  user on 2026-10-25, so ask before touching the file.

| Piece | State |
|---|---|
| `tools/audit_repo.py` | written (PS2 adaptation of the 360 repos' script); not yet run on a commit |
| `tools/setup.sh` | written: pins PS2Recomp, checks tools, records the commit; **never run** |
| `tools/extract.sh` | written: `chdman extractdvd` → ISO → `tools/iso9660.py` listing/extraction; **never run** |
| `tools/iso9660.py` | written: pure-Python ISO 9660 lister/extractor for the DVD image; untested |
| `tools/chd_info.py` | written: prints a CHD v5 header, codecs and metadata; untested |
| `tools/build.sh`, `launch.sh`, `smoke.sh` | not written (need Layer 0 and a PS2Recomp pin first) |
| `port/jackass.toml` | not written (output of `ps2xAnalyzer`, Layer 2) |
| `native/` | empty |

## Blockers before Layer 0 can run
1. **A Linux environment.** No WSL distribution is installed. Decide between WSL2 Ubuntu
   (install needs the user's OK: it is a system change), the Steam Deck over SSH, or a Linux
   box. The extraction itself (chdman + Python) can run on Windows if the user prefers.
2. **chdman.** Not installed. Source: the official MAME release (mamedev.org or the
   `mame` package on Linux). Downloading needs the user's OK.
3. **PCSX2** for the oracle traces. Not installed on this PC.
4. **PS2Recomp pinned commit.** `tools/setup.sh` clones `ran-j/PS2Recomp` and records the commit
   in `third_party/PS2Recomp.commit`; the first run decides the pin. Its license text goes into
   `LICENSES/` the same day.

## Next steps
1. Get the user's OK for: the Linux host choice, downloading chdman, installing PCSX2.
2. Layer 0: `tools/extract.sh <chd>` (or the chdman step on Windows), fill FINDINGS.md: game
   ID, ELF hash, segments, IRX list, movie/audio formats, overlays yes/no. Open the ELF in REA
   or Ghidra and count functions.
3. Boot the dump in PCSX2 once; save the title-screen frame to `private/reference/`.
4. Pin PS2Recomp, read its runtime to see what exists versus is stubbed; write the Layer 1 and
   Layer 2 findings into PLAN.md's open questions.

## How it is built and run
Not yet. The intended loop, once the scripts exist:
```
tools/extract.sh /path/to/Jackass.chd      # once
tools/build.sh [-j 14]                      # analyze → recompile → cmake build
tools/smoke.sh                              # headless boot, log in port/logs/
tools/launch.sh                             # play
```

## Where things live
- `docs/`: this file, PLAN.md, FINDINGS.md, SETUP.md, REFERENCES.md.
- `tools/`: scripts above; `tools/patches/` for PS2Recomp patches (none yet).
- `port/`: the PS2Recomp project (assets, toml, src, generated).
- `native/`: the GS replacement (software rasterizer, then Vulkan).
- `private/` (ignored): disc images, PCSX2 traces, captures.
- Sister repos: `../graw360-recomp` (scripts and docs to copy from), `../fear360-recomp`.
