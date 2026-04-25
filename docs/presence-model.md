# Presence-based lighting – formal model

## Assumptions

1. **Single occupant.** Exactly one person in the studio at any time. If hallway motion fires while no tracked room shows motion, that person is in the hallway – they cannot also be in the living room.
2. **Hallway is the transit hub.** Every move between tracked rooms passes through the hallway.
3. **Studio layout.** The living room is open-plan and contains the kitchenette and bedroom nook. They share a single PIR (`binary_sensor.living_room_motion_occupancy`) and a single tracked room (`living_room`).

## Tracked rooms

- **Tracked** (have motion sensors, participate in `input_select.current_room`): `living_room`, `bathroom`, `laundry_room`.
- **Transit zone** (has motion sensor, does NOT set current_room): `hallway`.
- **Sub-areas of the living room** (no own PIR): kitchenette, bedroom nook. Lit by `light.kitchenette_light` (kitchenette ceiling) and `light.bedroom_light` (nook); both are members of the `light.living_room` group.

## Master kill switch

`input_boolean.presence_enabled` (default ON). Every presence automation has it as a `condition:` – when off, motion does nothing, hallway light doesn't react, no Layer 1b cleanup, no R2 dwell, no R5 leave-home. Manual control via the Hue dimmer / app continues to work because the automations only block their _own_ effects, never the user's.

Use case: guests over, hosting, anything where the model would mis-interpret traffic patterns.

## State model

| Entity                                | Purpose                                                                                                |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `input_select.current_room`           | The tracked room the user is currently in. Options: `none`, `living_room`, `bathroom`, `laundry_room`. |
| `input_boolean.presence_enabled`      | Master kill switch (above).                                                                            |
| `input_number.presence_grace_seconds` | Layer 1b grace period (seconds).                                                                       |

## Turn-on rule

A room's light turns on when **its** motion sensor fires `on`, AND `presence_enabled` is `on`. Automation: `room_light_on_and_track` (Layer 1).

## Turn-off rules

A room's light turns off when **any** of the following happens (and `presence_enabled` is `on`):

### R1 – Room transition (Layer 1 trigger half)

A different room's motion fires → `current_room` flips → Layer 1b's grace timer arms with the new value.

### R1b – Cleanup after settle (Layer 1b)

**Trigger**: `input_select.current_room` has been a tracked room (LR / bathroom / laundry) continuously for `presence_grace_seconds`.

**Action**: turn off every other tracked room's light. Reads `current_room` _live_ in the action body so it always cleans the right rooms even when state has moved between tracked values during the wait.

### R2 – Hallway dwell

**Trigger**: hallway motion `on` AND every tracked-room motion `off` continuously for 90 s.

**Action**: turn off whatever `current_room` points to; reset to `none`.

### R3 – (removed)

Intentionally absent. Pure presence: a room's light stays on as long as it's the `current_room`. Sitting still (toilet use, reading on the bed, folding laundry) is not grounds for turning off the light.

### R4 – Hallway light follower

`hallway_light_on` mirrors hallway PIR `on`. `hallway_light_off` fires after hallway motion has been continuously `off` for 60 s – any motion within the window resets the timer, so dwelling keeps the light lit.

### R5 – Leave home

`person.antek → not_home` for 2 min, OR all motion `off` for 10 min while not home → all tracked lights off, `current_room=none`.

## Scenario matrix

| #   | You do…                                                      | Expected outcome                                                                                                                                     | Which rule                                                    |
| --- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| 1   | Come home: front door → hallway → LR                         | Hallway light on, then LR light on; `current_room=living_room`; hallway off 60 s after you settle in LR                                              | R4                                                            |
| 2   | Sit on the bed in LR, still for 3 hours                      | LR stays on; `current_room` stays `living_room`; nothing else fires                                                                                  | No rule fires                                                 |
| 3   | LR → hallway (grab mail) → LR, total 20 s                    | LR stays on throughout; `current_room` stays `living_room`                                                                                           | No rule fires                                                 |
| 4   | LR → bathroom → LR, total 30 s (quick use)                   | Bathroom on during visit; LR stays on                                                                                                                | R1 (timer re-arms on return; cleanup targets bathroom not LR) |
| 5   | LR → bathroom, stay 30 min (toilet, reading)                 | LR off after grace; **bathroom stays on the entire 30 min regardless of motion stillness**                                                           | R1b only                                                      |
| 6   | LR → laundry → hang in hallway 3 min → LR                    | LR off after grace once `current_room=laundry`; R2 fires after 90 s of hallway-only → laundry off, `current_room=none`; LR back on when you re-enter | R1b, R2                                                       |
| 7   | LR → hallway only, dwell 2 min, return to LR                 | LR off ~90 s into hallway dwell; `current_room=none`; on return, LR motion fires and LR comes back on, `current_room=living_room`                    | R2                                                            |
| 8   | LR motion sensor blips off for 0.2 s while user on couch     | LR stays on (no rule samples motion-off under the model)                                                                                             | No rule fires                                                 |
| 9   | Cat walks through hallway briefly (< 90 s) while user on bed | LR stays on (R2 threshold not met)                                                                                                                   | No rule fires                                                 |
| 10  | Cat hangs out in hallway > 90 s while user on bed            | LR would turn off (false positive). Known edge case under single-person assumption violation.                                                        | R2 false positive                                             |
| 11  | Hanging laundry, back-and-forth between laundry and hallway  | Laundry stays on; hallway light stays on as long as motion within 60 s; LR off after grace from laundry-entry                                        | R4, R1b                                                       |
| 12  | Friends over, presence disabled                              | Nothing presence-related fires; lights are entirely under manual control                                                                             | Kill switch                                                   |

## Tuning knobs

| Knob                                                | File                                          | Default                           | Tradeoff                                                                                                                                                                      |
| --------------------------------------------------- | --------------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `presence_grace_seconds`                            | `packages/presence.yaml`                      | 180 s                             | Higher = brief trips don't kill the previous room; lower = snappier cleanup                                                                                                   |
| Hallway dwell threshold                             | `automations.yaml` R2 trigger `for:`          | 90 s                              | Higher = less likely to trip on long transits; lower = faster LR-off when hallway dwelling                                                                                    |
| Hallway light off threshold                         | `automations.yaml` `hallway_light_off` `for:` | 60 s                              | Higher = stays on longer between motion bursts; lower = darker hallway between events                                                                                         |
| Hue sensor `occupancy_timeout` (per device, in Z2M) | Z2M per-device config                         | LR 5 / BR 15 / HW 30 / Laundry 60 | Lower = sensor reports off faster after you stop moving; under the pure-presence model this only affects when R1/R2 can re-trigger on re-entry – no longer gates any turnoff. |

## Live verification

The **Presence** dashboard view shows: master kill switch, `current_room`, sensor + light state per room, 24 h occupancy history graph, and live countdowns for R1b, R2 and R5.

## Test suite

Every row of the matrix has a corresponding pytest scenario in `tests/`. The suite drives an in-process Home Assistant instance against the production YAML; it runs in well under a second locally and on every push / PR via `.github/workflows/tests.yml`. Make a YAML change, see the matching test go red – that's how you know what you broke.
