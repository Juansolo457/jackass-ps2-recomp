#pragma once
// GPL-3.0-or-later, like the rest of src/ (NOTICE).

class PS2Runtime;

namespace jackass::rettrace
{
    // JA_RET_TRACE=0xADDR,...: wrap these guest functions and log $a0-$a3 on entry and $v0 on return
    // (first 50 calls of each). Install after the HLE bindings and before the call profile.
    void installFromEnvironment(PS2Runtime &runtime);
}
