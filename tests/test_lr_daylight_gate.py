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
    light,
    motion,
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
