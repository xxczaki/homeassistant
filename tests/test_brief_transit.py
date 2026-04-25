"""Scenario row 3 – LR → hallway (grab mail) → LR.

Hallway motion fires, but you go straight back. R2 must not fire
because hallway motion does not stay on for 90 s, and `current_room`
never changes (hallway is a transit zone, not tracked).
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_brief_hallway_transit_back_to_lr_keeps_lr_on(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"

    # Step out for a few seconds
    await motion(hass, "living_room", on=False)
    await motion(hass, "hallway", on=True)
    await advance(hass, seconds=10)
    await motion(hass, "hallway", on=False)

    # Back in LR
    await motion(hass, "living_room", on=True)

    # Settle for a few seconds; R2 (90 s hallway-only) cannot fire
    # because hallway is now off and LR motion is on
    await advance(hass, seconds=10)

    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"
