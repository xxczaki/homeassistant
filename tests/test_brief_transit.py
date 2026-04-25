"""Scenarios where the user briefly visits the hallway without committing
to another tracked room.

Row 3 – LR → hallway (grab mail) → LR.
    Hallway motion fires, but you go straight back. R2 must not fire
    because hallway motion does not stay on for 90 s, and `current_room`
    never changes (hallway is a transit zone, not tracked).

Row 8 – LR → hallway → kitchen (untracked) → … → back to LR.
    From HA's perspective: brief hallway transit, then quiet (untracked
    kitchen), then transit back. Person.antek stays 'home' so the
    leave-home no-motion fallback doesn't kick in. LR remains lit through
    the entire kitchen visit.
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


async def test_lr_to_untracked_kitchen_via_hallway_keeps_lr_on(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    # Settle in LR
    await motion(hass, "living_room", on=True)

    # Walk through hallway towards the (untracked) kitchen
    await motion(hass, "living_room", on=False)
    await motion(hass, "hallway", on=True)
    await advance(hass, seconds=5)
    await motion(hass, "hallway", on=False)

    # Idle period in the kitchen – no sensor events. Short, just enough
    # to confirm no rule fires on its own. R2's 90 s `for:` requires
    # hallway motion to *stay on* throughout, which it isn't here, so
    # no real-time-cost virtual-time advance is needed.
    await advance(hass, seconds=15)

    # Walk back through hallway to LR
    await motion(hass, "hallway", on=True)
    await advance(hass, seconds=5)
    await motion(hass, "hallway", on=False)
    await motion(hass, "living_room", on=True)

    # LR should still be lit; current_room should still be living_room
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"
