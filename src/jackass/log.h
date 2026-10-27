// Copied from the Urban Reign PC port (https://github.com/thiagordsfx/urban-reign-recomp, commit 20b30fd)
// src/urban/log.h and adapted for Jackass: The Game. GPL-3.0-or-later, like the rest of src/ (NOTICE).
#pragma once

#include <cstdint>
#include <sstream>
#include <string>
#include <string_view>

namespace jackass::log
{
    enum class Category : uint32_t
    {
        Boot = 1u << 0,
        Loader = 1u << 1,
        File = 1u << 2,
        Ee = 1u << 3,
        Iop = 1u << 4,
        Gs = 1u << 5,
        Vu = 1u << 6,
        Spu2 = 1u << 7,
        Input = 1u << 8,
        Game = 1u << 9,
        Hook = 1u << 10,
    };

    enum class Level
    {
        Error,
        Warn,
        Info,
        Trace,
    };

    void configureFromEnvironment();
    void setTraceMask(uint32_t mask);
    bool traceEnabled(Category category);
    void write(Category category, Level level, std::string_view message);
    // Seconds since the log started: the time stamp of every log line ("[  12.3456]").
    double elapsedSeconds();
    std::string_view name(Category category);
}

#define JA_LOG(cat, lvl, expr)                                                   \
    do                                                                             \
    {                                                                              \
        if ((lvl) != ::jackass::log::Level::Trace || ::jackass::log::traceEnabled(cat)) \
        {                                                                          \
            std::ostringstream jaLogStream_;                                     \
            jaLogStream_ << expr;                                                \
            ::jackass::log::write((cat), (lvl), jaLogStream_.str());                \
        }                                                                          \
    } while (0)

#define JA_INFO(cat, expr) JA_LOG(::jackass::log::Category::cat, ::jackass::log::Level::Info, expr)
#define JA_WARN(cat, expr) JA_LOG(::jackass::log::Category::cat, ::jackass::log::Level::Warn, expr)
#define JA_ERROR(cat, expr) JA_LOG(::jackass::log::Category::cat, ::jackass::log::Level::Error, expr)
#define JA_TRACE(cat, expr) JA_LOG(::jackass::log::Category::cat, ::jackass::log::Level::Trace, expr)
