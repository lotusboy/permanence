## Running this on Antigravity (experimental)

This command was written for another tool's subagent calls. On Antigravity, read it with these
five substitutions. Everything else in it applies as written.

1. **Dispatching.** Where the text says to dispatch with `subagent_type: "role:…"`, call
   `invoke_subagent` with one entry in `Subagents`: `TypeName` is that same `role:…` string, kept
   exactly, colon included; `Role` is a short label; `Prompt` is the brief; `Model` is `inherit`.
   A hook replaces the role with the agent that fills it, and the tool result says so. Do not
   define a subagent, and do not pick an agent yourself. If the call is refused, the reason says
   what to do.
2. **Waiting.** A subagent answers later, by message. Do not finish your turn, and do not start the
   next step, until its message has arrived.
3. **Talking to a running subagent.** Where the text says SendMessage, use `send_message` with the
   conversation id that `invoke_subagent` returned.
4. **Preflight.** Put `PERMA_HARNESS=antigravity` in front of every `team-preflight.py` command, so
   it checks the agents installed for Antigravity.
5. **Two checks are yours here, because no hook makes them.** After a reviewer finishes, confirm
   its record folder exists under the repo's reviews folder before you go on; if it does not, send
   the reviewer back once. And a role's model is set in the installed agent's own file, so do not
   pass a model name.

