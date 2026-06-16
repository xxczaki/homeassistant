"""Regression: the 2026-06-17 00:21 production incident.

Reconstructed from the recorder DB:
  00:15:18 user returns to LR -> current_room=living_room, LR lights on
  00:18:14 LR PIR fires on (user still in the room)
  00:18:17 hallway + bathroom PIRs BOTH fire on, ~3 s later, while the
           LR PIR is still on – physically impossible for one occupant
  00:18:17 Layer 1 latches current_room=bathroom (last edge wins)
  00:21:17 R1b fires 180 s later -> light.living_room OFF on a user who
           never left the living room; the bathroom light stayed lit.

A single occupant cannot be in two tracked rooms at once (model
assumption #1). When a second tracked PIR co-fires while the current
room's PIR is still active, the reading is ambiguous sensor cross-fire,
so Layer 1 must HOLD current_room rather than chase the spurious blip.
A genuine transition clears the previous room's PIR first, so it is
unaffected (see test_room_transitions).
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_cofire_blip_does_not_steal_room_from_seated_user(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    # Established and seated in the LR; the PIR is still reporting motion.
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"

    # A spurious bathroom detection co-fires with the hallway while the LR
    # PIR is still on. current_room must NOT flip to bathroom.
    await motion(hass, "hallway", on=True)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "living_room"

    # The blip clears; the user stays put and stops producing motion edges.
    await motion(hass, "bathroom", on=False)
    await motion(hass, "hallway", on=False)
    await motion(hass, "living_room", on=False)

    # Past the grace window: R1b must not turn off the room the user is in.
    # Pre-fix this asserted off – current_room was 'bathroom' and the LR
    # was cleaned up as a non-current room.
    await advance(hass, seconds=50)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"


async def test_cofire_does_not_block_switch_once_old_room_clears(presence_hass):
    """The guard holds only while the previous room's PIR is still active.

    Once the LR PIR clears, the next bathroom motion edge commits the
    switch normally – the guard must not strand a user who really did move.
    """
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"

    # Ambiguous co-fire is ignored...
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "living_room"

    # ...but once the LR PIR clears and the bathroom re-fires, the user has
    # genuinely moved: commit the switch.
    await motion(hass, "living_room", on=False)
    await motion(hass, "bathroom", on=False)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"
    assert light(hass, "bathroom_light") == "on"
