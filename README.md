# AP Agent — accounts-payable exception handling with deterministic controls

[![CI](https://github.com/Juan-sanchez-reulet/ap-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Juan-sanchez-reulet/ap-agent/actions/workflows/ci.yml)

Supplier invoices arrive as PDFs. An LLM reads them, **deterministic accounting and tax
controls decide whether they can be trusted**, and anything doubtful is held for a human
with a diagnosis attached. Clean invoices become **draft** vendor bills in Odoo — never
posted entries — so the ERP stays the system of record.

Reading an invoice is a commodity; every ERP does OCR now. The interesting problem is the
other one: **never letting a bad invoice reach the ledger, and proving it with numbers.**
That is why the evaluation harness was built before the agent.

> **Status: week 1 of 4 — the deterministic core and the eval harness are done and
> measured; the LangGraph orchestration, the human review queue and the live Odoo
> integration are next.** See [Roadmap](#roadmap). Every number below comes from a real
> run, reproducible with the commands in [Quickstart](#quickstart).

## What it does today

```
invoice.pdf
   │
   ├─ read text layer ................................ pdfplumber (scanned PDFs are detected, not guessed at)
   ├─ extract fields ................................. Gemini, structured output, 1 retry, disk cache
   │     └─ prompt rule: transcribe literally, never "fix" a wrong total
   ├─ validate (no LLM, no network, deterministic) .... arithmetic · Spanish invoicing rules · NIF/NIE/CIF checksums
   └─ report ......................................... per-field accuracy, detection precision/recall
```

An extraction is never trusted on its own: it is only ever *input* to code that checks it.

## Evaluation results

Ten hand-authored invoice cases: four clean (one and two VAT rates, 15% IRPF withholding
for a freelancer, 19% for rent) and six with a deliberate error, rendered across four
different layouts, one of them in English.

| | Result |
|---|---|
| Model | `gemini-3.5-flash-lite` (free tier) |
| Critical fields correct (8 fields × 10 invoices) | **100%** |
| Exception detection | **precision 100%, recall 100%** |
| False alarms on clean invoices | **0** |
| Cost / latency | 1 LLM call and ~18 s per invoice |

Detected, one case each: total that does not equal base + VAT − withholding, line total
that does not equal quantity × price, CIF with an invalid check digit, missing invoice
number, invoice addressed to another company, VAT amount that does not match its base.

**How to read that 100%.** It shows the pipeline works end to end and that the literal
transcription rule holds — the model copies a wrong total instead of silently correcting
it, which is what makes the error detectable at all. It does **not** show the extractor
generalises: ten cases, layouts authored in this repo, no scans. Week 2 adds invoices
built outside the repo and a real-document benchmark. Full report:
[`evals/results/`](evals/results).

Two decisions behind the harness are worth more than the score:

- **A quota error is not a failure.** A 429 from the model means a case was *not measured*;
  counting those as wrong understated accuracy at 70% and recall at 50% in the first run.
  The report separates measured from skipped cases, and a test locks that behaviour.
- **The ground truth is itself tested.** Every `expected.json` is re-run through the
  validators in CI, so a mislabelled case breaks the build instead of quietly corrupting
  the metrics.

## Design

The agent being built is a **deterministic workflow with a bounded agent only where the
problem is open-ended** — the split argued in Anthropic's "Building effective agents".

```
ingest → extract → validate → match_po → assign_accounts → route
   ▲                                                         │
   │                 ┌───────────────────────────────────────┼──────────────────┐
   │                 ▼                                       ▼                  ▼
   │          investigate (blockers)              human_review (warnings,   create_draft_bill
   │          [read-only tools, 6 steps]          low confidence, >1000 €)   (clean)
   └── human edits ──┴──────────────► [interrupt] ─── approve ──────────────────┘
```

Four rules shape the code:

1. **The LLM proposes; code decides.** Every model output is schema-validated and passes
   deterministic controls before it has any effect.
2. **One writer.** Only `create_draft_bill` holds an `ErpWriter`; the investigator gets an
   `ErpReader` only — enforced by types, not by prompt wording.
3. **Drafts only.** The agent never posts or confirms a bill.
4. **Everything external is swappable**: `ErpReader`/`ErpWriter` protocols, and chat models
   behind `init_chat_model`, so tests and evals run offline with fakes and cached responses.

Full spec: [`docs/design/ap-agent-v1-design.md`](docs/design/ap-agent-v1-design.md).

### ERP integration

Verified against **Odoo 19 Community** (self-hosted, `docker-compose.yml`) over both the
JSON-2 API and legacy XML-RPC: vendor → confirmed purchase order → validated goods receipt
→ PO-linked **draft** vendor bill (378.00 + 79.38 = 457.38 €) → lookup by vendor + invoice
reference, which is what makes draft creation idempotent under retries. Findings and the
traps that cost time — installing accounting before the company has a country silently
loads a generic USD chart — are in
[`docs/spikes/2026-09-odoo-json2.md`](docs/spikes/2026-09-odoo-json2.md).

## Quickstart

```bash
uv sync                      # Python 3.12 toolchain and dependencies
cp .env.example .env         # then add a free Gemini API key from aistudio.google.com
uv run pytest -q             # 97 tests, no API key and no network needed
```

Run the evaluation over the golden set (~10 LLM calls, free tier, results cached):

```bash
uv run python -m evals.run --cases evals/datasets/golden
```

Optional — the local ERP used by the integration spike:

```bash
docker compose up -d
uv run python -m scripts.odoo_spike --transport xmlrpc
```

## Layout

```
src/apagent/
  domain/       Invoice, LineItem, TaxLine, Issue, Vendor, Account  (Decimal money, no floats)
  validation/   tax_id · arithmetic · formal — pure functions, offline, behind validate_invoice()
  extraction/   pdf (text-layer detection) · schema (LLM-facing types + conversion) · extractor
  llm.py        provider-agnostic chat model with rate limiting
  cache.py      content-hashed disk cache; doubles as recorded responses for CI
  world.py      the fictional company's master data
evals/          golden dataset, metrics, runner, markdown reports
docs/           design spec, integration spike
```

## Testing

97 tests, all offline: table-driven validator tests, `hypothesis` property tests asserting
the arithmetic checks never fire on a correctly computed invoice, scripted fake chat models
that assert the retry carries the validation error back to the model, PDF fixtures generated
at test time, and the ground-truth consistency check described above. CI runs ruff, `mypy
--strict`, and the suite on every push.

## Limitations

- Scanned invoices are detected and rejected, not read yet (multimodal path: week 2).
- The golden set is small and its layouts are self-made; see the caveat above.
- Single tenant, no authentication — it runs locally.
- Spain only: Spanish VAT rates, IRPF withholding and the PGC chart of accounts.
- Free-tier model quotas are tight (`gemini-3.6-flash` allows 20 requests/day), so large
  eval runs are spread across models and run overnight.

## Roadmap

- **Week 2** — LangGraph orchestration, `FakeErp`, PO/receipt matching, account assignment,
  duplicate and changed-IBAN controls, FastAPI, multimodal path for scans.
- **Week 3** — bounded exception investigator with read-only tools, review queue UI,
  `OdooErp` over JSON-2 with contract tests shared with `FakeErp`.
- **Week 4** — eval iteration with before/after numbers, real-document extraction
  benchmark, adversarial control tests, recorded demo.
