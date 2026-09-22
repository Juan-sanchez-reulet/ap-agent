# Spike: Odoo 19 Community + JSON-2 (week 1)

- **Date:** 2026-09-22
- **Image:** `odoo:19` (native arm64) + `postgres:16`, via `docker-compose.yml`
- **Time spent:** ~40 min
- **Script:** `scripts/odoo_spike.py` (transports: `json2`, `xmlrpc`)

## Results

| Step | Works? | Notes |
|---|---|---|
| Install `account`, `purchase`, `stock`, `l10n_es` | ✅ | ~15 s once the database exists |
| Spanish chart of accounts | ✅ **with a catch** | Installing `account` before the company has a country silently loads the **generic chart in USD**. Set country + currency on `res.company` **first**, then install the accounting modules: `es_pymes` then loads automatically (646 accounts, EUR, Spanish VAT set including intra-EU `21% EU G`). |
| Create vendor with Spanish VAT | ✅ | `res.partner` with `vat="ESB46234563"` |
| Create + confirm purchase order | ✅ | `purchase.order` + `button_confirm` |
| Validate goods receipt | ✅ | `stock.picking` reaches `done`. Each `stock.move` needs `quantity` and `picked=True` written first; `button_validate` then returns `True` instead of a wizard action. |
| Draft vendor bill with account + 21% tax | ✅ | `account.move` `move_type="in_invoice"` stays in `state="draft"`; totals 378.00 / 79.38 / 457.38 as expected |
| Link bill line to PO line | ✅ | `purchase_line_id` on `account.move.line` |
| Find bill by vendor + ref (idempotency) | ✅ | `search_read` on `move_type`, `partner_id`, `ref` — this is what makes `create_draft_bill` safe to retry |
| JSON-2 transport (`/json/2/<model>/<method>`) | ⏳ pending | Needs an API key, which can only be created from the UI (Preferences → Account Security → New API Key). The script already speaks it; only the key is missing. |

## Decision

- [x] **Go:** implement `OdooErp` in week 3. Every model mapping the design assumed is real and reachable over RPC.
- Transport: prefer **JSON-2** (bearer API key, the documented path in 19+). XML-RPC stays as the fallback and is what these results were produced with; Odoo has it scheduled for removal in v22.
- Access to the external API is *not* gated for self-hosted Community; the "Custom plan only" note in Odoo's docs applies to Odoo Online.

## Gotchas worth remembering

1. **Country before accounting.** Otherwise you get `generic_coa` in USD and, once entries exist, the chart cannot be swapped — the database has to be rebuilt.
2. `account.chart.template` is not readable over RPC (no group grants it), so the chart cannot be chosen after the fact from a script; it is driven by the company's country.
3. Product `type="consu"` plus `is_storable=True` is what produces a receipt to validate in 19.
