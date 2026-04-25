"""Pytest fixtures for the presence-automation suite.

The `presence_hass` fixture spins up a fresh in-process HA, loads the
production YAML (`packages/presence.yaml` + the presence-related entries
of `automations.yaml`), seeds motion sensors and lights to `off`, and
registers in-test light services that mutate `hass.states` so template
conditions in the automations evaluate against real state.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component

from .helpers import reset_clock

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTOMATIONS_YAML = REPO_ROOT / "automations.yaml"
PRESENCE_PACKAGE = REPO_ROOT / "packages" / "presence.yaml"

# IDs of the automations that constitute the presence model. Other
# automations in `automations.yaml` (vacuum notifications, kitchen switch,
# push_config_on_shutdown, etc.) are intentionally excluded — their
# dependencies (real Zigbee devices, MQTT, shell commands) aren't worth
# stubbing for the presence tests.
PRESENCE_AUTOMATION_IDS = {
    "room_light_on_and_track",
    "room_cleanup_after_settle",
    "hallway_dwell_turnoff",
    "manual_light_override",
    "leave_home_lights_off",
    "hallway_light_on",
    "hallway_light_off",
}

LIGHTS = (
    "light.living_room",
    "light.bathroom_light",
    "light.laundry_room_light",
    "light.hallway_light",
)

MOTION_SENSORS = (
    "binary_sensor.living_room_motion_occupancy",
    "binary_sensor.bathroom_motion_occupancy",
    "binary_sensor.laundry_room_motion_occupancy",
    "binary_sensor.hallway_motion_occupancy",
)


def _load_presence_package() -> dict:
    return yaml.safe_load(PRESENCE_PACKAGE.read_text())


def _load_presence_automations() -> list[dict]:
    raw = yaml.safe_load(AUTOMATIONS_YAML.read_text())
    return [a for a in raw if a.get("id") in PRESENCE_AUTOMATION_IDS]


def _entity_ids(call: ServiceCall) -> list[str]:
    """Pull entity IDs out of a ServiceCall regardless of where they sit.

    HA automations may pass entity_id via `target:` (modern) or `data:`
    (legacy / direct service calls). Cover both.
    """
    ids: list[str] = []
    target = getattr(call, "target", None) or {}
    target_eid = target.get("entity_id") if target else None
    if target_eid:
        ids.extend([target_eid] if isinstance(target_eid, str) else list(target_eid))
    data_eid = call.data.get("entity_id")
    if data_eid:
        ids.extend([data_eid] if isinstance(data_eid, str) else list(data_eid))
    return ids


@pytest.fixture
async def presence_hass(hass: HomeAssistant) -> HomeAssistant:
    """A hass instance with the production presence YAML loaded.

    Light services are mocked so that turn_on/turn_off mutate state — the
    Layer 1b cleanup template needs to read `is_state(light, 'on')` to
    decide whether to skip a turnoff, so a service that only records calls
    isn't enough.
    """
    package = _load_presence_package()

    # Helper domains first — automations reference these in conditions/templates.
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": package["input_boolean"]}
    )
    assert await async_setup_component(
        hass, "input_number", {"input_number": package["input_number"]}
    )
    assert await async_setup_component(
        hass, "input_select", {"input_select": package["input_select"]}
    )
    await hass.async_block_till_done()

    # Seed sensors + lights to a known idle state BEFORE loading automations,
    # so initial-state-restoration doesn't fire spurious triggers.
    for sensor in MOTION_SENSORS:
        hass.states.async_set(sensor, "off")
    for light in LIGHTS:
        hass.states.async_set(light, "off")

    # In-test light services. Mutate state on call so subsequent template
    # reads (`is_state(light.X, 'on')`) reflect what the automation just did.
    async def _light_turn_on(call: ServiceCall) -> None:
        for eid in _entity_ids(call):
            hass.states.async_set(eid, "on")

    async def _light_turn_off(call: ServiceCall) -> None:
        for eid in _entity_ids(call):
            hass.states.async_set(eid, "off")

    hass.services.async_register("light", "turn_on", _light_turn_on)
    hass.services.async_register("light", "turn_off", _light_turn_off)

    # Now the automations. Order matters: their triggers reference the
    # entities + helpers we just set up.
    assert await async_setup_component(
        hass, "automation", {"automation": _load_presence_automations()}
    )
    await hass.async_block_till_done()

    reset_clock(hass)
    return hass
