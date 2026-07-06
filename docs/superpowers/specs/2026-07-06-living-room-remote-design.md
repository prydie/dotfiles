# Living Room Remote Redesign

## Context

The default Home Assistant dashboard contains a conditional
`custom:universal-remote-card` for the Living Room Samsung TV. It currently
provides BBC iPlayer, Plex, a visually ambiguous circle pad, Back, and volume
controls. It lacks an Off button, Home, Mute, and playback control.

## Requirements

- Keep the remote compact and focused on frequently used controls.
- Keep the BBC iPlayer and Plex shortcuts.
- Add an explicit Off action.
- Make the D-pad centre visibly and functionally act as OK/Enter.
- Add Home, Mute, and Play/Pause.
- Retain Back, directional navigation, and volume controls.
- Continue showing the card only while the TV is on.
- Preserve the existing light visual treatment and branded app buttons.

## Layout and Actions

Use this row order:

1. Off, BBC iPlayer, Plex
2. Custom circle pad with a centre labelled OK
3. Back, Home, Mute
4. Volume Down, Play/Pause, Volume Up

Use the Universal Remote Card's Samsung mappings:

- Off: `KEY_POWEROFF`
- D-pad centre: `KEY_ENTER`
- Directions: `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, and `KEY_RIGHT`
- Back: `KEY_RETURN`
- Home: `KEY_HOME`
- Mute: `KEY_MUTE`
- Volume: `KEY_VOLDOWN` and `KEY_VOLUP`
- Play/Pause: `media_player.media_play_pause`

Retain the existing `media_player.play_media` actions and application IDs for
BBC iPlayer and Plex.

## Styling

Keep the rounded pale card, white control buttons, dark navigation centre, and
branded iPlayer/Plex gradients. Make Off red and label it clearly. Display
`OK` in the D-pad centre. Keep touch targets large enough for a phone while
fitting the controls within the existing dashboard column.

## Deployment and Verification

Update `tools/home_assistant/dashboards/home_dashboard.json`, validate its JSON,
and apply it to the default Lovelace dashboard with the repository Home
Assistant tooling. Capture the authenticated dashboard with `bin/webshot` and
inspect desktop and phone-width renders.

Verify that:

- the card displays only while the TV is on;
- all controls fit without clipping or horizontal overflow;
- Off is visually distinct;
- the D-pad centre visibly says OK;
- BBC iPlayer and Plex still launch through their existing actions;
- OK sends `KEY_ENTER`;
- Off sends `KEY_POWEROFF`;
- Back, Home, Mute, volume, and Play/Pause have the intended mappings.

