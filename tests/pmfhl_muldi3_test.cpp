// Regression test for engine/patches/04 (PMFHL/PMTHL with pipeline 1): replays, statement by statement, the C++ that
// ps2_recomp emits for the Metrowerks __muldi3 in Jackass (0x1B0E38: mult, multu1, madd, pmfhl.lw, pcpyud) and checks
// the 64-bit products. With the old PS2_PMFHL_LW(hi, lo) every product came out wrong (strtol("505") == 5).
// Build and run (no game data needed):
//   clang++ -std=c++20 -msse4.1 -I engine/runtime/runtime/ps2xRuntime/include tests/pmfhl_muldi3_test.cpp -o /tmp/t && /tmp/t
// GPL-3.0-or-later, like the runtime it tests (NOTICE).
#include <cstdint>
#include <cstdio>
#include <immintrin.h>

#include "ps2_runtime_macros.h"

namespace
{
    struct Regs
    {
        uint64_t gpr[32] = {};
        __m128i vec_at = _mm_setzero_si128();
        uint64_t hi = 0, lo = 0, hi1 = 0, lo1 = 0;
    };

    int64_t s64(uint64_t v) { return static_cast<int64_t>(v); }
    int32_t s32(uint64_t v) { return static_cast<int32_t>(v); }
    uint32_t u32(uint64_t v) { return static_cast<uint32_t>(v); }

    // __muldi3(a0, a1): the generated code for 0x1B0E38-0x1B0E80, register for register.
    uint64_t muldi3(uint64_t a, uint64_t b)
    {
        Regs r;
        uint64_t &v0 = r.gpr[2], &a0 = r.gpr[4], &a1 = r.gpr[5], &t7 = r.gpr[15];
        a0 = a;
        a1 = b;
        v0 = a0 << 32;                                  // dsll32 v0, a0, 0
        t7 = static_cast<uint64_t>(s64(a1) >> 32);      // dsra32 t7, a1, 0
        v0 = static_cast<uint64_t>(s64(v0) >> 32);      // dsra32 v0, v0, 0
        a1 = a1 << 32;                                  // dsll32 a1, a1, 0
        {                                               // mult zero, v0, t7
            const int64_t result = static_cast<int64_t>(s32(v0)) * static_cast<int64_t>(s32(t7));
            r.lo = static_cast<uint64_t>(static_cast<int64_t>(static_cast<int32_t>(result)));
            r.hi = static_cast<uint64_t>(static_cast<int64_t>(static_cast<int32_t>(result >> 32)));
        }
        a1 = static_cast<uint64_t>(s64(a1) >> 32);      // dsra32 a1, a1, 0
        {                                               // multu1 zero, v0, a1
            const uint64_t result = static_cast<uint64_t>(u32(v0)) * static_cast<uint64_t>(u32(a1));
            r.lo1 = static_cast<uint64_t>(static_cast<int64_t>(static_cast<int32_t>(result)));
            r.hi1 = static_cast<uint64_t>(static_cast<int64_t>(static_cast<int32_t>(result >> 32)));
        }
        a0 = static_cast<uint64_t>(s64(a0) >> 32);      // dsra32 a0, a0, 0
        {                                               // madd a0, a0, a1
            const uint64_t acc = (static_cast<uint64_t>(u32(r.hi)) << 32) | u32(r.lo);
            const int64_t prod = static_cast<int64_t>(s32(a0)) * static_cast<int64_t>(s32(a1));
            const int64_t result = static_cast<int64_t>(acc) + prod;
            r.lo = static_cast<uint64_t>(static_cast<int64_t>(static_cast<int32_t>(result)));
            r.hi = static_cast<uint64_t>(static_cast<int64_t>(static_cast<int32_t>(result >> 32)));
            a0 = r.lo;
        }
        r.vec_at = PS2_PMFHL_LW(r.hi, r.lo, r.hi1, r.lo1);                    // pmfhl.lw at
        r.vec_at = _mm_unpackhi_epi64(r.vec_at, _mm_setzero_si128());         // pcpyud at, at, zero
        v0 = static_cast<uint64_t>(_mm_cvtsi128_si64(r.vec_at));              // daddu v0, at, zero
        t7 = static_cast<uint64_t>(s64(v0) >> 32);                            // dsra32 t7, v0, 0
        v0 = v0 << 32;                                                        // dsll32 v0, v0, 0
        t7 = static_cast<uint64_t>(static_cast<int64_t>(static_cast<int32_t>(u32(t7) + u32(a0)))); // addu t7, t7, a0
        v0 = v0 >> 32;                                                        // dsrl32 v0, v0, 0
        t7 = t7 << 32;                                                        // dsll32 t7, t7, 0
        return v0 | t7;                                                       // or v0, v0, t7 (delay slot)
    }
}

int main()
{
    struct Case { uint64_t a, b; };
    const Case cases[] = {{5, 10}, {50, 10}, {1074, 1}, {107, 10}, {0, 10}, {65459321, 10}, {0x7FFFFFFFull, 3},
                          {0x123456789ull, 0x1000ull}, {static_cast<uint64_t>(-5), 7}, {static_cast<uint64_t>(-3), static_cast<uint64_t>(-9)}};
    int failures = 0;
    for (const Case &c : cases)
    {
        const uint64_t got = muldi3(c.a, c.b);
        const uint64_t want = c.a * c.b;
        if (got != want)
        {
            std::printf("FAIL __muldi3(%lld, %lld) = %lld, want %lld\n", static_cast<long long>(c.a), static_cast<long long>(c.b),
                        static_cast<long long>(got), static_cast<long long>(want));
            ++failures;
        }
    }
    // PMFHL word order and PMTHL round trip.
    uint64_t hi = 0x2222222211111111ull, lo = 0x4444444433333333ull, hi1 = 0x6666666655555555ull, lo1 = 0x8888888877777777ull;
    alignas(16) uint32_t w[4];
    _mm_store_si128(reinterpret_cast<__m128i *>(w), PS2_PMFHL_LW(hi, lo, hi1, lo1));
    if (w[0] != 0x33333333u || w[1] != 0x11111111u || w[2] != 0x77777777u || w[3] != 0x55555555u)
    {
        std::printf("FAIL pmfhl.lw order %08x %08x %08x %08x\n", w[0], w[1], w[2], w[3]);
        ++failures;
    }
    _mm_store_si128(reinterpret_cast<__m128i *>(w), PS2_PMFHL_UW(hi, lo, hi1, lo1));
    if (w[0] != 0x44444444u || w[1] != 0x22222222u || w[2] != 0x88888888u || w[3] != 0x66666666u)
    {
        std::printf("FAIL pmfhl.uw order %08x %08x %08x %08x\n", w[0], w[1], w[2], w[3]);
        ++failures;
    }
    uint64_t h = 0xAAAAAAAA00000000ull, l = 0xBBBBBBBB00000000ull, h1 = 0, l1 = 0;
    ps2_pmthl_lw(h, l, h1, l1, _mm_set_epi32(4, 3, 2, 1));
    if (l != 0xBBBBBBBB00000001ull || h != 0xAAAAAAAA00000002ull || l1 != 3 || h1 != 4)
    {
        std::printf("FAIL pmthl.lw\n");
        ++failures;
    }
    std::printf("%s (%d failure%s)\n", failures ? "FAILED" : "ok", failures, failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}
