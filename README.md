# The Inspection Files: Violation Desk

Private MVP dashboard for researching official restaurant inspection violations.

## Deploy On Cloudflare Pages

Use Cloudflare Pages with GitHub.

- Framework preset: `None`
- Build command: leave blank
- Build output directory: `/`

The app is static and loads `data.js` from the repo root.

## Local Refresh

Run from the repo root:

```bash
python3 scripts/export_app_data.py
```

Optional Mecklenburg snapshot refresh:

```bash
python3 scripts/fetch_mecklenburg_snapshot.py
python3 scripts/export_app_data.py
```

## Current Sources

- NYC open data
- Chicago open data
- LA County closure snapshot
- Orange County closure snapshot
- Mecklenburg County detailed inspection snapshot
- San Francisco open data

Some county/vendor portals require browser-assisted snapshots. Those snapshots live in `data-snapshots/`.
