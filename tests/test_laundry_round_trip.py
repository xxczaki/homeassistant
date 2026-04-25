"""Scenario row 6 – LR → laundry → hang in hallway → LR.

Composition test: exercises Layer 1b cleanup (LR off after entering
laundry), then R2 hallway-dwell turning off laundry, then a return to
LR re-arming via Layer 1.
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_lr_then_laundry_then_hallway_dwell_then_back_to_lr(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    # Settle in LR
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"

    # Move to laundry – current_room flips, Layer 1b's grace timer arms.
    # LR PIR clears as the user leaves (real-world behavior).
    await motion(hass, "living_room", on=False)
    await motion(hass, "laundry_room", on=True)
    assert current_room(hass) == "laundry_room"
    assert light(hass, "laundry_room_light") == "on"

    # Sit past grace; LR gets cleaned up, laundry stays
    await advance(hass, seconds=50)
    assert light(hass, "living_room") == "off"
    assert light(hass, "laundry_room_light") == "on"

    # Step out into the hallway, drop laundry motion
    await motion(hass, "laundry_room", on=False)
    await motion(hass, "hallway", on=True)

    # Hallway-only for 95 s – R2 fires
    await advance(hass, seconds=95)
    assert current_room(hass) == "none"
    assert light(hass, "laundry_room_light") == "off"

    # Return to LR – Layer 1 re-arms
    await motion(hass, "hallway", on=False)
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"
