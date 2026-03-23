# HANDOFF — FunFunPod Neko Edition

**Trigger:** `BARAHIR HANDOFF runpod-gaming`

---

## Current State (2026-03-23)

- **Image:** `eruilu/funfunpod:latest` — **FRESHLY REBUILT AND PUSHED this session**
- **Key fix this session:** X server was crashing (`Invalid argument for -config xorg.conf` → `unable to open display :99.0`). Fixed by replacing Xorg with Xvfb in supervisord via range-based sed patch.
- **Active pod:** NONE — `lwa4x0fxj8d1ga` terminated. Image rebuilt. **Deploy fresh pod to test.**
- **Windows registry:** `FunFunPodID` = `lwa4x0fxj8d1ga` (stale — update after next deploy)

## Dockerfile Fix Applied

Old broken sed (too greedy, didn't match):
```
sed -i 's|command=.*Xorg.*|...|g'
```

New working sed (range-based, targets only `[program:x-server]` block):
```dockerfile
RUN sed -i '/^\[program:x-server\]/,/^\[/{s|^command=.*|command=/usr/bin/Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset|}' \
    /etc/neko/supervisord.conf
```
Build also prints before/after grep for verification.

## Next Action

Deploy fresh pod via RunPod assistant:
```
Deploy FunFunPod. Image: eruilu/funfunpod:latest. GPU: RTX 4000 Ada. Container 50GB, Volume 100GB at /workspace. Ports: 8080/http, 8081/tcp, 22/tcp.
```
Then: hit `https://<POD_ID>-8080.proxy.runpod.net` — expect Neko login page.

## Windows Env Vars (Registry HKCU:\Environment)

| Var | Purpose |
|---|---|
| `Funpod-RunpodGaming` | RunPod API key |
| `FunFunPodID` | Current pod ID |
| `Docker-Funpod-Runpod-Gaming` | Docker Hub PAT |

## Critical Tool Usage Rules for Next Session

**TERMINAL MCP** — use `& "C:\Program Files\Git\bin\git.exe"` for git (not in PATH). Docker IS on PATH. `build-and-push.ps1` works directly via `Set-Location` + `& ".\build-and-push.ps1"`.

**GITHUB MCP** — always `get_file_contents` before `create_or_update_file` to get SHA. Private repo code search returns zero — use `filesystem:search_files` or `filesystem:read_text_file` instead.

**RUNPOD TERMINATION** — Claude terminates pods directly via GraphQL. API key = `Funpod-RunpodGaming` in registry. RunPod assistant deploys; Claude terminates.

**CIC (Claude in Chrome)** — use `find` to get refs before clicking. Input box ref changes after navigation. Always `screenshot` after every action to confirm state. Use `tabs_context_mcp` once per session.

**TOKEN CONSERVATION** — use `filesystem:read_text_file`, `github:get_file_contents`, `terminal:run_command` in parallel where possible. Do NOT take screenshots in loops — use `wait` x3 then one screenshot. Do NOT re-read files already in context.

## Neko Credentials
- Admin: `admin` / `admin`
- User: `neko` / `neko`

## What Failed (DO NOT RETRY)
- Moonlight/Sunshine — UDP blocked by RunPod at network level
- Chisel — Windows Defender HackTool flag
- Tailscale/boringtun — no TUN device
- Parsec — no Linux hosting on consumer accounts
- Custom `NEKO_CAPTURE_VIDEO_PIPELINE` — panic crash
- Setting pipeline env var to `""` — also crashes
- Restarting existing pod with `:latest` — node cache, pulls stale image
- Xorg / xorg.conf in containers — no GPU modesetting, always fails

## BARAHIR Violations

### V-008 — 2026-03-23: Tool Call Exhaustion / Inefficient Polling
**Root cause:** Used repeated `wait`+`screenshot` loops instead of batching waits. Burned tool calls on polling instead of using `terminal:run_command` to curl-probe the endpoint. Ran out of tool calls before completing deploy.
**Correct behavior:** Poll via `terminal:run_command` with `Invoke-WebRequest` in a loop — one tool call per probe. Reserve CIC screenshot calls for confirmation only.

### V-007 — 2026-03-22: 2-Hour Cascading Failure Loop
**Root cause:** Did not escalate to Arena.AI after iteration 2. Burned 5+ pods, SSH failures, credential issues across 2 hours.
**Correct behavior:** Escalate to Arena.AI at iteration 3. Not optional.

## BARAHIR: Arena Escalation Rule
2 unresolved iterations → escalate to Arena.AI. NOT OPTIONAL.
