// JA_RET_TRACE=0xADDR,0xADDR,...: log every call to these guest functions with $a0-$a3 on entry and $v0 on return.
// A debugging aid for "which init step failed": the wrapper calls the original recompiled function and logs what
// it returned. If the function yields (a thread switch inside it), the line says so instead of a return value.
// GPL-3.0-or-later, like the rest of src/ (NOTICE).
#include "jackass/ret_trace.h"
#include "jackass/function_hooks.h"
#include "jackass/log.h"

#include "ps2_runtime_macros.h"

#include <cstdlib>
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
            if (count <= 50u)
                JA_INFO(Game, "ret-trace enter 0x" << std::hex << address << " a0=0x" << a0 << " a1=0x" << a1 << " a2=0x" << a2
                                                   << " a3=0x" << a3 << " ra=0x" << ra << std::dec << " (call " << count << ")");
            original(rdram, ctx, runtime);
            if (count > 50u)
                return;
            if (ctx->pc == ra)
                JA_INFO(Game, "ret-trace leave 0x" << std::hex << address << " v0=0x" << getRegU32(ctx, 2) << " (call " << std::dec
                                                   << count << ")");
            else
                JA_INFO(Game, "ret-trace 0x" << std::hex << address << " left with pc=0x" << ctx->pc << " (not its return address 0x"
                                             << ra << "; a yield or a non-local exit)");
        }
    }

    void installFromEnvironment(PS2Runtime &runtime)
    {
        (void)runtime;
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
