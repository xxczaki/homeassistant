# Presence-based lighting — formal model

## Assumptions

1. **Single occupant.** Exactly one person in the flat at any time. If hallway motion fires while no tracked room shows motion, that person is in the hallway — they cannot also be in the living room.
2. **Hallway is the transit hub.** Every move between tracked rooms passes through the hallway.
3. **The living-room PIR has a blind spot over the bed.** Being still in the living room produces `motion: off` even though the user is present. **"No motion" is never a valid turn-off signal for the living room.**

## Tracked rooms

- **Tracked** (have motion sensors, participate in `input_select.current_room`): `living_room`, `bathroom`, `laundry_room`.
- **Transit zone** (has motion sensor, does NOT set current_room): `hallway`.
- **Untracked** (no motion sensor): `kitchen`, `bedroom` nook (covered by `light.bedroom_light` in the LR group).

Note: `light.living_room` is a *light group* of `light.kitchen_light + light.bedroom_light` — both Hue bulbs, neither of which is the IKEA TRÅDFRI strip.

## State model

| Entity | Purpose |
|---|---|
| `input_select.current_room` | The tracked room the user is currently in. Options: `none`, `living_room`, `bathroom`, `laundry_room`. |
| `input_boolean.suppress_<room>_auto_light` | Per-room flag. When `on`, motion won't auto-turn-on the room's light. Set by `manual_light_override` when the user manually turns off a light; cleared when the light is turned on (by any path). |

## Turn-on rule (unchanged)

A room's light turns on when **its** motion sensor fires `on` AND **its** suppress flag is `off`. Automation: `room_light_on_and_track` (Layer 1), trigger half.

## Turn-off rules (refactored)

A room's light turns off when **any** of the following happens:

### R1 — Room transition (Layer 1)

**Trigger**: a tracked room's motion fires `on`.

**Action**: set `current_room` to that room; turn the room's light on; wait `presence_grace_seconds`; then for every tracked room ≠ the live `current_room`, turn its light off. **Unconditionally** — no longer gated on "motion is off in the other room." The single-occupant + hallway-transit assumptions mean current_room is authoritative: if you're in room X, you're not in rooms Y or Z.

Why the grace: lets a quick return re-commit `current_room` so the wrong room isn't turned off. If you step into the bathroom then back into LR within 30 s, by the time the bathroom's scheduled turnoff evaluates, `current_room` has already flipped back to `living_room` and bathroom will be the one turned off instead.

### R2 — Hallway dwell (new Layer 2)

**Trigger**: `binary_sensor.hallway_motion_occupancy` has been `on` continuously for 60 s.

**Action**: turn off whatever `current_room` points to; reset `current_room` to `none`.

Rationale: continuous hallway motion for 60 s means the user is *in* the hallway (hanging laundry, putting on shoes, etc.). Under the single-person assumption, they cannot simultaneously be in any tracked room. The 60 s threshold filters out normal transit (walking through in a few seconds) and phantom blips.

This replaces the old `hallway_quick_room_turnoff` (which fired on any 30 s of hallway motion and was responsible for the 22:15:19 bug on 2026‑04‑22).

### R3 — Room timeout (Layer 3, bathroom / laundry only)

**Trigger**: bathroom or laundry motion has been `off` for `room_light_timeout_minutes`.

**Action**: turn off that room's light; if it was `current_room`, set `current_room` to `none`.

**Never applies to the living room** (blind spot).

### R4 — Manual

User presses a physical switch / UI toggle / voice command. `manual_light_override` captures this: if the light goes `off` while the room's motion is `on`, its suppress flag is set so a stale motion event doesn't immediately re-turn-on the light.

### R5 — Leave home

`person.antek → not_home for 2 min` (tracker now only uses `device_tracker.iphone_12` after the UniFi-only fix). Snapshots all lights into `scene.before_leaving`, turns all off, clears suppress flags.

## Scenario matrix (read this and tell me if any row is wrong)

| # | You do… | Expected outcome | Which rule |
|---|---|---|---|
| 1 | Come home: front door → hallway → LR | Hallway light on, then LR light on; `current_room=living_room`; hallway off ~30 s after you settle in LR | Turn-on + hallway_light_off |
| 2 | Sit on the bed in LR, still for 3 hours | LR stays on; `current_room` stays `living_room`; nothing else fires | No rule fires |
| 3 | LR → hallway (grab mail) → LR, total 20 s | LR stays on throughout; `current_room` stays `living_room` | No rule fires |
| 4 | LR → bathroom → LR, total 30 s (quick use) | Bathroom on during visit; LR stays on | R1 scheduled but current_room flips back → R1 turns off bathroom, not LR |
| 5 | LR → bathroom, stay 10 min | LR off 30 s after entering bathroom; bathroom stays on until 1.5 min of no motion | R1 turns off LR, eventually R3 turns off bathroom |
| 6 | LR → laundry → hang in hallway 3 min → LR | LR off 30 s after entering laundry; laundry off after 1.5 min of stillness; nothing else fires during hallway dwell because laundry was already off | R1, R3 |
| 7 | **LR → hallway only, dwell 2 min, return to LR** | LR off ~60 s into hallway dwell; `current_room=none`; on return, LR motion fires and LR comes back on, `current_room=living_room` | **R2** (the new rule) |
| 8 | LR → kitchen (via hallway) → kitchen dwell 30 min → LR | LR stays on the whole time. Kitchen is not tracked; no rule turns off LR. | No rule fires (known limitation) |
| 9 | User turns off LR via Hue dimmer while in LR | LR off; `suppress_living_room_auto_light = on`; LR motion won't re-on until either user turns it on again (clears flag) or the flag is cleared on arrive-home | R4 |
| 10 | LR motion sensor blips off for 0.2 s while user on couch | LR stays on (no rule samples motion-off under the refactor) | No rule fires |
| 11 | Cat walks through hallway briefly (< 60 s) while user on bed | LR stays on (R2's `for: 60` threshold not met) | No rule fires |
| 12 | **Cat hangs out in hallway > 60 s** while user on bed | LR would turn off (false positive). Known edge case under single-person assumption violation. | R2 false positive |

## Tuning knobs

| Knob | File | Default | Tradeoff |
|---|---|---|---|
| `presence_grace_seconds` | `packages/presence.yaml` | 30 s | Higher = more forgiving of fast returns; lower = snappier cleanup |
| `room_light_timeout_minutes` | `packages/presence.yaml` | 1.5 min | How long bathroom/laundry stay on after motion clears |
| Hallway dwell threshold | `automations.yaml` R2 trigger `for:` | 60 s | Higher = less likely to trip on long transits; lower = faster LR-off when hallway dwelling |
| Hue sensor `occupancy_timeout` (per device, in Z2M) | Z2M per-device config | LR 5 / BR 15 / HW 30 / Laundry 60 | Lower = sensor reports off faster after you stop moving. Under the refactor this only matters for R3 (bathroom + laundry fallback). |

## Live verification

The dashboard gains a **Presence Debug** view. It shows: each sensor's current state, seconds since last change, `current_room`, each suppress flag, and a live "R2 would fire in N seconds" readout so you can watch the model think.
