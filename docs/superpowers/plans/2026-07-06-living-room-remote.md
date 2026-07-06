# Living Room Remote Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the incomplete Living Room TV remote layout with the approved compact layout and verified Samsung commands.

**Architecture:** Keep the existing Universal Remote Card, entities, conditional wrapper, app launch actions, and visual theme. Change only its rows, add an explicit custom circle pad, and extend its scoped styles before deploying the complete dashboard through the existing Home Assistant CLI.

**Tech Stack:** Home Assistant Lovelace JSON, Universal Remote Card, Samsung TV remote commands, repository `bin/ha` and `bin/webshot`

---

## File Structure

- Modify: `tools/home_assistant/dashboards/home_dashboard.json` — source copy of the default Lovelace dashboard.
- Use: `tools/home_assistant/ha.py` through `bin/ha` — fetch and deploy dashboard JSON.
- Use: `tools/webshot.py` through `bin/webshot` — authenticated desktop and phone-width visual review.

### Task 1: Capture the Failing Baseline

- [ ] **Step 1: Validate the local JSON and assert the missing controls**

Run:

```bash
jq -e . tools/home_assistant/dashboards/home_dashboard.json >/dev/null
jq -e '
  .. | objects
  | select(.title? == "Living Room TV")
  | (.rows | flatten) as $controls
  | ($controls | index("power_off")) != null
    and ($controls | index("home")) != null
    and ($controls | index("volume_mute")) != null
    and ($controls | index("play_pause")) != null
' tools/home_assistant/dashboards/home_dashboard.json
```

Expected: JSON validation exits zero; the control assertion exits non-zero.

- [ ] **Step 2: Assert that the card lacks an explicit Enter mapping**

Run:

```bash
jq -e '
  .. | objects
  | select(.title? == "Living Room TV")
  | any(.custom_actions[]?;
      .name == "circlepad"
      and .tap_action.action == "key"
      and .tap_action.key == "KEY_ENTER")
' tools/home_assistant/dashboards/home_dashboard.json
```

Expected: exit non-zero.

### Task 2: Implement the Approved Remote

**Files:**

- Modify: `tools/home_assistant/dashboards/home_dashboard.json:117`

- [ ] **Step 1: Replace the remote rows**

Set the card's `rows` to:

```json
[
  ["power_off", "bbc_iplayer", "plex"],
  ["circlepad"],
  ["back", "home", "volume_mute"],
  ["volume_down", "play_pause", "volume_up"]
]
```

- [ ] **Step 2: Add the explicit circle-pad action before the app actions**

Add this object to `custom_actions`:

```json
{
  "type": "circlepad",
  "name": "circlepad",
  "label": "OK",
  "tap_action": {
    "action": "key",
    "key": "KEY_ENTER"
  },
  "up": {
    "icon": "mdi:chevron-up",
    "tap_action": {
      "action": "key",
      "key": "KEY_UP"
    },
    "hold_action": {
      "action": "repeat"
    }
  },
  "down": {
    "icon": "mdi:chevron-down",
    "tap_action": {
      "action": "key",
      "key": "KEY_DOWN"
    },
    "hold_action": {
      "action": "repeat"
    }
  },
  "left": {
    "icon": "mdi:chevron-left",
    "tap_action": {
      "action": "key",
      "key": "KEY_LEFT"
    },
    "hold_action": {
      "action": "repeat"
    }
  },
  "right": {
    "icon": "mdi:chevron-right",
    "tap_action": {
      "action": "key",
      "key": "KEY_RIGHT"
    },
    "hold_action": {
      "action": "repeat"
    }
  }
}
```

- [ ] **Step 3: Extend the scoped styles**

Keep the existing styles and add:

```css
#power_off::part(button) {
  background: linear-gradient(135deg, #d44955, #a91f2d);
  color: white;
  border: 0;
  box-shadow: 0 10px 22px rgba(169, 31, 45, 0.24);
}
#power_off::part(icon),
#power_off::part(label) {
  color: white;
}
#row-1 {
  gap: 8px;
}
#row-1 remote-button {
  min-width: 64px;
}
#row-1 #bbc_iplayer::part(button),
#row-1 #plex::part(button) {
  min-width: 92px;
  padding: 0 10px;
}
remote-circlepad::part(center-label) {
  color: white;
  font-weight: 800;
  letter-spacing: 0.04em;
}
#row-4 {
  margin-top: 8px;
}
#row-3 remote-button,
#row-4 remote-button {
  min-width: 66px;
  font-size: 0.82rem;
}
```

- [ ] **Step 4: Re-run structural validation**

Run:

```bash
jq -e . tools/home_assistant/dashboards/home_dashboard.json >/dev/null
jq -e '
  .. | objects
  | select(.title? == "Living Room TV")
  | (.rows | flatten) as $controls
  | ($controls | index("power_off")) != null
    and ($controls | index("home")) != null
    and ($controls | index("volume_mute")) != null
    and ($controls | index("play_pause")) != null
    and any(.custom_actions[]?;
      .name == "circlepad"
      and .label == "OK"
      and .tap_action.key == "KEY_ENTER")
' tools/home_assistant/dashboards/home_dashboard.json
```

Expected: both commands exit zero.

### Task 3: Deploy and Review Visually

- [ ] **Step 1: Save the complete dashboard**

Run:

```bash
uv run bin/ha dashboard set-config \
  --dashboard lovelace \
  --config-file tools/home_assistant/dashboards/home_dashboard.json
```

Expected: `Updated dashboard 'lovelace'.`

- [ ] **Step 2: Verify the live config contains the intended mappings**

Run:

```bash
uv run bin/ha dashboard get-config --dashboard lovelace --pretty |
  jq -e '
    .. | objects
    | select(.title? == "Living Room TV")
    | .rows == [
        ["power_off", "bbc_iplayer", "plex"],
        ["circlepad"],
        ["back", "home", "volume_mute"],
        ["volume_down", "play_pause", "volume_up"]
      ]
      and any(.custom_actions[]?;
        .name == "circlepad" and .tap_action.key == "KEY_ENTER")
  '
```

Expected: exit zero.

- [ ] **Step 3: Capture desktop and phone-width renders**

Run:

```bash
bin/webshot \
  --clone-user-data-dir-from ~/.config/google-chrome \
  --profile-directory Default \
  https://hass.nas.prydie.co.uk/lovelace/default_view \
  -o /tmp/ha-living-room-remote-desktop.png \
  --width 1440 --height 1200 --timeout-ms 60000

bin/webshot \
  --clone-user-data-dir-from ~/.config/google-chrome \
  --profile-directory Default \
  https://hass.nas.prydie.co.uk/lovelace/default_view \
  -o /tmp/ha-living-room-remote-phone.png \
  --width 390 --height 844 --timeout-ms 60000
```

Expected: both PNG files exist and show Off, both apps, an OK-labelled D-pad,
Back, Home, Mute, Volume Down, Play/Pause, and Volume Up without clipping.

### Task 4: Verify Commands Against the TV

- [ ] **Step 1: Verify the non-destructive Samsung commands**

With the TV showing a navigable screen, use the rendered card to press one
direction and OK. Confirm focus moves once and the highlighted item opens.

- [ ] **Step 2: Verify the supporting controls**

Use the rendered card to test Back, Home, Mute, Volume Down, Play/Pause, and
Volume Up. Confirm each produces the corresponding TV action.

- [ ] **Step 3: Verify both application shortcuts**

Press BBC iPlayer and Plex separately. Confirm each launches its existing
application ID.

- [ ] **Step 4: Verify Off last**

Press Off and confirm the TV powers down. The conditional card should then
disappear when `media_player.living_room_tv_2` reports `off`.

- [ ] **Step 5: Inspect recent Home Assistant errors**

Run:

```bash
ssh home-nas '
  cd /volume1/docker/homeassistant &&
  /usr/local/bin/docker compose logs --since=10m homeassistant 2>&1 |
  grep -iE "living.?room|samsung|remote.send_command|play_media" |
  tail -100
'
```

Expected: no errors from the tested remote actions.
