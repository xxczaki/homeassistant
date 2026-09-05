"""Regression: the 2026-06-17 00:21 production incident – and the
2026-09-05 misdiagnosis of it.

Reconstructed from the recorder DB:
  00:15:18 user returns to LR -> current_room=living_room, LR lights on
  00:18:14 LR PIR fires on (user still in the room)
  00:18:17 hallway + bathroom PIRs BOTH fire on, ~3 s later, while the
           LR PIR is still on
  00:18:17 Layer 1 latches current_room=bathroom (last edge wins)
  00:21:17 R1b fires 180 s later -> light.living_room OFF on a user who
           never left the living room

The original fix was a Layer 1 "co-fire guard": hold current_room
whenever a second tracked PIR is already on, on the theory that a
genuine transition clears the old room's PIR first. That theory is
false. Measured 2026-09-05: the LR Hue PIR latches ~10 s after last
motion while an LR -> hallway -> bathroom walk takes 4-6 s, so the old
room's PIR is ALWAYS still on when you reach the new room. The guard
suppressed every real transit – see
`test_room_transitions.test_transit_lights_new_room_with_old_pir_latched`.

The guard is gone. The harm it was aimed at is prevented downstream
instead, by R1b's presence-confirm gate: R1b refuses to darken other
rooms while current_room's own PIR is dead, which is exactly the
cross-fire signature (see `test_cofire_blip_after_lr_settle`).

These tests therefore assert the INCIDENT OUTCOME – the living room must
not go dark on a seated user – and deliberately say nothing about how
current_room behaves along the way. The versions of these tests written
on 2026-06-17 pinned the mechanism (`current_room == 'living_room'`), so
they kept passing while the real-world behaviour regressed underneath
them. Assert the harm, not the implementation that happens to avert it.
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_cofire_blip_does_not_darken_the_living_room(presence_hass):
    """The 00:21 harm itself: a seated user must not be plunged into dark."""
    hass = presence_hass
    await set_grace(hass, 45)

    # Established and seated in the LR; the PIR is still reporting motion.
    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"

    # Spurious hallway + bathroom detections co-fire while the LR PIR is
    # still on. current_room may well follow the blip – not under test.
    await motion(hass, "hallway", on=True)
    await motion(hass, "bathroom", on=True)

    # The blip clears; the user stays put and stops producing motion edges.
    await motion(hass, "bathroom", on=False)
    await motion(hass, "hallway", on=False)
    await motion(hass, "living_room", on=False)

    # Past the grace window. Whatever current_room says, the bathroom PIR
    # is dead, so R1b must not treat the bathroom as occupied and darken
    # the room the user is actually sitting in.
    await advance(hass, seconds=50)
    assert light(hass, "living_room") == "on"


async def test_wrongly_claimed_room_self_heals_on_next_real_motion(presence_hass):
    """A cross-fire may briefly light the wrong room; it must not orphan it.

    The 2026-09-05 orphan was permanent precisely because the guard stopped
    current_room from ever claiming the bathroom – so it never changed
    back, R1b never armed, and the lamp burned until switched off by hand.
    """
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"

    # Cross-fire blip lights the bathroom while the user sits in the LR.
    await motion(hass, "bathroom", on=True)
    assert light(hass, "bathroom_light") == "on"
    await motion(hass, "bathroom", on=False)

    # The user shifts on the sofa: a real LR edge reclaims current_room.
    await motion(hass, "living_room", on=False)
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"

    # R1b now has a current_room change to act on, and the LR is exempt
    # from presence-confirm, so the stray bathroom lamp is cleaned up
    # within the normal grace window – no extra timer, no hand-holding.
    await advance(hass, seconds=50)
    assert light(hass, "bathroom_light") == "off"
    assert light(hass, "living_room") == "on"
