// Regression test for engine/patches/08 (PATH3 at GIF packet granularity). Jackass's RenderWare texture cache sends a
// frame's texture uploads as one GIF-channel chain while VIF1 masks PATH3, then opens PATH3 for one texture at a time
// (FLUSHA; MSKPATH3 0; MSKPATH3 1) right before the draws that use it. The runtime queued the chain as one blob and
// released all of it at the first unmask, so later uploads overwrote GS memory that pending draws still sampled
// (garbage menus and terrain). Checks: one EOP packet per unmask window, the rest once PATH3 stays unmasked, and
// order kept with PATH2 packets. No game data needed.
// Build and run: cmake --build build --target ja_path3_packets_test && build/bin/ja_path3_packets_test
// GPL-3.0-or-later, like the runtime it tests (NOTICE).
#include "ps2_runtime.h"
#include "runtime/ps2_memory.h"
#include "runtime/gs/ps2_gif_arbiter.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

// The runtime library links against the game's recompiled function table; this test has no game code.
extern const uint32_t g_ps2RecompiledFunctionTableBase = 0u;
extern const uint32_t g_ps2RecompiledFunctionTableEnd = 0u;
extern const uint32_t g_ps2RecompiledFunctionTableSlotCount = 0u;
PS2Runtime::RecompiledFunction g_ps2RecompiledFunctionTable[1] = {};

namespace
{
    int g_failures = 0;

    void expect(bool condition, const char *what)
    {
        if (!condition)
        {
            ++g_failures;
            std::fprintf(stderr, "FAIL: %s\n", what);
        }
    }

    // A PACKED A+D GIF packet of `count` NOP writes (register 0x7F); `marker` goes in the first write's data so the
    // receiver can tell packets apart. EOP on the tag when `eop`.
    std::vector<uint8_t> nopPacket(uint32_t count, bool eop, uint32_t marker)
    {
        std::vector<uint8_t> out(16u + 16u * count, 0u);
        const uint64_t tagLo = static_cast<uint64_t>(count) | (eop ? (1ull << 15) : 0ull) | (1ull << 60); // NREG=1
        const uint64_t tagHi = 0xEull;                                                                  // A+D
        std::memcpy(out.data(), &tagLo, 8u);
        std::memcpy(out.data() + 8u, &tagHi, 8u);
        for (uint32_t i = 0; i < count; ++i)
        {
            const uint64_t data = i == 0u ? marker : 0u;
            const uint64_t address = 0x7Full;
            std::memcpy(out.data() + 16u + 16u * i, &data, 8u);
            std::memcpy(out.data() + 24u + 16u * i, &address, 8u);
        }
        return out;
    }

    void vif1(PS2Memory &memory, std::initializer_list<uint32_t> commands)
    {
        std::vector<uint32_t> words(commands);
        memory.processVIF1Data(reinterpret_cast<const uint8_t *>(words.data()), static_cast<uint32_t>(words.size() * 4u));
    }

    constexpr uint32_t kMask = (0x06u << 24) | 0x8000u;   // MSKPATH3 1
    constexpr uint32_t kUnmask = (0x06u << 24);           // MSKPATH3 0
    constexpr uint32_t kFlushA = (0x13u << 24);           // FLUSHA
}

int main()
{
    PS2Memory memory;
    if (!memory.initialize())
    {
        std::fprintf(stderr, "PS2Memory::initialize failed\n");
        return 2;
    }
    std::vector<uint32_t> received; // first marker of each packet the GS gets, 0 for packets without one
    GifArbiter arbiter([&](const uint8_t *data, uint32_t size)
    {
        uint32_t offset = 0u;
        while (offset + 16u <= size)
        {
            uint64_t lo = 0u;
            std::memcpy(&lo, data + offset, 8u);
            const uint32_t nloop = static_cast<uint32_t>(lo & 0x7FFFu);
            uint64_t marker = 0u;
            if (nloop != 0u)
                std::memcpy(&marker, data + offset + 16u, 8u);
            if (marker != 0u)
                received.push_back(static_cast<uint32_t>(marker));
            offset += 16u + 16u * nloop;
        }
    });
    memory.setGifArbiter(&arbiter);

    // PATH3 masked; the texture chain arrives as one transfer holding three EOP-terminated packets, the first two
    // made of two tags each (the second tag of each carries EOP), as the game builds them.
    vif1(memory, {kMask});
    std::vector<uint8_t> chain;
    for (uint32_t texture = 1u; texture <= 3u; ++texture)
    {
        const auto head = nopPacket(2u, false, texture * 10u);
        const auto tail = nopPacket(1u, true, texture * 10u + 1u);
        chain.insert(chain.end(), head.begin(), head.end());
        chain.insert(chain.end(), tail.begin(), tail.end());
    }
    memory.submitGifPacket(GifPathId::Path3, chain.data(), static_cast<uint32_t>(chain.size()));
    expect(received.empty(), "masked PATH3 data reached the GS");

    // One window: FLUSHA; MSKPATH3 0; MSKPATH3 1 -> exactly texture 1 (both of its tags).
    vif1(memory, {kFlushA, kUnmask, kMask});
    expect(received == std::vector<uint32_t>({10u, 11u}), "first unmask window did not release exactly packet 1");

    // A PATH2 packet after the window must come after texture 1 and before texture 2.
    const auto direct = nopPacket(1u, true, 99u);
    memory.submitGifPacket(GifPathId::Path2, direct.data(), static_cast<uint32_t>(direct.size()));
    expect(received == std::vector<uint32_t>({10u, 11u, 99u}), "PATH2 packet out of order with PATH3");

    // Second window -> texture 2 only.
    vif1(memory, {kFlushA, kUnmask, kMask});
    expect(received == std::vector<uint32_t>({10u, 11u, 99u, 20u, 21u}), "second unmask window did not release packet 2");

    // Unmask and carry on with other VIF1 commands: the rest flows.
    vif1(memory, {kUnmask, kFlushA});
    expect(received == std::vector<uint32_t>({10u, 11u, 99u, 20u, 21u, 30u, 31u}), "PATH3 left unmasked did not drain");

    if (g_failures == 0)
        std::printf("path3_packets_test: all checks passed\n");
    else
        std::printf("path3_packets_test: %d check(s) failed\n", g_failures);
    std::fflush(stdout);
    std::fflush(stderr);
    // _Exit: the runtime's static teardown must not replace the result.
    std::_Exit(g_failures == 0 ? 0 : 1);
}
