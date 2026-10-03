# Data Dictionary — FEC × Jev Head-to-Head Explorer

How money flows, what each file means, and the methodology traps baked into the numbers.
Generated 2026-10-03. Live app: `start.sh` → http://127.0.0.1:8741

## Runtime files

| File | Role | Shape |
|---|---|---|
| `.env` | Secrets (never commit). `FEC_API_KEY`, `JEV_KEY` | `KEY=value` lines |
| `server.py` | Stdlib-only backend. Serves `index.html`, proxies FEC, calls Jev, runs analysis jobs | — |
| `index.html` | Frontend: preset cards, candidate search, matchup picker (multi-committee sides), Bars + Sankey tabs | — |
| `presets.json` | 6 curated races | Array of `{id, name, note, cycle, a, b}`; each side `{label, candidate_id, committees: [{committee_id, committee_name, vehicle}]}` |
| `start.sh` | Startup: `cd` to dir, optional `PORT=` override, runs server | — |

## Sides: one side = a SET of committees (not "the campaign")

Each matchup side holds 1+ committees. Never summed naively: any Schedule B
record whose `recipient_committee_id` (or `unused_recipient_committee_id`)
belongs to the same side is **eliminated** — reported back as
`internal_transfers_excluded` $ + `internal_transfer_count`, never counted
as spending. Out-of-side transfers (e.g. to RNC/state parties) stay under
the `transfers` tactic. Rule is exact ID match, no fuzzy name matching.

### Verified vehicle identities (FEC presidential financial summary + filings)

- **Harris 2024 principal = C00703975** ($1.175B cycle disbursements).
  Current API name record reads "FIGHT FOR THE PEOPLE PAC / Unauthorized"
  (names drift across cycles); `candidate_ids` = Biden + Harris and the
  presidential summary confirm it is the campaign vehicle.
- **No single Trump 2024 principal exists in FEC data** — the presidential
  summary splits him across vehicles. Trump side = Never Surrender
  (C00828541, leadership PAC, $471M) + Save America (C00762591, leadership
  PAC, $112M). C00580100 (MAGA PAC) is Unauthorized + only $17M in-cycle:
  deliberately excluded.
- All Senate presets are principal-vs-principal (designation `P` verified).
- OH 2024 omitted: Brown's principal unfindable via API, his JFCs total
  <$1M — too small to chart.

## Learned translation tables (Jev output, cached)

Jev (`jev-1.13.0` via `jev-latest`) maps messy FEC free text → closed categories.
First-seen strings cost one batched Choice call; hits are free forever.

| File | Maps | Entries | Low-conf (<0.8) |
|---|---|---|---|
| `tactic_cache.json` | `disbursement_description` → tactic | ~744 | ~134 |
| `sector_cache.json` | `contributor_occupation` → sector | ~156 | ~42 |
| `tactic_translations.json` | Human-readable export of tactic cache | 744 | 134 |
| `sector_translations.json` | Human-readable export of sector cache | 156 | 42 |
| `committee_names.json` | `committee_id` → resolved display name | grows per run | — |

Export entry shape: `{raw, canonical, confidence, source}` + `meta` header
(`model`, `generated`, `note`). `source` is `jev-batch-1` (validated prototype),
`jev-harris-walk` / `jev-trump-walk`, `jev-web` (Schedule B, app runs), or
`jev-web-e` (Schedule E, app runs).

### Canonical tactics (7)

| Tactic | Covers (examples) |
|---|---|
| `media` | Media buys, placed media, digital/online advertising, video production, media consulting |
| `direct_contact` | Mail/postage, phones, telemarketing, canvassing, palm cards, yard signs, email/SMS outreach |
| `operations` | Payroll, rent, travel, lodging, security, IT, software, data services, office costs |
| `transfers` | Transfers / contributions / donations to other committees |
| `legal_compliance` | Legal, compliance, polling, taxes, strategy/research/communications consulting |
| `fundraising_ops` | Credit-card/merchant/bank fees, refunds, fundraising consulting |
| `events` | Event staging/production, site rental, catering, event AV/security/broadcasting |

### Donor sectors (9)

`retired_not_employed`, `legal`, `education`, `health`, `business_exec`,
`technical`, `arts_media`, `admin_service`, `unknown`.

## API surface (`server.py`)

| Endpoint | Upstream | Notes |
|---|---|---|
| `GET /api/presets` | local `presets.json` | — |
| `GET /api/search/candidates?q=` | FEC `/candidates/search/` | `{candidate_id, name, office, party, state, election_years}` |
| `GET /api/candidate/:id/committees?cycle=` | FEC `/committees/?candidate_id=&cycle=` | `{committee_id, name, designation, type}` |
| `GET /api/committee/:id?cycle=` | FEC `/committee/` + `/totals/` | info + `{receipts, disbursements, individual_contributions, cash_on_hand}` |
| `POST /api/analyze` | — | `{a_committees: [{committee_id, committee_name?}], a_label, a_candidate?, b_*, cycle, max_pages}` → `{job_id}` (legacy single `a_committee`/`b_committee` keys still accepted) |
| `GET /api/jobs/:id` | — | `{status, progress{side, stage, n}, result?}` |

`result` = `{a, b, cycle, tactic_cache_size, sector_cache_size, sankey?}`.
Side = `{label, committees: [{committee_id, committee_name, receipts,
disbursements}], totals (summed), records_walked, records_in_year,
internal_transfers_excluded, internal_transfer_count,
spend_total, spend_by_tactic, count_by_tactic, coverage, donor_n,
donor_by_sector, new_tactic_mappings, new_sector_mappings}`.
`sankey` = `{nodes[{id, label, kind}], links[{source, target, value}],
records, total, new_mappings}`; kinds: `committee`, `tactic`,
`outcome-S`, `outcome-O`.

## FEC source fields (as used)

**Schedule B** (`/schedules/schedule_b/`, committee's own spending):
`disbursement_description` (free text → tactic), `disbursement_amount`,
`disbursement_date`, `recipient_name`, `sub_id` (dedupe key),
`filing_form`, `report_year`.

**Schedule E** (`/schedules/schedule_e/`, independent expenditures):
`committee_id` (spender), `expenditure_description` (free text → tactic),
`expenditure_amount`, `expenditure_date`, `candidate_id` + `candidate_name`
(subject), `support_oppose_indicator` (`S`/`O`), `sub_id`, `filing_form`.

**Totals** (`/committee/:id/totals/?cycle=`): denominator for coverage
(`sample $ / cycle disbursements`).

## Methodology (traps handled — do not "simplify" these away)

1. **FEC ignores `page` when `sort` is set.** Pages 1–N return identical
   `sub_id`s. Always cursor with `last_*` + `last_index` from
   `pagination.last_indexes`, and dedupe on `sub_id`. Unsorted paging 504s
   on large committees — there is no shortcut.
2. **`cycle=` filter leaks across years.** Filter to election-year dates in
   code (`disbursement_date` / `expenditure_date` startswith year).
3. **Top-by-amount sampling hides high-frequency/low-amount tactics.**
   Harris top-100 was 100% media; Trump's showed $0.96M legal vs $10.5M in
   the full walk. Walk deep (cursor) for mix honesty.
4. **Schedule E double counts.** Exclude `filing_form = F24` (24/48hr notices
   duplicate F3X entries — FEC's own aggregate rule). Collapse
   exact-duplicate lines (committee, amount, date, description, candidate,
   S/O): some filers repeat a program total per payee line (observed: 9×
   $114M). Residual single-line filer errors are kept as-filed and flagged,
   not silently dropped.
5. **One ad, two filings.** A spot backing X while hitting Y is filed once
   per candidate at full amount (11 CFR 106.1; Schedule E is one
   candidate + S/O per line). Sankey outcome bands overlap by design —
   never sum across outcomes. Same convention as OpenSecrets.
6. **Dollars are summed in code, never by the model.** Jev returns
   categories + confidences only. Confidence < 0.8 is flagged in UI;
   dollars behind sub-0.8 mappings are typically < 1% of sample.

## External cross-checks (OpenSecrets, 2024 outside spending by candidate)

| Race | Subject | Supported | Opposed |
|---|---|---|---|
| President | Harris | $733M | $569M |
| President | Trump | $234M | $154M |
| OH Senate | Moreno (R) | $68M | $86M |
| OH Senate | Brown (D) | $24M | $114M |
| PA Senate | Casey (D) | $18M | $110M |
| PA Senate | McCormick (R) | $27M | $68M |
| MT Senate | Tester (D) | $17M | $63M |
| MT Senate | Sheehy (R) | $18M | $59M |
| AZ Senate | Gallego (D) | $25M | $21M |
| AZ Senate | Lake (R) | $2M | $25M |

Source: `opensecrets.org/outside-spending/by_candidate/2024`
(Dem candidate: supported = "For Dems", opposed = "Against Dems"; mirrored
for Republicans). Our top-by-amount walks should land *under* these totals
at plausible coverage ratios — check per-outcome, not just grand total.
