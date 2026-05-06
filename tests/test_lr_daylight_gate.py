"""LR-only daylight gate on the room_light_on_and_track automation.

Regression: 2026-04-26 – LR lights came on at ~196 lx because the
`light_on_lux_threshold` slider existed but no automation read it.
The fix gates only the living_room branch on
`sensor.living_room_motion_illuminance < input_number.light_on_lux_threshold`,
so:
  - LR motion below threshold still turns the lamp on (normal night flow).
  - LR motion at-or-above threshold leaves the lamp off (bright daylight).
  - Bathroom and laundry are unaffected – they have no usable daylight.
  - Sensor `unknown`/`unavailable` falls back to 0 lx so a flaky PIR
    can never trap the room in the dark.
"""

from .helpers import (
    advance,
    current_room,
    light,
    motion,
    set_grace,
    set_lr_illuminance,
    set_lux_threshold,
)


async def test_lr_motion_below_threshold_turns_lamp_on(presence_hass):
    hass = presence_hass
    await set_lux_threshold(hass, 50)
    await set_lr_illuminance(hass, 10)

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"


async def test_lr_motion_at_threshold_blocks_lamp(presence_hass):
    hass = presence_hass
    await set_lux_threshold(hass, 50)
    await set_lr_illuminance(hass, 50)

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "off"


async def test_lr_motion_above_threshold_blocks_lamp(presence_hass):
    hass = presence_hass
    await set_lux_threshold(hass, 50)
    await set_lr_illuminance(hass, 196)

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "off"


async def test_bathroom_unaffected_by_lr_brightness(presence_hass):
    hass = presence_hass
    await set_lux_threshold(hass, 50)
    await set_lr_illuminance(hass, 250)

    await motion(hass, "bathroom", on=True)
    assert light(hass, "bathroom_light") == "on"


async def test_laundry_unaffected_by_lr_brightness(presence_hass):
    hass = presence_hass
    await set_lux_threshold(hass, 50)
    await set_lr_illuminance(hass, 250)

    await motion(hass, "laundry_room", on=True)
    assert light(hass, "laundry_room_light") == "on"


async def test_unavailable_sensor_falls_back_to_dark(presence_hass):
    hass = presence_hass
    await set_lux_threshold(hass, 50)
    hass.states.async_set("sensor.living_room_motion_illuminance", "unavailable")

    await motion(hass, "living_room", on=True)
    assert light(hass, "living_room") == "on"


async def test_gated_lr_motion_still_updates_current_room(presence_hass):
    """Regression: 2026-04-29 production incident.

    The user's LR PIR reads its own lamp's spill (lux jumps from ~2 to
    ~30 once the lamp is on) and the threshold slider sits at 5. Once
    the lamp is on, every subsequent LR motion fails the daylight gate.

    The original automation gated the WHOLE Layer 1 step on lux, so a
    gated LR motion didn't update current_room either. After a
    bath-then-back-to-LR round trip the user was physically in the LR
    but current_room was still 'bathroom' – Layer 1b's grace timer
    expired and cleanup turned off the LR light on a user sitting under
    it. Repeated twice in one evening before the user complained.

    The gate must only suppress the lamp, never room tracking.
    """
    hass = presence_hass
    await set_grace(hass, 45)
    await set_lux_threshold(hass, 5)

    # Dark LR – first motion lights it
    await set_lr_illuminance(hass, 2)
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"

    # Lamp's own light bumps the PIR's illuminance above threshold
    await set_lr_illuminance(hass, 30)

    # Step out to the bathroom
    await motion(hass, "living_room", on=False)
    await motion(hass, "bathroom", on=True)
    assert current_room(hass) == "bathroom"

    # Walk back into LR. The gate blocks the lamp (it's already on, lux
    # high) – but room tracking MUST still flip back, otherwise Layer 1b
    # will turn the LR off in `set_grace` seconds.
    await motion(hass, "bathroom", on=False)
    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"

    # Past the grace window: Layer 1b should target the bathroom (the
    # non-current room), not the room the user is sitting in.
    await advance(hass, seconds=60)
    assert light(hass, "living_room") == "on"
    assert light(hass, "bathroom_light") == "off"
