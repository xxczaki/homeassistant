"""Scenario row 1: Arrive home → front door → hallway → LR.

Expected: hallway light on (R: hallway_light_on), LR motion sets
current_room=living_room, LR light on. Bathroom and laundry remain off.
"""

from .helpers import current_room, light, motion


async def test_arrive_home_through_hallway_to_lr(presence_hass):
    hass = presence_hass

    await motion(hass, "hallway", on=True)
    assert light(hass, "hallway_light") == "on"

    await motion(hass, "living_room", on=True)
    assert current_room(hass) == "living_room"
    assert light(hass, "living_room") == "on"

    # Other rooms untouched
    assert light(hass, "bathroom_light") == "off"
    assert light(hass, "laundry_room_light") == "off"
