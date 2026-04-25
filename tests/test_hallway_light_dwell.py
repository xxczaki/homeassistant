"""Regression for the 2026-04-25 22:06 bug.

User was hanging laundry — moving between the laundry room and the
hallway. Hallway PIR oscillated as they moved. The hallway light
turned off mid-dwell because the previous `hallway_light_off` rule was
"after total on-time exceeds min_on, any motion-off → off" — so once
the light had been on past `grace_seconds`, a single PIR drop would
kill it even though the user was still right there.

The current rule is "motion off continuously for 60 s → off". Any
motion-on resets the 60 s timer, so the light stays lit while the user
is around.
"""

from .helpers import advance, light, motion


async def test_hallway_motion_oscillation_keeps_light_on(presence_hass):
    hass = presence_hass

    # Hallway light comes on
    await motion(hass, "hallway", on=True)
    assert light(hass, "hallway_light") == "on"

    # Simulate dwelling: motion cycles off→on every ~30 s for 5 minutes.
    # Each motion-on resets the 60 s timer.
    for _ in range(10):
        await advance(hass, seconds=30)
        await motion(hass, "hallway", on=False)
        await advance(hass, seconds=20)
        await motion(hass, "hallway", on=True)

    # After 5 min of dwelling, hallway light still on
    assert light(hass, "hallway_light") == "on"


async def test_hallway_motion_off_for_60s_turns_off(presence_hass):
    hass = presence_hass

    await motion(hass, "hallway", on=True)
    assert light(hass, "hallway_light") == "on"

    # User leaves; 65 s of silence
    await motion(hass, "hallway", on=False)
    await advance(hass, seconds=65)

    assert light(hass, "hallway_light") == "off"


async def test_brief_motion_off_within_60s_does_not_kill_light(presence_hass):
    hass = presence_hass

    await motion(hass, "hallway", on=True)

    # Motion off briefly, then on again — within the 60 s window
    await motion(hass, "hallway", on=False)
    await advance(hass, seconds=30)
    await motion(hass, "hallway", on=True)

    # Still well within timer; light stays on
    await advance(hass, seconds=10)
    assert light(hass, "hallway_light") == "on"
