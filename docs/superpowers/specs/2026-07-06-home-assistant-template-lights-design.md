# Home Assistant Template Light Migration

## Context

Home Assistant 2026.6 removed legacy template entities. The two paired-light
entities in `/volume1/docker/homeassistant/configuration.yaml` on `home-nas`
still use `light: - platform: template`, so Home Assistant restores their last
state but marks them unavailable:

- `light.playroom_ceiling_master`
- `light.holly_bedroom_ceiling_master`

The Playroom Matter bulbs currently work. Holly's underlying Matter and cloud
entities are unavailable independently of this migration.

## Requirements

- Define both paired-light entities with the modern `template:` integration.
- Preserve both entity IDs by retaining their existing unique IDs.
- Preserve power, brightness, colour-temperature, HS-colour, and scene-effect
  controls.
- Continue sending commands to both underlying bulbs in each room.
- Avoid temporary custom integrations or new runtime dependencies.
- Back up the live configuration before changing it.

## Design

Move both light definitions into a `light:` list in the existing `template:`
configuration. Translate the legacy keys to the modern schema:

| Legacy key | Modern key |
| --- | --- |
| `friendly_name` | `name` |
| `value_template` | `state` |
| `level_template` | `level` |
| `temperature_template` | `temperature` |
| `color_template` | `hs` |
| `effect_list_template` | `effect_list` |
| `effect_template` | `effect` |
| `set_color` | `set_hs` |

Remove `min_mireds_template` and `max_mireds_template`; the modern light API
uses Kelvin bounds. Keep the existing action targets and unique IDs. Use the
modern template-light action variables, including `color_temp_kelvin` for
temperature commands and `h`/`s` for HS commands.

## Deployment and Recovery

Create a timestamped copy of `configuration.yaml` on `home-nas`. Apply one
focused edit, then run Home Assistant's configuration checker inside the
existing Compose service. Do not restart Home Assistant unless validation
passes. If startup fails, restore the backup and restart the previous
configuration.

## Acceptance Criteria

- The configuration checker exits successfully.
- Home Assistant restarts successfully without template-light configuration
  errors.
- Both master entities load from the template integration rather than restored
  state.
- The Playroom master controls both bulbs for:
  - turn off and turn on
  - brightness
  - colour temperature
  - HS colour
  - one scene effect
- The Playroom master reports the resulting state and attributes.
- Holly's master entity loads successfully. It may report unavailable while
  its source entities remain unavailable; this external Matter/cloud failure is
  outside this migration.
- Existing unrelated Home Assistant errors do not count as migration failures.

