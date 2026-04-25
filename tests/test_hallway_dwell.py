"""Scenario row 7 — R2 (hallway dwell turnoff).

The user steps out of LR into the hallway and stays there (e.g. hanging
laundry, tying shoes). After 90 s of hallway-only activity (hallway
motion ON AND every tracked-room motion OFF), R2 fires: turns off the
current_room's light and resets current_room to 'none'.

Brief transit through the hallway must NOT trigger this rule — covered
in `test_brief_transit.py`.
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_hallway_dwell_turns_off_current_room(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    # Settle in LR
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"

    # Step out: LR motion clears, hallway motion stays on
    await motion(hass, "living_room", on=False)
    await motion(hass, "hallway", on=True)

    # 95 s of hallway-only activity — R2's `for: 90` should fire
    await advance(hass, seconds=95)

    assert current_room(hass) == "none"
    assert light(hass, "living_room") == "off"
