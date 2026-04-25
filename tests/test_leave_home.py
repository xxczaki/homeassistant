"""Scenario R5 — leave_home_lights_off.

Two trigger paths, OR-conditioned:
  1. person.antek transitions to 'not_home' for 2 minutes (primary).
  2. all motion sensors off for 10 minutes AND person.antek != 'home'
     (fallback for when the tracker mis-reports).

On either path: every tracked light off, current_room → none, all
suppress flags cleared.
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
    """The fallback path: tracker is wrong/stuck, but motion has been
    silent for 10 min and person isn't 'home' — clean up."""
    hass = presence_hass

    # Light up LR, then mark person as away
    await motion(hass, "living_room", on=True)
    await motion(hass, "living_room", on=False)
    assert light(hass, "living_room") == "on"

    hass.states.async_set("person.antek", "not_home")
    await hass.async_block_till_done()

    # Don't advance enough to trigger the primary 2-min path? Actually
    # the primary path fires first (after 120 s). To exercise ONLY the
    # no-motion fallback we'd need person to be in some not-'home',
    # not-'not_home' value (e.g. 'unknown'). Set it to 'unknown' so
    # primary trigger ('to: not_home') doesn't fire.
    hass.states.async_set("person.antek", "unknown")
    await hass.async_block_till_done()

    # Wait 10 min + slack for the no-motion template trigger.
    # Real-time runtime of this advance is not great because HA processes
    # every internal periodic task in the window — acceptable for a
    # single regression test of the fallback path.
    await advance(hass, seconds=10 * 60 + 10)

    # All lights off via the fallback path
    assert light(hass, "living_room") == "off"
    assert current_room(hass) == "none"


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
