# FEC × Jev — Head-to-Head Campaign Finance Explorer

Whose money, doing what, for or against whom. FEC filings supply the facts;
Jev (TypeSafe's System One model) supplies the semantic normalization that
makes hundreds of free-text filing descriptions chartable. Dollars are always
summed in code — the model only ever returns categories + confidences.

## Run it

```sh
cd fec
./start.sh            # http://127.0.0.1:8741
PORT=9000 ./start.sh  # override port
```

Stdlib Python only, no dependencies. API keys stay server-side in `.env`
(`FEC_API_KEY`, `JEV_KEY`) and are never sent to the browser.

## What it does

Pick a preset race (2024 President, 2024 MT/PA/AZ Senate, 2026 NC/ME Senate)
or build your own: search FEC candidates → add their committees to Side A/B
(a side may hold several committees), pick a cycle and walk depth, run.

Two views per matchup:

- **Bars** — each side's own spending by Jev-normalized tactic (media,
  direct contact, operations, transfers, legal/compliance, fundraising,
  events) plus donor-occupation sectors. Money moving between a side's own
  committees is eliminated by recipient-ID match, never counted as spending.
- **Outside-money Sankey** — every committee filing independent expenditures
  *about* either candidate (Schedule E): spender → tactic → Pro-/Anti-X
  outcome. This is the super-PAC battlefield the Bars tab excludes.

## Key findings baked in

- Top-by-amount sampling hides high-frequency/low-amount tactics on both
  sides (Harris top-100 was 100% media; Trump's $0.96M visible legal spend
  was really $10.5M across 152 small payments). The app cursor-walks deep
  instead.
- 2024 outside money pointed overwhelmingly at Harris ($1.31B vs Trump's
  $0.39B per OpenSecrets) — on both the pro and anti sides.
- One ad is routinely filed twice (pro-X + anti-Y at full amount each);
  outcome bands overlap by design, matching FEC/OpenSecrets convention.

## Repo map

| File | Purpose |
|---|---|
| `server.py` / `index.html` / `start.sh` | App (backend / frontend / startup) |
| `presets.json` | 6 curated races with vehicle-type labels |
| `tactic_cache.json` / `sector_cache.json` | Live Jev caches (write-through; hits are free forever) |
| `tactic_translations.json` / `sector_translations.json` | Human-readable exports of the caches |
| `committee_names.json` | Resolved spender-committee display names |
| `DATA_DICTIONARY.md` | Full schema, endpoint, methodology, and cross-check reference |
| `fec.md` / `jev.md` | Source notes on the FEC API and the TypeSafe skill |
| `jev_fec_prototype.html` | Original single-committee prototype (superseded, kept for history) |

## Methodology in 30 seconds

Cursor-walk Schedule B/E top-by-amount (FEC ignores `page` with `sort`;
cursor via `last_indexes`, dedupe on `sub_id`), filter to election-year
dates (`cycle=` leaks across years), exclude F24 rapid-notice filings and
collapse exact-duplicate lines (both double-count), classify only uncached
descriptions through one batched Jev Choice call, aggregate dollars in code,
reconcile against `/committee/totals/`. Confidence < 0.8 is flagged in-UI.
See `DATA_DICTIONARY.md` for the full version including the six traps you
must not "simplify" away.
