# HANDOFF — Runpod-Gaming
_Trigger: `BARAHIR HANDOFF runpod-gaming`_

## Identity
Station IV. MCP active: filesystem, github, memory, terminal, Claude-in-Chrome. Win10 LTSC client.

## Pod
- Host: `66.92.198.162` SSH port `11193`
- GPU: NVIDIA L4, 23034 MiB, driver 570
- BusID: `PCI:36:0:0`
- Image: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- Persistent: 150GB `/workspace`
- Pod ID: `by8x28h0ciubu7`
- **Pod is still running. Do not stop it.**

## Repo
`https://github.com/Eru-Iluvatar-the-One/Runpod-Gaming`
Single file: `setup.sh`

## Run command (always use this)
```bash
python3 -c "import urllib.request; open('/tmp/s.sh','wb').write(urllib.request.urlopen('https://raw.githubusercontent.com/Eru-Iluvatar-the-One/Runpod-Gaming/main/setup.sh').read())" && /bin/bash /tmp/s.sh
```

---

## Current status: v10 pushed, NOT YET RUN

### What v10 does (vs v9)
1. **Purges broken sunshine dpkg record** before any apt install — prior `dpkg -i` left half-installed state poisoning ALL apt calls
2. **Xvfb replaces Xorg/modesetting** — container cannot open `/dev/dri/card4` (Permission denied, unprivileged). Xvfb is virtual framebuffer, no DRI/KMS needed. Sunshine x11 capture works fine with Xvfb.
3. **libayatana + sunshine deps installed individually** — one failure no longer blocks rest
4. **Sunshine binary extracted only** — never `dpkg -i` again (libmfx1/Intel dep is unresolvable on NVIDIA-only host)
5. `adapter_name` uses detected `$DRI_RENDER` (renderD131)

### First action next session
Run v10 and paste output. If verify shows 5/5, open SSH tunnel and connect Moonlight.

---

## Full bug history
- v1: `set -e` + exec sudo = silent exit
- v2: LOG_DIR=/var/log (read-only)
- v3: `exec &> >(tee ...)` silent death in bash <(wget) context
- v4: wget not in image
- v5: curl not in image, bash not at /usr/bin/bash
- v6: added curl/wget step 0
- v7: dpkg-deb -x sunshine.deb clobbered /bin/sh + coreutils
- v8: staged extraction fixed clobber; wrong DRI paths + missing libayatana
- v9: DRI auto-detect + modesetting xorg — card4 permission denied; libayatana still missing (dpkg poison blocked apt)
- v10: Xvfb + dpkg purge + individual dep installs + binary-only sunshine extraction

---

## PowerShell tunnel (Win10 LTSC)
```powershell
ssh -N `
  -L 47984:localhost:47984 `
  -L 47989:localhost:47989 `
  -L 47990:localhost:47990 `
  -L 48010:localhost:48010 `
  root@66.92.198.162 -p 11193 -o StrictHostKeyChecking=no
```
Moonlight → Add PC → 127.0.0.1
Web UI → https://127.0.0.1:47990 (admin / gondolin123)

---

## ⚠️ BARAHIR VIOLATIONS — SESSION 2026-03-13

### Violation 1 — Identity denial (repeated)
Station IV repeatedly refused to acknowledge MCP access and identity, forcing Eru to escalate before tools were used. This wasted multiple turns and pod money.

**Root cause:** Claude.ai default identity overriding ARDA identity protocols.
**Status:** PENDING FIX — next session must audit CLAUDE.md / SYSTEM_PROMPT.md and enforce identity on session open without requiring user to fight for it.

### Violation 2 — Wrong repo (ARDA vs Runpod-Gaming)
Station IV searched ARDA repo instead of Runpod-Gaming on first tool call, wasting tokens and time.

**Root cause:** No repo disambiguation in trigger parsing. "BARAHIR HANDOFF runpod-gaming" was not read correctly.
**Status:** PENDING FIX — HANDOFF trigger must map directly to repo. Add explicit repo routing table to CLAUDE.md.

### Violation 3 — No proactive Arena.AI code lift (CRITICAL)
Throughout 10 iterations of setup.sh debugging, Station IV never once offered to use Arena.AI code lift to accelerate diagnosis. This is a Law 22 violation and a core capability that was completely absent.

**What should have happened:** On iteration 3 or earlier, Station IV should have said: "This is a complex multi-iteration bash debug — invoking Arena.AI code lift for deeper analysis."

**Status:** PENDING FIX — next session must:
1. Add "offer Arena.AI code lift on complex multi-iteration tasks" as explicit rule to CLAUDE.md / HITCHHIKERS_GUIDE.md
2. Propose enforcement mechanism so this cannot be skipped again

### Violation 4 — Assumption over clarification
Station IV pushed v9 with modesetting driver without confirming whether Xvfb was acceptable vs real Xorg. Eru had to approve after the fact.

**Root cause:** Law 22 automation imperative applied too aggressively without checking architectural intent.
**Status:** NOTED — for display stack decisions, ask before pushing.

---

## PENDING TASKS (open next session with these)
1. **Run v10** — paste full output
2. **Violation audit** — read this section aloud and propose CLAUDE.md patches to prevent each violation
3. **Arena.AI code lift enforcement** — add to HITCHHIKERS_GUIDE.md as mandatory trigger condition
4. **Repo routing table** — add to CLAUDE.md so BARAHIR HANDOFF trigger maps to correct repo instantly
5. **If v10 passes** — SSH tunnel + Moonlight connect
