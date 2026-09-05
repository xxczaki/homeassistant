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

    # Step out to bathroom, with the LR PIR clearing first. Note this is the
    # idealised shape – a real walk arrives while the LR latch is still on,
    # which test_transit_lights_new_room_with_old_pir_latched covers.
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

    # LR PIR clears as the user leaves, then the bathroom edge commits.
    await motion(hass, "living_room", on=False)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"

    # Sit in bathroom past the grace window – Layer 1b targets LR
    await advance(hass, seconds=60)
    assert light(hass, "bathroom_light") == "on"
    assert light(hass, "living_room") == "off"


async def test_transit_lights_new_room_with_old_pir_latched(presence_hass):
    """The real-world transit shape, which the rest of this suite got wrong.

    Recorder trace of an LR -> hallway -> bathroom walk (2026-09-05):
      14:45:18.747 living_room PIR on
      14:45:22.214 hallway PIR on       (+3.5 s)
      14:45:24.884 bathroom PIR on      (+6.1 s)
      14:45:28.697 living_room PIR off  (+9.9 s – the Hue latch expiring)

    The LR PIR latches ~10 s after last motion but the walk takes 4-6 s, so
    the old room's PIR is STILL ON when you arrive in the new room. Every
    other transition test here clears the old PIR first, which is how the
    co-fire guard's false premise survived code review: it suppressed
    exactly this edge, and the bathroom lamp waited 16.3 s for the PIR to
    cycle off and re-fire before lighting.

    The new room must light on the arriving edge, with no second edge and
    no waiting.
    """
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"

    # Walk out through the hallway. The LR PIR is still latched on.
    await motion(hass, "hallway", on=True)
    await motion(hass, "bathroom", on=True)

    assert current_room(hass) == "bathroom"
    assert light(hass, "bathroom_light") == "on"

    # The LR latch expires a few seconds later; nothing should change.
    await motion(hass, "living_room", on=False)
    assert current_room(hass) == "bathroom"
    assert light(hass, "bathroom_light") == "on"
