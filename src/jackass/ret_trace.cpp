// JA_RET_TRACE=0xADDR,0xADDR,...: log every call to these guest functions with $a0-$a3 on entry and $v0 on return.
// JA_RET_TRACE_MAX=<n>: how many calls of each to log (default 50).
// A debugging aid for "which init step failed": the wrapper calls the original recompiled function and logs what
// it returned. If the function yields (a thread switch inside it), the line says so instead of a return value.
// GPL-3.0-or-later, like the rest of src/ (NOTICE).
#include "jackass/ret_trace.h"
#include "jackass/function_hooks.h"
#include "jackass/log.h"

#include "ps2_runtime_macros.h"

#include <cstdlib>
#include <cstring>
#include <mutex>
#include <string>
#include <unordered_map>

namespace jackass::rettrace
{
    namespace
    {
        std::mutex g_mutex;
        std::unordered_map<uint32_t, GuestFunction> g_originals;
        std::unordered_map<uint32_t, uint32_t> g_counts;

        uint32_t maxCalls()
        {
            static const uint32_t value = []
            {
                const char *text = std::getenv("JA_RET_TRACE_MAX");
                return text && *text ? static_cast<uint32_t>(std::strtoul(text, nullptr, 0)) : 50u;
            }();
            return value;
        }

        void trampoline(uint8_t *rdram, R5900Context *ctx, PS2Runtime *runtime)
        {
            const uint32_t address = ctx->pc;
            const uint32_t ra = getRegU32(ctx, 31);
            const uint32_t a0 = getRegU32(ctx, 4), a1 = getRegU32(ctx, 5), a2 = getRegU32(ctx, 6), a3 = getRegU32(ctx, 7);
            GuestFunction original = nullptr;
            uint32_t count = 0;
            {
                std::lock_guard<std::mutex> lock(g_mutex);
                original = g_originals[address];
                count = ++g_counts[address];
            }
            if (count <= maxCalls())
                JA_INFO(Game, "ret-trace enter 0x" << std::hex << address << " a0=0x" << a0 << " a1=0x" << a1 << " a2=0x" << a2
                                                   << " a3=0x" << a3 << " ra=0x" << ra << std::dec << " (call " << count << ")");
            original(rdram, ctx, runtime);
            if (count > maxCalls())
                return;
            if (ctx->pc == ra)
                JA_INFO(Game, "ret-trace leave 0x" << std::hex << address << " v0=0x" << getRegU32(ctx, 2) << " (call " << std::dec
                                                   << count << ")");
            else
                JA_INFO(Game, "ret-trace 0x" << std::hex << address << " left with pc=0x" << ctx->pc << " (not its return address 0x"
                                             << ra << "; a yield or a non-local exit)");
        }
    }

    namespace
    {
        // JA_ZIP_CHECK=1: before minizip's unzCloseCurrentFile (0x43DAA0) runs, apply its own CRC test (all bytes read,
        // crc32 != crc32_wait) and log a mismatch, which the game ignores. Tells a wrong inflate apart from wrong input.
        GuestFunction g_unzClose = nullptr;
        uint32_t g_zipCloses = 0u, g_zipCrcErrors = 0u;

        uint32_t guest32(const uint8_t *rdram, uint32_t address)
        {
            uint32_t value = 0u;
            std::memcpy(&value, rdram + (address & 0x01FFFFFCu), 4u);
            return value;
        }

        void unzCloseCheck(uint8_t *rdram, R5900Context *ctx, PS2Runtime *runtime)
        {
            const uint32_t file = getRegU32(ctx, 4);
            const uint32_t info = file ? guest32(rdram, file + 132u) : 0u;
            if (info)
            {
                const uint32_t crc = guest32(rdram, info + 80u), wanted = guest32(rdram, info + 84u);
                const uint32_t restUncompressed = guest32(rdram, info + 92u), raw = guest32(rdram, info + 112u);
                const uint32_t method = guest32(rdram, info + 104u);
                std::lock_guard<std::mutex> lock(g_mutex);
                ++g_zipCloses;
                if (restUncompressed == 0u && raw == 0u && wanted != 0u && crc != wanted)
                {
                    ++g_zipCrcErrors;
                    JA_INFO(Game, "zip-check CRC MISMATCH #" << g_zipCrcErrors << " of " << g_zipCloses << " closes: crc=0x" << std::hex
                                                          << crc << " expected=0x" << wanted << " method=" << std::dec << method
                                                          << " ra=0x" << std::hex << getRegU32(ctx, 31));
                }
                else if (restUncompressed != 0u)
                    JA_INFO(Game, "zip-check closed early: " << restUncompressed << " bytes unread");
                if ((g_zipCloses % 200u) == 0u)
                    JA_INFO(Game, "zip-check " << g_zipCloses << " closes, " << g_zipCrcErrors << " CRC mismatches");
            }
            g_unzClose(rdram, ctx, runtime);
        }
    }

    void installFromEnvironment(PS2Runtime &runtime)
    {
        (void)runtime;
        if (const char *zip = std::getenv("JA_ZIP_CHECK"); zip && *zip == '1')
        {
            if (FunctionHooks::instance().replace(0x43DAA0u, "zip_check", &unzCloseCheck, ReplacementStatus::Observed, "JA_ZIP_CHECK"))
            {
                g_unzClose = FunctionHooks::instance().original(0x43DAA0u);
                JA_INFO(Hook, "JA_ZIP_CHECK: checking CRCs at unzCloseCurrentFile 0x43daa0");
            }
        }
        const char *value = std::getenv("JA_RET_TRACE");
        if (!value || !*value)
            return;
        std::string list(value);
        size_t pos = 0;
        while (pos < list.size())
        {
            const size_t comma = list.find(',', pos);
            const std::string token = list.substr(pos, comma == std::string::npos ? std::string::npos : comma - pos);
            pos = comma == std::string::npos ? list.size() : comma + 1;
            if (token.empty())
                continue;
            const uint32_t address = static_cast<uint32_t>(std::strtoul(token.c_str(), nullptr, 0));
            if (!FunctionHooks::instance().replace(address, "ret_trace", &trampoline, ReplacementStatus::Observed, "JA_RET_TRACE"))
            {
                JA_ERROR(Hook, "JA_RET_TRACE: cannot wrap 0x" << std::hex << address);
                continue;
            }
            GuestFunction original = FunctionHooks::instance().original(address);
            if (!original)
            {
                JA_ERROR(Hook, "JA_RET_TRACE: 0x" << std::hex << address << " has no recompiled function");
                continue;
            }
            std::lock_guard<std::mutex> lock(g_mutex);
            g_originals[address] = original;
            JA_INFO(Hook, "JA_RET_TRACE: wrapping 0x" << std::hex << address);
        }
    }
}
