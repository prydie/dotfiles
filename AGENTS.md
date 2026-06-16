# AGENTS

## Visual Review

Use `bin/webshot` to capture webpages for visual inspection.

Authenticated Home Assistant pages should be captured by cloning the local Chrome profile instead of touching the live profile directly:

```bash
bin/webshot \
  --clone-user-data-dir-from ~/.config/google-chrome \
  --profile-directory Default \
  https://hass.nas.prydie.co.uk/solar \
  -o /tmp/ha-solar.png
```

Notes:
- `--clone-user-data-dir-from` is preferred over `--user-data-dir` for an already-open Chrome profile. It avoids `SingletonLock` errors and does not mutate the live profile.
- For Grafana or other HTTP Basic auth pages, prefer `--basic-auth user:password` over embedding credentials in the URL. Some dashboard frontends break when their JavaScript sees `user:pass@host` URLs.
- Use `--profile-directory Default` unless a different Chrome profile is known to hold the logged-in session.
- Default output is under `/tmp`; pass `-o` when you want a stable path.
- Adjust viewport with `--width` and `--height` when reviewing responsive layouts.
- Increase `--timeout-ms` for slower dashboards or cards that need more time to render.

Recommended review loop for Home Assistant dashboards:
1. Apply dashboard config with `uv run bin/ha dashboard set-config ...`
2. Capture the page with `bin/webshot --clone-user-data-dir-from ...`
3. Inspect the resulting image and iterate on layout/content.
