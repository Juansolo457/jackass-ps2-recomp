// Copied from the Urban Reign PC port (https://github.com/thiagordsfx/urban-reign-recomp, commit 20b30fd)
// src/urban/call_profile.h and adapted for Jackass: The Game. GPL-3.0-or-later, like the rest of src/ (NOTICE).
#pragma once

class PS2Runtime;

namespace jackass::callprofile
{
    // JA_CALL_PROFILE=1: count calls to every recompiled function entry (wraps the dispatch table slots, so it
    // must run after all other bindings). Costs one extra indirect call per guest call.
    void installFromEnvironment(PS2Runtime &runtime);

    // Prints the most called guest functions since the previous report (no-op when profiling is off).
    void report(int top);
}
