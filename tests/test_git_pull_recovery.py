"""`git_pull_restart_after_crash` restarts the Git pull add-on after a crash.

The add-on stops for good when a fetch fails during the nightly internet
reconnect. The automation starts it again after 10 minutes stopped, and
retries every 30 minutes while it stays stopped.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

PACKAGE = Path(__file__).resolve().parent.parent / "packages" / "git_pull_recovery.yaml"
RUNNING_SENSOR = "binary_sensor.git_pull_running"
BETWEEN_HALF_HOURS = datetime(2026, 1, 1, 12, 5, tzinfo=dt_util.UTC)


@pytest.fixture
async def recovery_hass(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> tuple[HomeAssistant, list[ServiceCall]]:
    freezer.move_to(BETWEEN_HALF_HOURS)
    starts: list[ServiceCall] = []

    async def _addon_start(call: ServiceCall) -> None:
        starts.append(call)

    hass.services.async_register("hassio", "addon_start", _addon_start)
    hass.states.async_set(RUNNING_SENSOR, "on")

    package = yaml.safe_load(PACKAGE.read_text())
    assert await async_setup_component(hass, "automation", {"automation": package["automation"]})
    await hass.async_block_till_done()
    return hass, starts


async def _wait(hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _set_running(hass: HomeAssistant, running: bool) -> None:
    hass.states.async_set(RUNNING_SENSOR, "on" if running else "off")
    await hass.async_block_till_done()


async def test_starts_the_add_on_after_ten_minutes_stopped(recovery_hass, freezer):
    hass, starts = recovery_hass

    await _set_running(hass, False)
    await _wait(hass, freezer, timedelta(minutes=9))
    assert starts == []

    await _wait(hass, freezer, timedelta(minutes=1, seconds=1))
    assert [call.data["addon"] for call in starts] == ["core_git_pull"]


async def test_does_nothing_when_the_add_on_comes_back_on_its_own(recovery_hass, freezer):
    hass, starts = recovery_hass

    await _set_running(hass, False)
    await _wait(hass, freezer, timedelta(minutes=2))
    await _set_running(hass, True)
    await _wait(hass, freezer, timedelta(minutes=10))

    assert starts == []


async def test_retries_on_the_half_hour_while_still_stopped(recovery_hass, freezer):
    hass, starts = recovery_hass

    await _set_running(hass, False)
    await _wait(hass, freezer, timedelta(minutes=11))
    assert len(starts) == 1

    await _wait(hass, freezer, timedelta(minutes=15))
    assert len(starts) == 2


async def test_half_hour_check_leaves_a_running_add_on_alone(recovery_hass, freezer):
    hass, starts = recovery_hass

    await _wait(hass, freezer, timedelta(minutes=30))

    assert starts == []
