// Copied from the Urban Reign PC port (https://github.com/thiagordsfx/urban-reign-recomp, commit 20b30fd)
// src/urban/game_disc.h and adapted for Jackass: The Game. GPL-3.0-or-later, like the rest of src/ (NOTICE).
#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace jackass
{
    // Jackass: The Game (USA), SLUS-21627 (games/jackass/game.toml).
    inline constexpr const char *kSerial = "SLUS-21627";
    inline constexpr const char *kBootElfPath = "SLUS_216.27";
    inline constexpr const char *kBootElfSha256 = "a6b5dd8013264f40a6af85b1461aa34647bb9a1848b7190d29f9426f90913701";

    struct DiscCheckResult
    {
        bool ok = false;
        std::string error;
        std::filesystem::path bootElfPath;
    };

    std::filesystem::path findDiscImage(const std::vector<std::filesystem::path> &searchRoots);
    DiscCheckResult verifyDiscAndPrepare(const std::filesystem::path &image, const std::filesystem::path &cacheDir);
}
