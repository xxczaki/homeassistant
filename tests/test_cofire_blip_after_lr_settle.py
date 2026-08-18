"""Regression: the 2026-06-2x "LR turned off on me" production incidents.

Reconstructed from the recorder DB (two near-identical occurrences,
2026-06-26 00:49 and 2026-06-28 01:27):

  user settled in the LR; LR PIR reads 'off' (sitting still – the LR
        blind spot, see test_blind_spot)
  a transient 15-20 s bathroom/laundry PIR blip fires (sensor cross-fire)
        while the LR PIR is in an off-window -> Layer 1 commits
        current_room=bathroom (the co-fire guard only blocks the
        *simultaneous* case; a lone blip slips through)
  ~5 s later the LR PIR fires again (the user IS there) but the blip is
        still on, so the co-fire guard suppresses the self-heal
  the blip clears; the LR PIR then stays quiet
  +180 s: R1b turns light.living_room OFF on a user who never left.

The room R1b turned off (LR) had its PIR 'off' at fire time, so a guard
on the *target* room can't catch this. The reliable signal is the other
side: current_room=bathroom but the bathroom PIR is dead – nobody is
actually in the room R1b is keeping. R1b must confirm presence in
current_room (its PIR live, or it's the LR) before darkening the rest.
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_transient_blip_after_lr_settle_does_not_kill_lr(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    # Settled in the LR; light on.
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"

    # LR PIR drops to off – the user is sitting still (blind spot), not gone.
    await motion(hass, "living_room", on=False)

    # A lone transient bathroom blip fires during the LR off-window. With no
    # other tracked PIR co-firing, Layer 1 commits current_room=bathroom.
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"

    # The blip clears almost immediately – nobody is actually in the bathroom.
    await motion(hass, "bathroom", on=False)

    # Grace elapses with no live motion anywhere. current_room still points at
    # the bathroom, but its PIR is dead -> presence unconfirmed -> R1b must
    # NOT clean up the LR. Pre-fix this asserted 'off'.
    await advance(hass, seconds=50)
    assert light(hass, "living_room") == "on"


async def test_blip_does_not_kill_lr_even_when_lr_pir_never_refires(presence_hass):
    """The motionless variant: after the spurious flip the LR PIR stays off
    for the whole grace window (deep stillness). R1b still must not darken the
    LR, because current_room=bathroom is unconfirmed (bathroom PIR off)."""
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    await motion(hass, "living_room", on=False)
    assert light(hass, "living_room") == "on"

    await motion(hass, "bathroom", on=True)
    await motion(hass, "bathroom", on=False)
    assert current_room(hass) == "bathroom"

    # No motion at all for well past grace.
    await advance(hass, seconds=120)
    assert light(hass, "living_room") == "on"


async def test_confirmed_bathroom_stay_still_cleans_up_lr(presence_hass):
    """The guard must not over-protect: a *genuine* bathroom stay (bathroom
    PIR live at fire time) still cleans up the LR as before."""
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"

    # Genuine departure: LR clears, bathroom PIR comes on and STAYS on (the
    # user is in there) – current_room commits to bathroom.
    await motion(hass, "living_room", on=False)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"

    # Past grace with the bathroom PIR still live -> presence confirmed ->
    # the empty LR is cleaned up.
    await advance(hass, seconds=60)
    assert light(hass, "bathroom_light") == "on"
    assert light(hass, "living_room") == "off"


async def test_occupied_target_room_is_not_darkened(presence_hass):
    """A room still reporting motion is never turned off, even if it isn't
    current_room. (current_room=LR is confirmed; the bathroom light is on and
    its PIR is live -> R1b leaves it alone.)"""
    hass = presence_hass
    await set_grace(hass, 45)

    # Settle in the LR; the LR PIR stays on. A bathroom PIR then co-fires
    # while the LR PIR is still live: the Layer 1 co-fire guard HOLDS
    # current_room at living_room, but Layer 1 still turns the bathroom light
    # on. Net: current_room=LR, bathroom light on, bathroom PIR live.
    await motion(hass, "living_room", on=True)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "bathroom_light") == "on"

    # Grace passes while the bathroom PIR stays on. current_room=LR is
    # confirmed, so cleanup runs – but the bathroom is occupied, so its light
    # must survive.
    await advance(hass, seconds=60)
    assert light(hass, "bathroom_light") == "on"
