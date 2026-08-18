"""Scenario R5 – leave_home_lights_off.

Two trigger paths, OR-conditioned:
  1. person.antek transitions to 'not_home' for 2 minutes (primary).
  2. all motion sensors off for 10 minutes AND person.antek is
     affirmatively 'not_home' (fallback for missed motion, NOT for a
     broken tracker – see the 2026-08-18 regression below).

On either path: every tracked light off, current_room → none.
"""

from .helpers import advance, current_room, light, motion


async def test_person_not_home_for_two_min_turns_everything_off(presence_hass):
    hass = presence_hass

    # In LR, lights on, current_room=living_room
    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"
    assert current_room(hass) == "living_room"

    # Person leaves
    hass.states.async_set("person.antek", "not_home")
    await hass.async_block_till_done()

    # Wait the 2-minute trigger duration plus a few seconds of slack
    await advance(hass, seconds=125)

    assert current_room(hass) == "none"
    for room in ("living_room", "bathroom_light", "laundry_room_light", "hallway_light"):
        assert light(hass, room) == "off", f"{room} should be off after leave-home"


async def test_no_motion_for_ten_min_with_person_away_turns_off(presence_hass):
    """The fallback path: person is affirmatively not_home, a light was
    left on (or re-lit) after the primary already ran, and motion has
    been silent for 10 min – clean up.

    To isolate the fallback, let the primary path fire first on an
    empty home (no-op), then re-light the LR: the primary won't re-fire
    without a fresh transition to not_home, so the later turn-off can
    only come from the no-motion fallback."""
    hass = presence_hass

    # Person leaves; primary fires after 2 min on an already-dark home.
    hass.states.async_set("person.antek", "not_home")
    await hass.async_block_till_done()
    await advance(hass, seconds=125)

    # A light comes back on while person is still not_home (guest,
    # missed arrival, cat on the sensor) and motion goes silent again.
    await motion(hass, "living_room", on=True)
    await motion(hass, "living_room", on=False)
    assert light(hass, "living_room") == "on"
    # Let the all_rooms_motion group sensor process the on->off cycle so
    # the fallback's 10-min `for:` timer is armed BEFORE the time jump.
    await hass.async_block_till_done()

    # Wait 10 min + slack for the no-motion fallback.
    await advance(hass, seconds=10 * 60 + 10)

    # All lights off via the fallback path
    assert light(hass, "living_room") == "off"
    assert current_room(hass) == "none"


async def test_person_unknown_never_fires_fallback(presence_hass):
    """Regression: the 2026-08-18 'lights keep dying on me' incident.

    UniFi re-created the phone's device_tracker entity on private-MAC
    rotation until person.antek lost every tracker link and stuck at
    'unknown'. The fallback condition was not(state == 'home'), which
    treats 'unknown' as away – so each 10-min still-sitting window (LR
    PIR blind spot) fired leave-home: 23 all-lights-off events in one
    day with the user on the sofa.

    'unknown' means no data. Only an affirmative 'not_home' may darken
    the house."""
    hass = presence_hass

    # Settled in the LR, tracker gives no data.
    await motion(hass, "living_room", on=True)
    await motion(hass, "living_room", on=False)
    assert light(hass, "living_room") == "on"

    hass.states.async_set("person.antek", "unknown")
    await hass.async_block_till_done()

    # Well past the 10-min no-motion window: nothing may turn off.
    await advance(hass, seconds=10 * 60 + 30)

    assert light(hass, "living_room") == "on"
    assert current_room(hass) == "living_room"


async def test_returning_after_leave_lights_room_on_via_motion(presence_hass):
    hass = presence_hass

    # Leave home flow
    await motion(hass, "living_room", on=True)
    hass.states.async_set("person.antek", "not_home")
    await hass.async_block_till_done()
    await advance(hass, seconds=125)
    assert light(hass, "living_room") == "off"

    # Return home: tracker flips back. Drop motion sensors first so the
    # next motion-on triggers Layer 1 (HA's state trigger needs an actual
    # off→on transition; motion was left 'on' from before leave-home).
    hass.states.async_set("person.antek", "home")
    await motion(hass, "living_room", on=False)
    await motion(hass, "hallway", on=False)
    await hass.async_block_till_done()

    await motion(hass, "hallway", on=True)
    await motion(hass, "living_room", on=True)

    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"
