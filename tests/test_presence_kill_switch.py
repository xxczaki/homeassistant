"""`input_boolean.presence_enabled` is the master kill switch.

When OFF, every presence automation short-circuits via its `condition:
state input_boolean.presence_enabled = on`. Motion does nothing, no
hallway light, no current_room tracking, no Layer 1b cleanup, no R2
dwell, no R5 leave-home. Manual control still works because the
automations only block their *own* effects – the user can still flip
lights with the dimmer or app.
"""

from .helpers import advance, current_room, light, motion


async def _disable(hass) -> None:
    await hass.services.async_call(
        "input_boolean",
        "turn_off",
        {"entity_id": "input_boolean.presence_enabled"},
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_motion_does_not_turn_on_lights_when_disabled(presence_hass):
    hass = presence_hass
    await _disable(hass)

    await motion(hass, "living_room", on=True)
    await motion(hass, "hallway", on=True)
    await motion(hass, "bathroom", on=True)

    # Nothing fires; lights stay off; current_room not updated
    assert light(hass, "living_room") == "off"
    assert light(hass, "hallway_light") == "off"
    assert light(hass, "bathroom_light") == "off"
    assert current_room(hass) == "none"


async def test_layer_1b_cleanup_does_not_fire_when_disabled(presence_hass):
    """If user disables presence WHILE a cleanup is pending, the
    automation's condition blocks the action when the timer expires."""
    hass = presence_hass

    # Set up a pending cleanup: enter LR, then bathroom (current_room flips).
    await motion(hass, "living_room", on=True)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"
    assert light(hass, "living_room") == "on"

    # Now disable presence
    await _disable(hass)

    # Wait long past the grace period
    await advance(hass, seconds=200)

    # LR was NOT cleaned up because the condition blocked the action
    assert light(hass, "living_room") == "on"


async def test_leave_home_does_not_fire_when_disabled(presence_hass):
    """When presence is OFF, person.antek going not_home does not flush
    lights – the user explicitly disabled the system."""
    hass = presence_hass
    await motion(hass, "living_room", on=True)
    await _disable(hass)

    hass.states.async_set("person.antek", "not_home")
    await advance(hass, seconds=125)

    assert light(hass, "living_room") == "on"
