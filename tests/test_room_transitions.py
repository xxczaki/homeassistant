"""Scenario rows 4 and 5: LR → bathroom round-trip behaviours.

Row 4 – quick visit (back to LR before grace expires):
    Bathroom light comes on during the visit, but Layer 1b's pending
    cleanup re-targets bathroom (not LR) once current_room flips back to
    living_room. So LR ends up on, bathroom ends up off.

Row 5 – long visit (no return within grace):
    Bathroom stays on the entire stay; Layer 1b cleanup turns off LR
    `presence_grace_seconds` after the bathroom transition.
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_lr_then_bathroom_then_back_to_lr_within_grace(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    # Settle in LR
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"

    # Step out to bathroom. LR PIR clears as the user leaves – the co-fire
    # guard only commits the room switch when the previous room's motion is
    # no longer active (two tracked PIRs on at once is sensor cross-fire,
    # not a transition).
    await motion(hass, "living_room", on=False)
    await motion(hass, "hallway", on=True)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"
    assert light(hass, "bathroom_light") == "on"

    # Within grace: LR is still lit (cleanup hasn't fired yet)
    await advance(hass, seconds=20)
    assert light(hass, "living_room") == "on"

    # Quick return – bathroom PIR clears first (user leaves it), then the
    # LR sensor needs an off→on transition to re-fire Layer 1.
    await motion(hass, "bathroom", on=False)
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"

    # After full grace from the LR-return, bathroom gets cleaned up
    await advance(hass, seconds=50)
    assert light(hass, "living_room") == "on"
    assert light(hass, "bathroom_light") == "off"


async def test_lr_then_bathroom_long_stay_cleans_up_lr(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"

    # LR PIR clears as the user leaves; the co-fire guard then commits the
    # bathroom switch (only one tracked room reporting motion).
    await motion(hass, "living_room", on=False)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"

    # Sit in bathroom past the grace window – Layer 1b targets LR
    await advance(hass, seconds=60)
    assert light(hass, "bathroom_light") == "on"
    assert light(hass, "living_room") == "off"
