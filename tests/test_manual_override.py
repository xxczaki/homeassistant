"""Scenario row 9 — R4 (manual_light_override).

When a light is turned off while motion is ON in that room, the suppress
flag is set so the next motion event won't bring the light back on.
Turning the light back on (manually or by any path) clears the flag.
"""

from .helpers import current_room, light, motion


async def _suppress(hass, room: str) -> str:
    return hass.states.get(f"input_boolean.suppress_{room}_auto_light").state


async def _set_suppress(hass, room: str, on: bool) -> None:
    await hass.services.async_call(
        "input_boolean",
        "turn_on" if on else "turn_off",
        {"entity_id": f"input_boolean.suppress_{room}_auto_light"},
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_manual_off_with_motion_on_sets_suppress(presence_hass):
    hass = presence_hass

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"
    assert await _suppress(hass, "living_room") == "off"

    # User toggles LR off while still in the room (motion on)
    await hass.services.async_call(
        "light", "turn_off",
        {"entity_id": "light.living_room"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert light(hass, "living_room") == "off"
    assert await _suppress(hass, "living_room") == "on"


async def test_suppressed_room_does_not_auto_on(presence_hass):
    hass = presence_hass
    await _set_suppress(hass, "living_room", True)

    await motion(hass, "living_room", on=True)

    # Suppress is on → Layer 1 skips turn_on. Light stays off.
    assert light(hass, "living_room") == "off"
    # current_room is still updated, since tracking is independent of suppress
    assert current_room(hass) == "living_room"


async def test_manual_on_clears_suppress(presence_hass):
    hass = presence_hass
    await _set_suppress(hass, "living_room", True)
    assert await _suppress(hass, "living_room") == "on"

    # User turns LR on directly
    await hass.services.async_call(
        "light", "turn_on",
        {"entity_id": "light.living_room"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert light(hass, "living_room") == "on"
    assert await _suppress(hass, "living_room") == "off"
