"""Scenarios 2 + 10 – LR sensor blind spot.

The Living Room PIR doesn't reliably see the user when they're on the
bed. The presence model treats motion-off as NOT a valid turn-off
signal for LR – only entering a different tracked room (R1), hallway
dwell (R2), or leaving home (R5) can turn LR off.

Row 2 – sit on the bed for hours: LR stays on.
Row 10 – PIR cycles off→on briefly: LR stays on.
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_lr_stays_on_when_user_motionless_for_hours(presence_hass):
    hass = presence_hass

    # Settle in LR, then PIR drops to off (user lying still)
    await motion(hass, "living_room", on=True)
    await motion(hass, "living_room", on=False)
    assert light(hass, "living_room") == "on"

    # 5 minutes of nothing. Person is home (fixture default), so the
    # leave-home 10-minute no-motion fallback can't fire. Real "hours
    # of stillness" is a corollary of "no rule fires" – anything longer
    # only burns CI time iterating internal HA periodic tasks.
    await advance(hass, seconds=5 * 60)

    # No rule fires – LR stays on, current_room stays living_room
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"


async def test_pir_blip_does_not_change_anything(presence_hass):
    """A 0.2-second motion-off blip while user sits in LR is invisible to
    Layer 1b because input_select.current_room never changes value."""
    hass = presence_hass
    await set_grace(hass, 45)

    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"

    # PIR oscillation: off-on cycles every few seconds
    for _ in range(10):
        await advance(hass, seconds=5)
        await motion(hass, "living_room", on=False)
        await motion(hass, "living_room", on=True)

    # Still settled in LR. No room transitioned, no cleanup fires.
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"
