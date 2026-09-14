#!/bin/bash
# antigravity/pre-tool-use-hook.sh — must always return a real decision object. A bare {} (or
# any malformed response) fails closed and blocks the tool call — confirmed live
# (design/antigravity-binding.md §2). Permanence has no reason to gate any tool, so this always
# allows; its only real job is existing, so a Permanence-caused response failure never silently
# blocks the user's own tool calls.
echo '{"decision": "allow"}'
