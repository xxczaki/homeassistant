"""Regression: tonight's bug (2026-04-25).

Previously, every motion-on event in any tracked room restarted Layer 1's
grace timer. Living-room PIR has pirOToUDelay=5s, so sitting in LR
produces an off→on transition every few seconds and the cleanup of
*other* rooms (bathroom, laundry that were on from earlier visits) never
got to run.

Layer 1b now triggers on `input_select.current_room` state CHANGE – not
on motion – and `input_select.select_option` to the same value is a
no-op in HA, so motion oscillation within the same room can no longer
restart the timer. Only entering a *different* room does.
"""

from .helpers import advance, current_room, light, motion, set_grace


async def test_lr_motion_burst_does_not_keep_other_rooms_lit(presence_hass):
    hass = presence_hass
    await set_grace(hass, 45)

    # Earlier visits leave bathroom and laundry on
    await motion(hass, "bathroom", on=True)
    await motion(hass, "bathroom", on=False)
    await motion(hass, "laundry_room", on=True)
    await motion(hass, "laundry_room", on=False)
    assert light(hass, "bathroom_light") == "on"
    assert light(hass, "laundry_room_light") == "on"

    # User now settles in LR
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"

    # Simulate 100 s of sitting in LR with the PIR cycling every 5 s
    for _ in range(20):
        await advance(hass, seconds=5)
        await motion(hass, "living_room", on=False)
        await motion(hass, "living_room", on=True)

    # Layer 1b should have fired after ~45 s of stable current_room=living_room
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"
    assert light(hass, "bathroom_light") == "off"
    assert light(hass, "laundry_room_light") == "off"
