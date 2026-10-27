// Jackass: The Game (PS2, SLUS-21627) on the PS2Recomp runtime of the Urban Reign PC port.
// A trimmed version of that port's src/main.cpp (https://github.com/thiagordsfx/urban-reign-recomp, commit 20b30fd):
// CPU check, crash reporter, 16 MB thread stacks, the disc image, the runtime, the recompiled code, the SDK bindings,
// run. Everything Urban Reign specific (mods, aspect patches, fighter hooks, pnach, menus) is left out; Jackass gets
// its own pieces as they are needed. GPL-3.0-or-later, like the rest of src/ (NOTICE).
#include "ps2_runtime.h"
#include "runtime/ps2_async_vif.h"
#include "runtime/ee_scheduler.h"
#include "runtime/ps2_display_options.h"
#include "runtime/gs/gs_threaded_backend.h"
#include "runtime/gs/gs_gpu_backend.h"
#include "runtime/gs/gs_pcsx2_backend.h"
#include "jackass/function_hooks.h"
#include "jackass/game_disc.h"
#include "jackass/hle_bindings.h"
#include "jackass/log.h"

#if defined(PS2X_ENABLE_DEBUG_UI)
#include "ps2_debug_panel.h"
#endif

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <csignal>
#include <exception>
#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>
#include <xmmintrin.h>
#include <pmmintrin.h>

#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
#include <intrin.h>
#else
#include <execinfo.h>
#include <pthread.h>
#include <unistd.h>
#endif

#if !defined(JA_ARCH_NAME)
#define JA_ARCH_NAME "SSE41"
#endif

namespace
{
    // The runtime uses SSE4.1 intrinsics (the PCSX2 minimum); an older CPU gets a message, not an illegal instruction.
    bool checkCpu()
    {
#if defined(_WIN32)
        int regs[4] = {};
        __cpuid(regs, 1);
        const bool sse41 = (regs[2] & (1 << 19)) != 0;
#else
        __builtin_cpu_init();
        const bool sse41 = __builtin_cpu_supports("sse4.1");
#endif
        std::fprintf(stderr, "[cpu] SSE4.1 %s; build %s\n", sse41 ? "yes" : "NO", JA_ARCH_NAME);
        if (!sse41)
            std::fprintf(stderr, "This processor does not support SSE4.1, which this build needs.\n");
        return sse41;
    }

    std::filesystem::path executableDirectory()
    {
#if defined(_WIN32)
        wchar_t buffer[MAX_PATH];
        const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
        if (length > 0 && length < MAX_PATH)
            return std::filesystem::path(buffer).parent_path();
#else
        std::error_code error;
        const std::filesystem::path self = std::filesystem::read_symlink("/proc/self/exe", error);
        if (!error && !self.empty())
            return self.parent_path();
#endif
        return std::filesystem::current_path();
    }

    void setDefaultEnv(const std::string &variable, const std::string &value)
    {
        if (value.empty() || std::getenv(variable.c_str()))
            return;
#if defined(_WIN32)
        _putenv_s(variable.c_str(), value.c_str());
#else
        setenv(variable.c_str(), value.c_str(), 0);
#endif
    }

#if !defined(_WIN32)
    void printStackTrace()
    {
        void *frames[64];
        const int count = backtrace(frames, 64);
        backtrace_symbols_fd(frames, count, STDERR_FILENO);
    }

    void crashSignal(int signal, siginfo_t *info, void *)
    {
        std::fprintf(stderr, "[crash] signal %d at %p on thread %lu\n", signal, info ? info->si_addr : nullptr,
                     static_cast<unsigned long>(pthread_self()));
        printStackTrace();
        std::_Exit(3);
    }

    void installCrashReporter()
    {
        static std::vector<char> alternateStack(256u * 1024u);
        stack_t stack{};
        stack.ss_sp = alternateStack.data();
        stack.ss_size = alternateStack.size();
        sigaltstack(&stack, nullptr);
        struct sigaction action{};
        action.sa_sigaction = crashSignal;
        action.sa_flags = SA_SIGINFO | SA_ONSTACK;
        sigemptyset(&action.sa_mask);
        for (const int signal : {SIGSEGV, SIGBUS, SIGILL, SIGFPE, SIGABRT})
            sigaction(signal, &action, nullptr);
        std::set_terminate([]() {
            std::fprintf(stderr, "[crash] std::terminate\n");
            if (const std::exception_ptr ep = std::current_exception())
            {
                try { std::rethrow_exception(ep); }
                catch (const std::exception &e) { std::fprintf(stderr, "[crash] exception: %s\n", e.what()); }
                catch (...) { std::fprintf(stderr, "[crash] non-std exception\n"); }
            }
            printStackTrace();
            std::_Exit(3);
        });
    }

    // The game runs on std::threads; deep guest call chains run on the host stack. 16 MB, as the MSVC build's /STACK.
    void setDefaultThreadStack()
    {
        pthread_attr_t attributes;
        if (pthread_attr_init(&attributes) != 0)
            return;
        if (pthread_attr_setstacksize(&attributes, 16u * 1024u * 1024u) != 0 || pthread_setattr_default_np(&attributes) != 0)
            std::fprintf(stderr, "[boot] could not set the 16 MB default thread stack\n");
        pthread_attr_destroy(&attributes);
    }
#else
    void installCrashReporter() {}
    void setDefaultThreadStack() {}
#endif

    // The EE's FPU: round toward zero, denormals flushed. Set on the game thread when the guest starts.
    void applyEeFloatingPointMode()
    {
        _MM_SET_ROUNDING_MODE(_MM_ROUND_TOWARD_ZERO);
        _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
        _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
    }

    void printUsage()
    {
        std::cout << "usage: jackass [--iso <path-to-" << jackass::kSerial << ".iso>]\n"
                  << "environment: JA_ISO=<path>, JA_USER_DIR=<folder>, JA_TRACE=BOOT,LOADER,FILE,EE,IOP,GS,VU,SPU2,INPUT,GAME,HOOK|ALL,\n"
                  << "             JA_MISSING_FUNCTION=continue, JA_DEBUG_UI=1, PS2X_* (the runtime's own)\n";
    }

    std::filesystem::path userDirectory(const std::filesystem::path &exeDir)
    {
        const char *value = std::getenv("JA_USER_DIR");
        if (!value || !*value)
            return exeDir;
        std::error_code error;
        const std::filesystem::path dir = std::filesystem::absolute(value, error);
        std::filesystem::create_directories(dir, error);
        return dir;
    }
}

int main(int argc, char *argv[])
{
    if (!checkCpu())
        return 4;
    installCrashReporter();
    setDefaultThreadStack();
    const std::filesystem::path exeDir = executableDirectory();
    const std::filesystem::path userDir = userDirectory(exeDir);
    if (userDir != exeDir)
        setDefaultEnv("PS2X_DATA_DIR", userDir.string()); // the PCSX2 GS's shader cache and texture packs
    jackass::log::configureFromEnvironment();

    std::filesystem::path iso;
    for (int i = 1; i < argc; ++i)
    {
        const std::string arg = argv[i];
        if ((arg == "--iso" || arg == "-iso") && i + 1 < argc)
            iso = argv[++i];
        else if (arg == "--help" || arg == "-h")
        {
            printUsage();
            return 0;
        }
        else if (iso.empty() && arg.rfind("-", 0) != 0)
            iso = arg;
    }
    if (iso.empty())
        if (const char *env = std::getenv("JA_ISO"))
            iso = env;
    if (iso.empty())
    {
        // The repository layout (private/jackass.iso from tools/extract.sh) and a game/ folder next to the program.
        iso = jackass::findDiscImage({userDir / "game", exeDir / "game", exeDir.parent_path() / "game",
                                      exeDir.parent_path().parent_path() / "game", exeDir.parent_path().parent_path() / "private",
                                      exeDir.parent_path().parent_path().parent_path() / "private",
                                      std::filesystem::current_path() / "private", std::filesystem::current_path() / "game",
                                      std::filesystem::current_path()});
    }
    if (iso.empty())
    {
        JA_ERROR(Boot, "no disc image found. Pass --iso <path> to your own " << jackass::kSerial << " disc image.");
        printUsage();
        return 2;
    }

    const std::filesystem::path cacheDir = userDir / "game_data";
    JA_INFO(Boot, "disc image: " << iso.string());
    const jackass::DiscCheckResult disc = jackass::verifyDiscAndPrepare(iso, cacheDir);
    if (!disc.ok)
    {
        JA_ERROR(Boot, disc.error);
        return 3;
    }

    PS2Runtime::IoPaths paths;
    paths.elfPath = disc.bootElfPath;
    paths.elfDirectory = cacheDir;
    paths.hostRoot = cacheDir;
    paths.cdRoot = cacheDir;
    paths.mcRoot = userDir / "memcards" / "mc0";
    if (const char *mcDir = std::getenv("JA_MC_DIR"); mcDir && *mcDir)
        paths.mcRoot = std::filesystem::path(mcDir) / "mc0";
    setDefaultEnv("PS2X_GS_SHADER_CACHE_DIR", (cacheDir / "gs_shaders").string());
    paths.cdImage = std::filesystem::absolute(iso);
    std::error_code error;
    std::filesystem::create_directories(paths.mcRoot, error);

    // GS and VIF/VU threading defaults, as the Urban Reign port sets them on Linux: PCSX2's GS (libpcsx2gs.so) when
    // present, the software GS otherwise; the asynchronous VIF1/VU1/GIF workers only with PCSX2's GS (with the
    // software GS they stalled that game's intro). PS2X_MTVU=1/0 still decides.
    GSThreadedBackend::SetEnabledByDefault(true);
    GSGpuBackend::SetAsyncPresentDefault(true);
#if defined(_WIN32)
    GSThreadedBackend::SetGpuByDefault(true);
    ps2x::asyncvif::setDefaultEnabled(true);
#else
    const bool pcsx2Gs = GSPcsx2Backend::Requested();
    GSThreadedBackend::SetGpuByDefault(false);
    ps2x::asyncvif::setDefaultEnabled(pcsx2Gs);
#endif
    ps2x::asyncvif::setHostPacingDefault(true);
    EeScheduler::setHostPacingDefault(true);
    // Jackass loads its own MCMAN/MCSERV/PADMAN/SIO2MAN (SDK 3.0) from the disc: run them, as Urban Reign does, over the
    // emulated SIO2 card and pads rather than the runtime's MCSERV HLE. Revisit if the card or pads misbehave.
    setDefaultEnv("PS2X_IOP_HLE_MCSERV", "0");
    setDefaultEnv("PS2X_SIO2_RECV1", "2");
    // The finished image stays on the GPU (no RAM round trip per frame).
    setDefaultEnv("PS2X_GS_DIRECT_PRESENT", "1");

    try
    {
        PS2Runtime runtime;
#if defined(PS2X_ENABLE_DEBUG_UI)
        static PS2DebugPanel debugPanel;
        {
            const char *openAtStart = std::getenv("JA_DEBUG_UI");
            debugPanel.setVisible(openAtStart && *openAtStart == '1');
        }
        runtime.setDebugUiCallbacks(
            [](PS2Runtime &, void *userData) { static_cast<PS2DebugPanel *>(userData)->initialize(); },
            [](PS2Runtime &rt, void *userData) {
                auto *panel = static_cast<PS2DebugPanel *>(userData);
                panel->draw(rt);
                GSPcsx2Backend::SetHostUiVisible(panel->isVisible());
            },
            [](PS2Runtime &, void *userData) { static_cast<PS2DebugPanel *>(userData)->shutdown(); },
            &debugPanel);
#endif
        {
            const char *fullscreen = std::getenv("JA_START_FULLSCREEN");
            ps2_host_display::setStartFullscreen(fullscreen && *fullscreen == '1');
        }
        if (!runtime.initialize("Jackass: The Game"))
        {
            JA_ERROR(Boot, "runtime initialization failed");
            return 1;
        }
        JA_INFO(Boot, "runtime initialized; loading " << disc.bootElfPath.string());
        if (!runtime.loadELF(disc.bootElfPath.string()))
        {
            JA_ERROR(Boot, "failed to load " << disc.bootElfPath.string());
            return 1;
        }
        JA_INFO(Boot, "ELF loaded, entry 0x" << std::hex << runtime.cpu().pc);
        PS2Runtime::setIoPaths(paths);

        const char *missingPolicy = std::getenv("JA_MISSING_FUNCTION");
        runtime.setMissingFunctionPolicy(missingPolicy && std::string(missingPolicy) == "continue"
                                             ? PS2Runtime::MissingFunctionPolicy::ContinueToTarget
                                             : PS2Runtime::MissingFunctionPolicy::Stop);
        jackass::FunctionHooks::instance().attach(runtime);
        jackass::FunctionHooks::instance().observeEntry(runtime.cpu().pc, "boot_entry", [](uint8_t *, R5900Context *, PS2Runtime *) {
            applyEeFloatingPointMode();
            JA_INFO(Ee, "EE FPU host mode: round toward zero, denormals flushed");
        });
        jackass::installHleBindings(runtime);
        jackass::FunctionHooks::instance().logBindings();

        JA_INFO(Boot, "starting guest at 0x" << std::hex << runtime.cpu().pc);
        runtime.run();
        JA_INFO(Boot, "runtime exited");
    }
    catch (const std::exception &e)
    {
        JA_ERROR(Boot, "fatal: " << e.what());
        std::cout.flush();
        std::_Exit(1);
    }
    std::cout.flush();
    std::_Exit(0);
}
