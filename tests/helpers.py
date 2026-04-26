"""DSL for writing scenarios – keeps tests reading like the matrix in
`docs/presence-model.md`.

`motion(hass, "bathroom")` is the executable form of "user enters bathroom."

Virtual time: the suite anchors a per-test virtual clock at the first
`advance()` call. Subsequent advances accumulate against that anchor,
so 5 × `advance(seconds=10)` deterministically lands at T+50 – not at
six independent T+10 events (which is what naive `now() + delta` does
because real wall time barely moves between calls).
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

# Per-test cumulative virtual time. Set on first advance(); reset by the
# `presence_hass` fixture between tests via `reset_clock`.
_virtual_now: dict[int, "dt_util.dt.datetime"] = {}


def reset_clock(hass: HomeAssistant) -> None:
    _virtual_now.pop(id(hass), None)


# ── stimulus ────────────────────────────────────────────────────────────


async def motion(hass: HomeAssistant, room: str, on: bool = True) -> None:
    """Set a motion sensor to on/off and yield once so triggers fire.

    `await hass.async_block_till_done()` would also wait for any
    `async_call_later` callbacks scheduled by automation `delay:` steps
    – that's real wall-time, not virtual, so a `delay: 45` blocks the
    test for 45 s. We yield with `asyncio.sleep(0)` instead, which lets
    the state-change event propagate to listeners (and triggers run
    their synchronous prelude) but doesn't await scheduled callbacks.
    The next `advance()` call will pump virtual time and let those
    pending delays elapse.

    Accepts either a short room name ("bathroom") or a full entity_id
    ("binary_sensor.bathroom_motion_occupancy").
    """
    if not room.startswith("binary_sensor."):
        room = f"binary_sensor.{room}_motion_occupancy"
    hass.states.async_set(room, "on" if on else "off")
    await asyncio.sleep(0)


async def advance(hass: HomeAssistant, *, seconds: int) -> None:
    """Advance the test's virtual clock by N seconds and run due timers."""
    key = id(hass)
    base = _virtual_now.get(key) or dt_util.utcnow()
    new_now = base + timedelta(seconds=seconds)
    _virtual_now[key] = new_now
    async_fire_time_changed(hass, new_now)
    await hass.async_block_till_done()


async def set_grace(hass: HomeAssistant, seconds: int) -> None:
    """Set the presence_grace_seconds slider value at runtime."""
    await hass.services.async_call(
        "input_number",
        "set_value",
        {"entity_id": "input_number.presence_grace_seconds", "value": seconds},
        blocking=True,
    )
    await hass.async_block_till_done()


async def set_lux_threshold(hass: HomeAssistant, lx: int) -> None:
    """Set the LR daylight gate slider at runtime."""
    await hass.services.async_call(
        "input_number",
        "set_value",
        {"entity_id": "input_number.light_on_lux_threshold", "value": lx},
        blocking=True,
    )
    await hass.async_block_till_done()


async def set_lr_illuminance(hass: HomeAssistant, lx: int) -> None:
    """Seed the LR Hue PIR's illuminance reading."""
    hass.states.async_set("sensor.living_room_motion_illuminance", str(lx))
    await asyncio.sleep(0)


# ── inspection ──────────────────────────────────────────────────────────


def current_room(hass: HomeAssistant) -> str:
    return hass.states.get("input_select.current_room").state


def light(hass: HomeAssistant, name: str) -> str:
    """State of a light, accepting short ('bathroom_light') or full id."""
    if not name.startswith("light."):
        name = f"light.{name}"
    state = hass.states.get(name)
    return state.state if state else "unknown"
