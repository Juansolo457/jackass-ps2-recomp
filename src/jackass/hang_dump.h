// Copied from the Urban Reign PC port (https://github.com/thiagordsfx/urban-reign-recomp, commit 20b30fd)
// src/urban/hang_dump.h and adapted for Jackass: The Game. GPL-3.0-or-later, like the rest of src/ (NOTICE).
#pragma once

class PS2Runtime;

namespace jackass::hangdump
{
    // JA_HANG_DUMP=<seconds>: after that delay, print the native stack of every thread in the process to stderr.
    // JA_HANG_DUMP_REPEAT=<seconds>: keep dumping at that interval afterwards.
    // JA_HANG_DUMP_NATIVE=0: skip the native stacks (guest kernel state and call profile only).
    void startFromEnvironment();

    // Once set, dumps also include the guest EE kernel state (threads, PCs, wait reasons, semaphores).
    void setRuntime(PS2Runtime *runtime);
}
