---
description: Toggle fireteam autonomous execution mode
allowed-tools: []
---

# /fireteam Command

Toggle fireteam mode on or off.

## Usage
- `/fireteam on` - Enable fireteam mode for this session
- `/fireteam off` - Disable fireteam mode

## When "on"
- Set session state to enable fireteam
- Write `{"enabled": true}` to `~/.claude/fireteam_state.json`
- Confirm: "Fireteam mode enabled. All tasks will use multi-phase execution."

## When "off"
- Clear session state
- Write `{"enabled": false}` to `~/.claude/fireteam_state.json`
- Confirm: "Fireteam mode disabled. Returning to normal Claude Code behavior."
