# Production architecture

The Daily Brief presentation layer and daily intelligence payload are separated.

## Production files
- `index.html`: frozen presentation shell. It must not contain daily intelligence data.
- `assets/styles.css`: frozen visual design.
- `assets/app.js`: frozen rendering and filter behaviour.
- `data/latest.json`: the only file normally replaced by a successful daily run.
- `data/archive/YYYY-MM-DD.json`: immutable successful daily snapshots.
- `legacy/bootstrap-2026-09-27.html`: last-known-good pre-migration dashboard, retained as a bootstrap/fallback.

## Transactional publish rule
Research and database ingestion happen before publication. Build a candidate JSON payload, validate it, create the dated archive, then replace `data/latest.json`. Do not modify the frozen presentation layer during routine daily runs.

A candidate must not be published unless it contains exactly 40 tracked accounts; preserves account-manager mappings and category grouping; contains a More Reading subsection for every account; has no more than five More Reading items per account; contains only items in the five-day lookback; orders them newest to oldest; excludes the selected Top Story from More Reading; contains real verified URLs; and confirms all required Supabase writes.

If any gate fails, leave `data/latest.json` unchanged. The public dashboard therefore remains on the last-known-good brief.

## Recovery layers
1. `backup/pre-data-separation-2026-09-27` preserves the complete pre-migration production state.
2. `legacy/bootstrap-2026-09-27.html` preserves the working dashboard blob inside the production tree.
3. Dated JSON snapshots preserve every successful brief independently of `latest.json`.
4. Git history permits rollback of application code or data.
5. Supabase remains the append-only historical article database, not the dashboard runtime dependency.

## Daily run order
Web research -> verified structured candidate -> Supabase append/upsert -> validation -> dated archive -> update `latest.json` -> Netlify deploy -> production smoke test.

Never replace a working `latest.json` with partial or failed data.