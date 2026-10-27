// Copied from the Urban Reign PC port (https://github.com/thiagordsfx/urban-reign-recomp, commit 20b30fd)
// src/urban/sha256.h and adapted for Jackass: The Game. GPL-3.0-or-later, like the rest of src/ (NOTICE).
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

namespace jackass
{
    class Sha256
    {
    public:
        Sha256();
        void update(const void *data, size_t size);
        std::array<uint8_t, 32> finish();
        std::string finishHex();

        static std::string hex(const void *data, size_t size);

    private:
        void block(const uint8_t *chunk);

        std::array<uint32_t, 8> m_state;
        std::array<uint8_t, 64> m_buffer{};
        size_t m_bufferSize = 0;
        uint64_t m_totalBytes = 0;
    };
}
