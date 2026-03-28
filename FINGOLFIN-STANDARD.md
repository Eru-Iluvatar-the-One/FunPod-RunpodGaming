# FINGOLFIN QUALITY STANDARD v2.0
> "He stood alone. And he challenged the Dark Lord to single combat."
> Last updated: 2026-03-27T21:00:00Z

This document is **NON-NEGOTIABLE**. Every app, UI, tool, and deliverable in Project Arda
must meet or exceed these standards. Violations are termination-grade.

---

## UI TIER HIERARCHY

| Tier | Stack | Status |
|------|-------|--------|
| **GOLD** | Electron + React + TypeScript | Target for all new apps |
| **SILVER** | PyQt6 + Catppuccin QSS | Minimum acceptable for Python tools |
| **BANNED** | Tkinter, raw HTML without framework | Never. No exceptions. Migration scheduled for all legacy. |

### Gold Standard (Electron + React)
- Frameless window with custom titlebar (drag, minimize, maximize, close)
- React functional components + hooks
- TypeScript strict mode
- Vite bundler
- CSS Modules or Tailwind with Catppuccin tokens
- Smooth animations (IntersectionObserver fades, transitions)
- Responsive grid layouts
- IPC between main/renderer via preload bridge
- Auto-updater ready

### Silver Standard (PyQt6)
- Dark theme mandatory (Catppuccin Mocha default)
- Tile/card layouts
- Drag-and-drop zones where applicable
- Progress bars for any operation > 1 second
- DPI-aware (highdpi.py)
- Icons for all actions
- Keyboard shortcuts for all primary actions
- Graceful error handling with user-visible messages
- Single-file launch capability
- QSS theming via arda_theme.py

### Banned
- Tkinter: scheduled for removal everywhere. Zero new code.
- Raw unstyled HTML: never ship without Catppuccin tokens.
- Alert/confirm/prompt dialogs as primary UI: use proper components.

---

## THEME: CATPPUCCIN MOCHA (mandatory default)

```
base:     #1e1e2e
mantle:   #181825
crust:    #11111b
surface0: #313244
surface1: #45475a
surface2: #585b70
overlay0: #6c7086
overlay1: #7f849c
text:     #cdd6f4
subtext0: #a6adc8
subtext1: #bac2de
accent:   #89b4fa  (blue)
green:    #a6e3a1
red:      #f38ba8
yellow:   #f9e2af
peach:    #fab387
mauve:    #cba6f7
teal:     #94e2d5
pink:     #f5c2e7
```

All 6 theme variants supported via arda_theme.py:
Catppuccin Mocha (default), Dracula, Mordor, Fingolfin, Tokyo Night, Gruvbox.

---

## REFERENCE APPLICATIONS

These are the quality bar. If your output doesn't match, it doesn't ship.

- **PDF Candy Desktop** — layout, polish, icon quality
- **Obsidian** — markdown editing, plugin architecture, theming
- **Spotify** — responsive grid, smooth transitions, dark theme
- **VS Code** — command palette, keyboard-first, extension model

---

## CODE QUALITY

- Type annotations on ALL functions (params + return types)
- Module-level docstrings on all files
- `from __future__ import annotations` in all Python files
- Mandos audit score: 85+ (A) minimum before merge
- QSS semicolons are FALSE POSITIVES — do not count against score
- `dist/`, `build/`, `PASTA-*` excluded from audits

---

## DELIVERY RULES

- ONE SHOT RULE: One fenced code block, one copy button. Never interleave prose.
- Pre-Implementation Gate: State WHAT/HOW/WHY before code/config/deploy.
- Long-running scripts: MANDATORY `[N/total]` progress output per item.
- 2 failed iterations → Arena.ai escalation, no exceptions.
- Confirmation threshold: ZERO. Execute immediately.

---

## EXEMPT ONLY IF

Eru explicitly says "quick and dirty" or "CLI only". Otherwise, Fingolfin standard applies.
