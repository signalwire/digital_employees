# Archived files

## reservation_agent.py
Archived 2026-06-13.

**Why:** orphaned skeleton. Nothing in the codebase imports it (verified via
grep); it was only launched by `start.sh`. Its SWAIG functions are stubs
(`pass`), and the real reservation logic lives in `skills/restaurant_reservation/`
and `swaig_agents.py`.

**It also breaks on `signalwire-agents==1.1.0`** — it uses two APIs removed
after 0.1.38:
- `from signalwire_agents import route`  (the `@route` decorator)
- `from signalwire_agents.core.swaig_function import swaig_function`  (lowercase decorator)

Replacements in 1.1.0 would be `AgentBase.register_routing_callback()` and
`@AgentBase.tool(...)` / `self.define_tool(...)` respectively (note the
`parameters` schema also changed from a list-of-dicts to a JSON-schema dict).

`start.sh` was repointed from `python reservation_agent.py` to
`python start_agents.py` (the README-documented entry point → `app.py`).

**To restore:** `mv archived/reservation_agent.py ../` and revert `start.sh`.
