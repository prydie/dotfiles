# Home Assistant Template Lights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the two paired ceiling-light entities by migrating them to Home Assistant's modern template integration and verify their controls.

**Architecture:** Keep the live configuration on `home-nas` as the source of truth. Replace only the removed legacy light platform block, append equivalent lights to the existing `template:` integration, validate inside the running Home Assistant 2026.6.4 container, and restart through the existing Compose project.

**Tech Stack:** Home Assistant 2026.6 YAML, Jinja templates, Docker Compose, repository `bin/ha` API client

---

## File Structure

- Modify: `home-nas:/volume1/docker/homeassistant/configuration.yaml` — live Home Assistant configuration.
- Create: `home-nas:/volume1/docker/homeassistant/configuration.yaml.<timestamp>.bak` — rollback copy.
- Use: `tools/home_assistant/ha.py` through `bin/ha` — state and action verification without changes.

### Task 1: Capture the Failing Baseline

- [ ] **Step 1: Confirm the current configuration parses but the removed platform does not load**

Run:

```bash
ssh home-nas 'cd /volume1/docker/homeassistant && /usr/local/bin/docker compose exec -T homeassistant python -m homeassistant --script check_config -c /config'
uv run bin/ha state light.playroom_ceiling_master
uv run bin/ha state light.holly_bedroom_ceiling_master
```

Expected: configuration checking exits zero, while both states print
`unavailable`.

- [ ] **Step 2: Confirm the Playroom test seam and Holly's external outage**

Run:

```bash
uv run bin/ha state light.playroom_bulb_1_matter
uv run bin/ha state light.playroom_bulb_2_matter
uv run bin/ha state light.holly_bedroom_bulb_1_matter
uv run bin/ha state light.holly_bedroom_bulb_2_matter
```

Expected: both Playroom bulbs report `on` or `off`; both Holly bulbs currently
report `unavailable`.

### Task 2: Back Up and Migrate the Definitions

- [ ] **Step 1: Copy the live file locally and create a remote rollback copy**

Run:

```bash
scp home-nas:/volume1/docker/homeassistant/configuration.yaml /tmp/homeassistant-configuration.yaml
ssh home-nas 'cp -p /volume1/docker/homeassistant/configuration.yaml "/volume1/docker/homeassistant/configuration.yaml.$(date +%Y%m%dT%H%M%S).bak"'
```

Expected: both commands exit zero.

- [ ] **Step 2: Remove the complete legacy block**

In `/tmp/homeassistant-configuration.yaml`, remove the section beginning with:

```yaml
light:
  - platform: template
```

and ending immediately before:

```yaml
automation: !include automations.yaml
```

- [ ] **Step 3: Add both modern lights to the existing `template:` list**

Insert this block as another item under the existing top-level `template:`
list:

```yaml
  - light:
      - name: "Playroom Ceiling Lights"
        unique_id: playroom_ceiling_master
        state: "{{ is_state('light.playroom_bulb_1_matter', 'on') }}"
        level: "{{ state_attr('light.playroom_bulb_1_matter', 'brightness') | int(0) }}"
        temperature: >
          {{ ((1000000 / state_attr('light.playroom_bulb_1_matter', 'color_temp_kelvin'))
              if state_attr('light.playroom_bulb_1_matter', 'color_temp_kelvin')
              else 300) | int }}
        hs: >
          {% if state_attr("light.playroom_bulb_1_matter", "color_mode") == "color_temp" %}
            {{ none }}
          {% else %}
            {% set value = state_attr("light.playroom_bulb_1_matter", "hs_color") %}
            {{ value if value is not none else (0, 0) }}
          {% endif %}
        effect_list: "{{ state_attr('select.playroom_bulb_1_scene', 'options') or [] }}"
        effect: >
          {% set options = state_attr("select.playroom_bulb_1_scene", "options") or [] %}
          {% set value = states("select.playroom_bulb_1_scene") %}
          {{ value if value in options else none }}
        turn_on:
          action: light.turn_on
          target:
            entity_id:
              - light.playroom_bulb_1_matter
              - light.playroom_bulb_2_matter
        turn_off:
          action: light.turn_off
          target:
            entity_id:
              - light.playroom_bulb_1_matter
              - light.playroom_bulb_2_matter
        set_level:
          action: light.turn_on
          target:
            entity_id:
              - light.playroom_bulb_1_matter
              - light.playroom_bulb_2_matter
          data:
            brightness: "{{ brightness }}"
        set_temperature:
          action: light.turn_on
          target:
            entity_id:
              - light.playroom_bulb_1_matter
              - light.playroom_bulb_2_matter
          data:
            color_temp_kelvin: "{{ color_temp_kelvin }}"
        set_hs:
          action: light.turn_on
          target:
            entity_id:
              - light.playroom_bulb_1_matter
              - light.playroom_bulb_2_matter
          data:
            hs_color:
              - "{{ h }}"
              - "{{ s }}"
        set_effect:
          action: select.select_option
          target:
            entity_id:
              - select.playroom_bulb_1_scene
              - select.playroom_bulb_2_scene
          data:
            option: "{{ effect }}"

      - name: "Holly's Ceiling Lights"
        unique_id: holly_bedroom_ceiling_master
        state: "{{ is_state('light.holly_bedroom_bulb_1_matter', 'on') }}"
        availability: >
          {{ not is_state('light.holly_bedroom_bulb_1_matter', 'unavailable')
             and not is_state('light.holly_bedroom_bulb_2_matter', 'unavailable') }}
        level: "{{ state_attr('light.holly_bedroom_bulb_1_matter', 'brightness') | int(0) }}"
        temperature: >
          {{ ((1000000 / state_attr('light.holly_bedroom_bulb_1_matter', 'color_temp_kelvin'))
              if state_attr('light.holly_bedroom_bulb_1_matter', 'color_temp_kelvin')
              else 300) | int }}
        hs: >
          {% if state_attr("light.holly_bedroom_bulb_1_matter", "color_mode") == "color_temp" %}
            {{ none }}
          {% else %}
            {% set value = state_attr("light.holly_bedroom_bulb_1_matter", "hs_color") %}
            {{ value if value is not none else (0, 0) }}
          {% endif %}
        effect_list: "{{ state_attr('select.holly_bedroom_bulb_1_scene', 'options') or [] }}"
        effect: >
          {% set options = state_attr("select.holly_bedroom_bulb_1_scene", "options") or [] %}
          {% set value = states("select.holly_bedroom_bulb_1_scene") %}
          {{ value if value in options else none }}
        turn_on:
          action: light.turn_on
          target:
            entity_id:
              - light.holly_bedroom_bulb_1_matter
              - light.holly_bedroom_bulb_2_matter
        turn_off:
          action: light.turn_off
          target:
            entity_id:
              - light.holly_bedroom_bulb_1_matter
              - light.holly_bedroom_bulb_2_matter
        set_level:
          action: light.turn_on
          target:
            entity_id:
              - light.holly_bedroom_bulb_1_matter
              - light.holly_bedroom_bulb_2_matter
          data:
            brightness: "{{ brightness }}"
        set_temperature:
          action: light.turn_on
          target:
            entity_id:
              - light.holly_bedroom_bulb_1_matter
              - light.holly_bedroom_bulb_2_matter
          data:
            color_temp_kelvin: "{{ color_temp_kelvin }}"
        set_hs:
          action: light.turn_on
          target:
            entity_id:
              - light.holly_bedroom_bulb_1_matter
              - light.holly_bedroom_bulb_2_matter
          data:
            hs_color:
              - "{{ h }}"
              - "{{ s }}"
        set_effect:
          action: select.select_option
          target:
            entity_id:
              - select.holly_bedroom_bulb_1_scene
              - select.holly_bedroom_bulb_2_scene
          data:
            option: "{{ effect }}"
```

- [ ] **Step 4: Copy the candidate configuration to the server**

Run:

```bash
scp /tmp/homeassistant-configuration.yaml home-nas:/volume1/docker/homeassistant/configuration.yaml
```

Expected: command exits zero.

### Task 3: Validate and Load the Configuration

- [ ] **Step 1: Run Home Assistant's configuration checker**

Run:

```bash
ssh home-nas 'cd /volume1/docker/homeassistant && /usr/local/bin/docker compose exec -T homeassistant python -m homeassistant --script check_config -c /config'
```

Expected: exit zero and no template-light errors. On failure, restore the newest
backup before attempting another migration change.

- [ ] **Step 2: Restart only Home Assistant**

Run:

```bash
ssh home-nas 'cd /volume1/docker/homeassistant && /usr/local/bin/docker compose restart homeassistant'
```

Expected: Compose reports that `homeassistant` restarted.

- [ ] **Step 3: Wait for the API and inspect startup errors**

Run `uv run bin/ha state light.playroom_ceiling_master` repeatedly until it
succeeds, for at most two minutes. Then run:

```bash
ssh home-nas 'cd /volume1/docker/homeassistant && /usr/local/bin/docker compose logs --since=5m homeassistant 2>&1 | grep -iE "template|invalid config|setup failed|error" | tail -200'
uv run bin/ha state light.playroom_ceiling_master
uv run bin/ha state light.holly_bedroom_ceiling_master
```

Expected: no template-light setup errors; Playroom reports `on` or `off`;
Holly reports `unavailable` while its source bulbs remain offline.

### Task 4: Exercise Playroom Controls End to End

- [ ] **Step 1: Record the original master state and attributes**

Run:

```bash
uv run bin/ha state light.playroom_ceiling_master --json > /tmp/playroom-master-before.json
```

Expected: the file contains the state, brightness, colour mode, and applicable
colour attributes.

- [ ] **Step 2: Verify off, on, and brightness propagation**

Run each action, then query both Matter bulbs:

```bash
uv run bin/ha service light.turn_off --data '{"entity_id":"light.playroom_ceiling_master"}'
uv run bin/ha service light.turn_on --data '{"entity_id":"light.playroom_ceiling_master","brightness":96}'
uv run bin/ha state light.playroom_bulb_1_matter --json
uv run bin/ha state light.playroom_bulb_2_matter --json
```

Expected: both bulbs turn off, then both turn on with brightness near `96`.

- [ ] **Step 3: Verify colour-temperature and HS propagation**

Run:

```bash
uv run bin/ha service light.turn_on --data '{"entity_id":"light.playroom_ceiling_master","color_temp_kelvin":4000}'
uv run bin/ha service light.turn_on --data '{"entity_id":"light.playroom_ceiling_master","hs_color":[30,80]}'
uv run bin/ha state light.playroom_bulb_1_matter --json
uv run bin/ha state light.playroom_bulb_2_matter --json
```

Expected: both bulbs accept each action and report the corresponding colour
mode and values, subject to device rounding.

- [ ] **Step 4: Verify effect propagation**

Run:

```bash
uv run bin/ha service light.turn_on --data '{"entity_id":"light.playroom_ceiling_master","effect":"Reading"}'
uv run bin/ha state select.playroom_bulb_1_scene
uv run bin/ha state select.playroom_bulb_2_scene
```

Expected: both selects report `Reading`.

- [ ] **Step 5: Restore the original Playroom state**

Read `/tmp/playroom-master-before.json`. If the original state was `off`, call
`light.turn_off`. If it was `on`, call `light.turn_on` with its original
brightness and either its original `color_temp_kelvin` or `hs_color`.

- [ ] **Step 6: Perform final health checks**

Run:

```bash
uv run bin/ha state light.playroom_ceiling_master --json
uv run bin/ha state light.holly_bedroom_ceiling_master --json
ssh home-nas 'cd /volume1/docker/homeassistant && /usr/local/bin/docker compose ps && /usr/local/bin/docker compose logs --since=10m homeassistant 2>&1 | grep -iE "template|invalid config|setup failed" | tail -100'
```

Expected: Playroom tracks its source light, Holly loads but remains unavailable,
the container is up, and no template configuration errors appear.

