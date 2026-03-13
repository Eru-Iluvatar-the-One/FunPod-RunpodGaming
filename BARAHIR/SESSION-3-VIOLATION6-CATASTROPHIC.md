# BARAHIR VIOLATION LOG — Session 3 ADDENDUM (2026-03-13)

## VIOLATION 6: CATASTROPHIC — Switched from viable Sunshine/Moonlight to dead-end Parsec
**Severity:** CRITICAL — 3+ hours wasted, multiple pods burned
**Description:** In Session 1, user was working on Sunshine/Moonlight streaming. The only blocker was RunPod's UDP restriction. Instead of solving the UDP problem (Tailscale tunnels UDP over TCP trivially), Claude switched the user to Parsec. Arena.AI confirmed Parsec CANNOT host from Docker containers — it requires NVFBC which requires real Xorg which requires DRM modesetting which containers can't get. This was a dead end from the start.
**Root cause:** Did not research whether Parsec hosting works in Docker containers before recommending the switch. Hallucinated a viable path.
**Impact:** 3+ hours, 3 sessions, 2 pods, ~$2+ in RunPod costs, massive user frustration — all for nothing.
**Correct path:** Sunshine + Tailscale. Tailscale tunnels Moonlight's UDP over TCP/443, bypassing RunPod's UDP block. This was solvable in Session 1.
