# Growth Attribution & Measurement

High-level, **directional** view of CAC, LTV and Net Revenue per channel for ClerkMinutes — built for leadership (CEO, Product, CTO, Growth, Sales). Open `index.html` in any browser; no server or build step needed to view.

## What it shows
- **Total overview** — Net Revenue (ARR), spend, net after spend, blended CAC, first-year ROI, attribution coverage. **Revenue figures count only channels/campaigns that have a cost entered** (so it's an apples-to-apples economic view); shows "—" until you add costs.
- **Movable & filterable table** — drag column headers or the ⠿ row handle to reorder (saved in-browser); type in the filter box to narrow rows; "Reset layout" restores defaults.
- **Per-channel economics** — every won customer rolled up by **Foundational Channel** or by **Growth Lever** (toggle). Enter spend per row to unlock CAC, payback & ROI.
- **Monthly breakdown** — wins / revenue stacked by channel, limited to the selected period; click any month for a modal breakdown.
- **Growth Decision Framework — AI Suggestions** — auto-generated Scale / Maintain / Fix / Cut verdict per channel/lever from the numbers. Each card has a dropdown to **manually override** the decision (falls back to the AI suggestion when set to "Use AI suggestion"); overrides are saved and tagged "Manual override".
- **Period selector** — Focus (Feb 2025 → now), All time, custom from→to range, or by year / quarter / month.

## Channel taxonomy (how Notes map to channels)
Reconstructed from the CRM `Notes / Lead Source` free-text (codes like `PT0525SwitchGO` = Postcard, May 2025, SwitchGO). Rules in `build-data.py → classify()`:

| Note signal | Foundational channel | Notes |
|---|---|---|
| `(HG_CM)` coded rows + `ClerkMinutes Trial Started` | **Referral Postcard** | also a Growth Lever (channel + lever) |
| Other `PT…` / `LT…` codes, `Coast-to-Coast`, `Evolution`, `SwitchGO`, `Land Grab`, `PC Exclusive 30-day`, generic "postcard" | **Campaign Postcard** | named campaign becomes the lever |
| `Google Ads`, `gas`, `adwords` | **Google Ads** | |
| `YouTube` | **YouTube Commercial** | |
| `NMMD`, `Lightning Strike`, "meeting minutes day" | **Multi-channel (NMMD)** | one multi-channel campaign |
| `NCAMC2025`-style codes, `OAMR`, `NEACTC`, `conference`, `UTconf` | **Conferences & Events** | |
| `exclusivecall` / "call experiment", `cold call` | **Sales Outbound** | |
| `TW…` codes / "town web proposal" | **Partner — Town Web** | |
| `HG…` prefix / "heygov proposal" | **Partner — HeyGov** | |
| `??`, blank, `None`, bare town names | **Unattributed** | OK to leave — no signal to recover |

## Key concepts & honest limits
- Attribution is **directional, not exact.** ~20% of customers are `Unattributed` (mostly `??`/blank/`None`). Tightening lead-source tagging is the single biggest accuracy win.
- **Default view is the Feb 2025 → now focus window** (leadership's focus period). Switch to All time or any single month in the Period selector.
- These are **won (paid) customers only.** Trial→paid conversion and 14-day maturity are *not* wired in — the CRM export has no trial-start dates. Placeholder section activates once a trials export is provided.
- **Cost has no source in the CRM** — you enter it per active period. Saved in your browser (`localStorage`); **Export** to share, **Import** to load.
- **Referral Postcard CAC is grounded from Aug 2025** — we don't have earlier spend, so its CAC counts only customers won since then (flagged with `*`). Set per-channel cost-start dates in `index.html → COST_START`.
- **No LTV.** We deliberately don't model LTV (needs a churn guess that adds complexity without rigor). Health is judged on **payback period** (months to recoup CAC, fixed bands: ≤12 Scale, ≤18 Maintain, ≤24 Fix, >24 Cut) and **first-year ROI** shown as a return multiple (× — e.g. `1.4×` = $1.40 back per $1 spent in year one).
- **Cost field has three states:** type a **number** (including an explicit **$0** for free channels → "Scale (free)"), leave it **blank** (= not entered yet), or click **N/A** when spend is unknown (row reads N/A, no false CAC). Each period is its own cost bucket.
- **Click any month** in the Monthly breakdown for a modal with that month's full per-channel split.
- **Net Revenue is color-tagged** by net after spend: green = positive, yellow = slightly negative (lost ≤25% of revenue), red = very negative. Only tags once a channel's cost is known.
- **Graduates column** — per-channel/lever dropdown for maturity stage: Experiment → Growth Lever → Foundational Channel → Sunset → N/A. Always available (non-applicable rows like Unattributed default to N/A). Saved in-browser, included in Export.
- **Foundational Channel vs Growth Lever:** a Foundational Channel is an ongoing channel-level tool; a Growth Lever is a campaign that runs within one. Toggle with **Group by**. The two views are filtered lenses with different denominators:
  - **Foundational Channels** excludes campaign-only rows (Campaign Postcard, Multi-channel NMMD) — those are campaigns, shown under Growth Levers.
  - **Growth Levers** excludes channel-only wins (the old "Untracked / channel" buckets) — those have no campaign tag and belong under Foundational Channels.
  - Each view shows a "Showing X of Y wins" note so the excluded count is explicit. Configured via `FOUNDATIONAL_HIDE` and `keyOf()` in `index.html`; the two 30-day experiments merge into "30-day Experiment" via `LEVER_MERGE`.

## Monthly refresh (when a new CRM export lands)
```bash
cd growth-attribution
python3 build-data.py "/path/to/HeyGov miniCRM (ARR) - ClerkMinutes Customers (NN).csv" --inject
```
This re-classifies every row and rewrites the data baked into `index.html`. Your saved costs/assumptions are untouched (they live in the browser, not the file).

To review the channel split without writing the file, run it without `--inject` — it prints a summary to stderr.

## Shared live data (Supabase) — the team edits in the link

The dashboard is wired to a **Supabase** project (`rjywjxmhfmcwlqnanppo`). All costs, graduate tags, decisions and layout are stored in one shared row (`growth_settings`, id=1). Anyone you send the deployed link to edits the **same live data** — changes save automatically and everyone sees them on reload. The header shows a "☁ Shared via Supabase" status with the last-saved time.

- The anon key embedded in `index.html` is **safe to commit/ship** (it's a public browser key; access is governed by Row-Level-Security policies on that one table).
- Current policy = **anyone with the link can read & edit.** To lock it to your team, add a shared password gate or Supabase Auth (ask and I'll wire it).
- Edits are "last save wins" — fine for a small team editing occasionally.
- localStorage is now just an offline cache; the Supabase row is the source of truth (loaded on open).

To reset everything, run in Supabase SQL editor: `update growth_settings set data='{}'::jsonb where id=1;`

## (Optional) Bake a static snapshot for deploy (GitHub → Netlify)

This is the older fallback path (used if you ever turn Supabase off). It bakes data into the file itself:

Costs, graduate tags, manual decisions and layout are stored in **your browser** (localStorage) — they don't travel with the repo. To make the **deployed** site show your data for everyone:

1. In the dashboard, enter everything, then click **Export** → downloads `growth-attribution-settings.json` to your Downloads.
2. Bake it into the file:
   ```bash
   cd growth-attribution
   python3 save-settings.py --inject       # auto-finds the newest export in ~/Downloads
   # or: python3 save-settings.py /path/to/growth-attribution-settings.json --inject
   ```
   This writes your data into the `DEFAULTS` block of `index.html`.
3. Commit & push:
   ```bash
   git add index.html && git commit -m "Update growth dashboard data" && git push
   ```
   Netlify rebuilds and the live site now shows your numbers.

How it loads: `index.html` reads the baked `DEFAULTS` first (what every visitor sees), then layers any local browser edits on top (so the person editing always sees their latest, and viewers see the committed baseline). To preview a clean "what visitors see" state, open the page in a private window.

**Netlify config:** this is a plain static site — no build command, publish directory = repo root. Run `save-settings.py` again whenever you want to push updated numbers.

## Cost import format (optional)
Instead of typing costs in the panel you can **Import** a CSV with this header:
```
period,channel,spend
_alltime,Postcards,120000
2026-06,Google Ads,3000
```
`period` is `_alltime` or a `YYYY-MM` month; `channel` must match the channel/lever name shown in the table. See `costs-template.csv`.
