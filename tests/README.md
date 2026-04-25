# Presence-automation test suite

In-process pytest suite that loads the **real** `automations.yaml` and `packages/presence.yaml` into a Home Assistant test instance, drives fake state changes through HA's actual automation engine, advances virtual time without real sleeps, and asserts the resulting entity states.

The tests are the executable form of the scenario matrix in [`docs/presence-model.md`](../docs/presence-model.md). One test per row.

## Why this works

`pytest-homeassistant-custom-component` (used by the HA Core team for their own tests) gives us:

- a `hass` fixture: a fresh, in-process Home Assistant instance per test,
- `async_setup_component` to load any HA YAML domain (automation, input_select, …),
- `hass.states.async_set` to inject sensor states,
- `async_fire_time_changed` to advance the scheduler clock,
- `await hass.async_block_till_done()` to flush the event loop deterministically.

That's HA's *actual production engine* — `mode: restart`, `for:`-with-template state triggers, Jinja, `repeat`/`for_each`, `input_select.select_option` no-op semantics — running our YAML. No interpreter to maintain.

## Running

Toolchain handled by [`mise`](https://mise.jdx.dev/) (declared in repo-root `mise.toml`) and [`uv`](https://docs.astral.sh/uv/).

```sh
cd tests
uv sync                 # install the dev group into a virtualenv
uv run pytest           # run the suite
uv run pytest -k motion # run a single test by keyword
```

`mise` will install Python 3.13 and uv on first entry into the repo if they aren't already present.

## Layout

```
tests/
├─ pyproject.toml          # uv dependency config
├─ conftest.py             # fixtures: presence_hass, mocked light services
├─ helpers.py              # tiny DSL: motion(), advance(), current_room(), …
├─ test_arrive_home.py     # row 1 of the scenario matrix
├─ test_room_transitions.py# rows 4, 5 (LR ↔ bathroom)
└─ test_motion_burst.py    # tonight's regression (LR PIR oscillation)
```

## What's mocked / stubbed

- **Light services** (`light.turn_on` / `light.turn_off`) — registered as in-test handlers that mutate `hass.states` so template conditions like `is_state(light.living_room, 'on')` evaluate correctly.
- **Light entities themselves** — created via `hass.states.async_set` rather than registered through a real platform. Sufficient because the presence model only reads/writes their `state`, not their attributes.
- **Motion sensors** — same: pure state entities under `binary_sensor.<room>_motion_occupancy`.

## What's *not* mocked

- The automations themselves — loaded from `automations.yaml` verbatim.
- The presence package (`input_boolean`, `input_number`, `input_select`) — loaded from `packages/presence.yaml` verbatim.
- The trigger / template / mode semantics — provided by HA core (`pytest-homeassistant-custom-component` bundles a real HA core).

## Adding a new test

1. Add the scenario to the matrix in `docs/presence-model.md` if it isn't there.
2. Create a test that drives the events and asserts the expected end state. Use the helpers in `helpers.py` so the scenario reads like the matrix row.
3. Reference the matrix row in the test's docstring so the doc and the suite stay paired.
