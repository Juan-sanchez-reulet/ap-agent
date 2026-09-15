# AP Agent — Design Spec (v1)

- **Status:** Draft for review
- **Date:** 2026-09-15
- **Author:** Juan Sánchez Reulet
- **Target v1 date:** 2026-10-13

---

## 1. Summary

AP Agent is an accounts-payable exception-handling agent for a fictional Spanish SMB. It takes supplier invoices (PDF), extracts their data, runs deterministic accounting and fiscal controls, matches them against purchase orders and goods receipts, proposes ledger accounts, investigates exceptions with a bounded read-only agent, routes anything doubtful to a human review queue, and creates **draft** vendor bills in Odoo.

**Positioning.** Reading invoices is a commodity — ERPs like Odoo already offer PDF upload, email intake and PO matching. The differentiator is **exception management with controls and traceability**: every invoice either reaches the ERP as a correct draft or is held with a diagnosis a human can act on, and every decision is auditable. The project's headline claim is *measured reliability*, backed by evals.

## 2. Goals and non-goals

### Goals (v1)
1. End-to-end flow: PDF → extraction → validation → PO/receipt match → account assignment → routing → (investigation) → (human review) → draft vendor bill in the ERP.
2. Deterministic controls that the LLM cannot bypass.
3. A bounded, read-only exception investigator that produces evidence-backed recommendations.
4. A web review queue for held invoices.
5. An evaluation harness with human-verified golden cases, synthetic scale-up and honest metrics.
6. Runs entirely at **$0**.

### Non-goals (v1)
- Bank reconciliation, month-end close, financial reporting.
- Email intake (Mailpit), Slack notifications.
- Confirming/posting bills in the ERP (the agent only creates drafts).
- Creating vendors from the agent.
- Multi-user, authentication, multi-tenancy (single-tenant local demo; documented limitation).
- Local models (Ollama) — possible later.
- Non-Spanish jurisdictions.

## 3. Constraints

| Constraint | Implication |
|---|---|
| Budget $0 | Gemini API free tier (AI Studio, Flash models) as default LLM; self-hosted open-source infra; free GitHub Actions on a public repo. |
| Gemini free tier: ~10–15 RPM (per-project, unpublished), possible daily caps, inputs may be used for training | Rate limiter + LLM response cache; **only synthetic/public data** is ever sent to the free tier. |
| Hardware: Apple M4, 16 GB RAM | Don't run every container at once; Odoo only when needed. |
| Time: ~20 h/week, 4 weeks | Strict scope; defined cut order (§15). |

## 4. Architecture

### 4.1 Stack
- **Backend:** Python 3.12, `uv`, Pydantic v2, FastAPI.
- **Orchestration:** LangGraph with Postgres checkpointer.
- **LLM layer:** LangChain chat models via `init_chat_model` (`langchain-google-genai`), `with_structured_output`, `bind_tools`, `set_llm_cache`; `GenericFakeChatModel` in tests.
- **ERP:** Odoo 19 Community (self-hosted, Docker) with `account`, `purchase`, `stock`, `l10n_es`.
- **Frontend:** Next.js (review queue).
- **Tracing:** LangSmith free developer tier (fallback: Arize Phoenix, local).
- **Infra:** Docker Compose (Postgres, Odoo).

### 4.2 Repository layout
```
ap-agent/
├── backend/apagent/
│   ├── domain/        # Pydantic models: Invoice, LineItem, Vendor, PurchaseOrder, GoodsReceipt, Issue, ...
│   ├── llm.py         # get_chat_model(config): init_chat_model + cache + rate limiter
│   ├── extraction/    # PDF → text/image → Invoice
│   ├── validation/    # Pure, offline validators → list[Issue]
│   ├── matching/      # Invoice ↔ PO ↔ goods receipt (deterministic)
│   ├── accounts/      # Account assignment per line
│   ├── erp/           # ErpReader / ErpWriter protocols, fake.py, odoo.py
│   ├── graph/         # Main graph, investigator subgraph, InvoiceState, routing policy
│   ├── api/           # FastAPI app
│   └── config.py      # pydantic-settings
├── backend/tests/
├── web/               # Next.js review queue
├── evals/             # world generator, case generator, templates, degrader, datasets, runner, results
├── docs/adr/          # Architecture Decision Records
└── docker-compose.yml
```

### 4.3 Design rules
1. **The LLM proposes; code decides.** Every LLM output is schema-validated and passes deterministic controls before it has any effect.
2. **One writer.** Only the `create_draft_bill` node holds an `ErpWriter`, and only after validation or human approval. The investigator receives an `ErpReader` only — enforced by types, not prompts.
3. **Drafts only.** The agent never confirms or posts a bill; Odoo stays the system of record and an accountant confirms drafts there.
4. **Everything external is swappable.** `ErpReader`/`ErpWriter` protocols and chat models behind `init_chat_model`. Tests and evals run on `FakeErp` + fake/cached LLM responses.

## 5. Domain model (key types)

```python
class LineItem:     description, quantity, unit_price, discount_pct, vat_rate, line_total
class Invoice:      invoice_number, issue_date, due_date,
                    issuer_name, issuer_tax_id, issuer_address, issuer_iban,
                    recipient_name, recipient_tax_id,
                    po_reference, currency, lines: list[LineItem],
                    tax_breakdown: list[TaxLine],   # base, rate, amount per VAT rate
                    irpf_rate, irpf_amount, subtotal, vat_total, total,
                    notes, language
class Issue:        code, severity: "blocker" | "warning", field, message, evidence: dict
class MatchResult:  po_id, receipt_ids, status: "matched" | "partial" | "mismatch" | "no_po", line_diffs
class LineCoding:   line_index, account_code, confidence, source: "history" | "rule" | "llm", rationale
class InvestigationReport: findings: list[Finding], inconclusive: bool, tool_calls_used: int
class Finding:      issue_code, finding, evidence_refs: list[str], recommended_action, confidence
class ReviewDecision: decision: "approve" | "edit" | "reject", edits: dict, reason
```

`recommended_action` ∈ {`approve_with_note`, `request_credit_note`, `contact_vendor`, `create_vendor`, `reject_duplicate`, `flag_fraud`}.

## 6. Main graph

```
ingest → extract → validate → match_po → assign_accounts → route
             ▲                                               │
             │        ┌──────────────────────────────────────┼──────────────────────┐
             │        ▼                                      ▼                      ▼
             │   investigate (blockers)            human_review (warnings,     create_draft_bill
             │        └───────────────► human_review   low confidence,          (clean)
             │                          [interrupt]     amount > limit)             │
             └──── edit ────────────────────┤                                       ▼
                                            ├── approve ──► create_draft_bill ──► END (drafted)
                                            └── reject ───────────────────────────► END (rejected)
```

### 6.1 Nodes

| Node | Responsibility | LLM |
|---|---|---|
| `ingest` | SHA-256 of file (skip identical re-uploads), detect text layer, page count; reject corrupt/non-PDF/>20 pages | No |
| `extract` | Text layer → text + LLM; scanned → page images + multimodal LLM. Structured output into `Invoice`. On schema failure: 1 retry with the validation error; then `EXTRACTION_FAILED` blocker | Yes |
| `validate` | Run all validators (§7) → `issues` | No |
| `match_po` | Find PO (by reference, else vendor + amount/date window); compare against goods receipts with tolerances (unit price ±2%, quantities exact) | No |
| `assign_accounts` | Per line: (1) vendor+concept history; (2) policy rules (e.g. IT equipment ≥ capitalisation threshold → 217); (3) LLM constrained to the allowed-accounts enum, with rationale and confidence. VAT (472), IRPF withholding (4751) and vendor/creditor (400/410) lines are always set by code | Sometimes |
| `route` | Code-only routing policy (§6.2) | No |
| `investigate` | Bounded investigator subgraph (§8) | Yes |
| `human_review` | `interrupt()` with full context; resumes with `ReviewDecision`. `edit` goes back to `validate` so human edits are also checked | No |
| `create_draft_bill` | The only ERP write. Idempotent: look up existing bill by vendor + invoice ref before creating; attach PDF | No |

### 6.2 Routing policy (configurable)
1. Any `blocker` issue → `investigate` → `human_review`.
2. Else any `warning`, any `LineCoding.confidence` < 0.8, or `total` > €1,000 (four-eyes control) → `human_review`.
3. Else → `create_draft_bill`.

### 6.3 State (`InvoiceState`)
```python
invoice_id: str
document: DocumentRef              # path, sha256, has_text_layer, page_count
invoice: Invoice | None
vendor: Vendor | None
issues: list[Issue]
po_match: MatchResult | None
account_codings: list[LineCoding]
investigation: InvestigationReport | None
review: ReviewDecision | None
status: "received" | "needs_review" | "drafted" | "rejected" | "failed" | "draft_failed"
erp_bill_id: str | None
error: str | None
audit: list[AuditEvent]            # node, timestamp, summary, inputs/outputs refs
```
Each invoice is one LangGraph thread; state is checkpointed in Postgres so held invoices survive restarts.

### 6.4 Company policy (config)
- Auto-draft limit: €1,000.
- Capitalisation threshold: €300 per item (below → expense).
- Allowed accounts (v1): 600, 602, 621, 622, 623, 624, 625, 626, 627, 628, 629, 206, 216, 217; system-set: 400, 410, 472, 4751.

## 7. Validators

Pure functions `(invoice, context) -> list[Issue]`; no LLM, no network; deterministic.

| Group | Check | Code (examples) | Severity |
|---|---|---|---|
| Arithmetic | qty × price × (1 − discount) = line total; Σ lines = subtotal; base × rate = VAT per rate; subtotal + VAT − IRPF = total (tolerance €0.01) | `LINE_TOTAL_MISMATCH`, `TOTAL_MISMATCH` | blocker |
| Formal (Spanish invoicing rules) | Missing invoice number, date, issuer/recipient tax ID, or base/rate/amount breakdown; invalid NIF/CIF check digit; recipient is not our company | `MISSING_FIELD`, `INVALID_TAX_ID`, `WRONG_RECIPIENT` | blocker |
| Fiscal | VAT rate ∉ {21, 10, 4, 0}; IRPF rate inconsistent with vendor type (15% professionals, 19% rentals); EU vendor with 0% VAT and no reverse-charge mention | `INVALID_VAT_RATE`, `IRPF_MISMATCH`, `REVERSE_CHARGE_MENTION_MISSING` | blocker / warning |
| Vendor | Vendor not in ERP; IBAN differs from vendor master | `UNKNOWN_VENDOR`, `IBAN_CHANGED` | blocker |
| Duplicates | Same vendor + invoice number already exists → blocker; same vendor + amount + date, different number → warning | `DUPLICATE_INVOICE`, `POSSIBLE_DUPLICATE` | blocker / warning |
| Plausibility | Issue date in the future or > 365 days old; total > 3× vendor's historical mean | `DATE_OUT_OF_RANGE`, `AMOUNT_ANOMALY` | warning |
| Matching (from `match_po`) | PO required but missing; price/quantity outside tolerance; invoiced qty > received qty | `PO_MISSING`, `PRICE_MISMATCH`, `QTY_EXCEEDS_RECEIPT` | blocker / warning |

VIES VAT-number verification requires network access, so it is an investigator tool, not a validator.

## 8. Exception investigator (subgraph)

- **Trigger:** at least one blocker.
- **Goal:** turn "doesn't match" into a diagnosis with evidence and a recommended action.
- **Loop:** LLM with `bind_tools` → `ToolNode` → LLM …; **max 6 tool calls**; on budget exhaustion return `inconclusive=True`.
- **Tools (read-only, backed by `ErpReader` or external lookups):**
  - `search_vendors(query)` — fuzzy name/tax-ID search (aliases)
  - `get_vendor_history(vendor_id, limit)` — past bills, amounts, IBANs, accounts
  - `find_purchase_orders(vendor_id, amount_range, date_range)`
  - `get_goods_receipts(po_id)` — partial deliveries
  - `find_similar_invoices(vendor_id, amount, date_range)` — duplicates
  - `check_vat_vies(vat_number)` — EU VIES lookup (mocked in tests/evals)
- **Output:** structured `InvestigationReport` (§5).
- **Guardrails:**
  1. Investigator holds `ErpReader` only (type-level).
  2. Every `evidence_ref` must reference an actual tool result ID from this run; unknown refs are dropped and confidence is lowered.
  3. `recommended_action` is an enum without any "post/draft" option — only a human approves.

## 9. ERP integration

### 9.1 Interfaces
```python
class ErpReader(Protocol):
    def get_company(self) -> Company: ...
    def get_vendor(self, vendor_id: str) -> Vendor | None: ...
    def search_vendors(self, query: str) -> list[Vendor]: ...
    def get_vendor_history(self, vendor_id: str, limit: int) -> list[PostedBill]: ...
    def find_purchase_orders(self, vendor_id: str, amount_range, date_range) -> list[PurchaseOrder]: ...
    def get_goods_receipts(self, po_id: str) -> list[GoodsReceipt]: ...
    def find_bills(self, vendor_id: str, ref: str | None = None,
                   amount: Decimal | None = None, date_range=None) -> list[PostedBill]: ...
    def list_allowed_accounts(self) -> list[Account]: ...

class ErpWriter(Protocol):
    def create_draft_bill(self, draft: BillDraft, idempotency_key: str) -> str: ...
    def attach_document(self, bill_id: str, filename: str, pdf: bytes) -> None: ...
```

### 9.2 Single source of truth: `world.json`
Describes the fictional company: vendors (tax IDs, IBANs, vendor type, requires-PO flag, aliases), purchase orders, goods receipts, bill history, allowed accounts. Consumed by `FakeErp`, the Odoo seed script and the synthetic case generator. Generated with a fixed seed.

### 9.3 Implementations
- **`FakeErp`:** in-memory, loaded from `world.json`. Used by unit/graph tests and evals.
- **`OdooErp`:** Odoo 19 Community via the External JSON-2 API (`/json/2/<model>/<method>`, bearer API key). Mapping: vendors → `res.partner` (+ `res.partner.bank`), POs → `purchase.order`, receipts → `stock.picking`, drafts → `account.move` (`move_type="in_invoice"`, `state="draft"`, `ref` = vendor invoice number).
- **Contract tests:** one test suite parameterised over both implementations; Odoo runs are marked `integration` and executed locally / via manual CI workflow.

### 9.4 Week-1 spike (timeboxed: 4 h)
Install Odoo 19 Community in Docker with `account`, `purchase`, `stock`, `l10n_es`; create an API key; via JSON-2: create a vendor, a PO, a receipt, and a draft vendor bill linked to the PO lines; read it back.
- **Success:** all steps work from a Python script.
- **Fallback A:** legacy JSON-RPC (deprecated, removal scheduled for Odoo 22).
- **Fallback B:** ship v1 with `FakeErp` only and document Odoo as next step.

Note: bank reconciliation and full financial reports are not in Odoo Community's Invoicing app (Enterprise or OCA modules); they are out of scope anyway.

## 10. API (FastAPI)

| Method | Path | Behaviour |
|---|---|---|
| POST | `/invoices` | Upload PDF; create thread; enqueue graph run → `202 {invoice_id}` |
| GET | `/invoices?status=` | Queue listing |
| GET | `/invoices/{id}` | Full state: invoice, issues, match, codings, investigation, audit |
| GET | `/invoices/{id}/document` | PDF bytes |
| POST | `/invoices/{id}/review` | `{decision, edits, reason}` → resume via `Command(resume=...)` |
| POST | `/invoices/{id}/retry` | Resume a `failed` / `draft_failed` thread from its last checkpoint |
| GET | `/stats` | Counts by status, straight-through rate, top issue codes |

Execution: in-process worker queue, concurrency 1–2, LangChain `InMemoryRateLimiter` sized to the Gemini free-tier limit. On startup, threads left mid-run are resumed.

## 11. Review queue (Next.js)

1. **Inbox:** table (vendor, invoice number, total, status, top issue, age), status filters, upload button.
2. **Review:** PDF viewer (left); right column: editable extracted fields with per-field issue badges; investigator report (findings, evidence, recommended action); per-line account table (dropdown restricted to allowed accounts, confidence); actions **Approve**, **Save & revalidate**, **Reject (reason)**; audit timeline.
3. **Summary:** processed, straight-through %, in review, drafted; most frequent issue codes. *(First item cut if behind schedule.)*

## 12. Evaluation

### 12.1 Datasets

| Set | Size | Built how | Measures | Role |
|---|---|---|---|---|
| **Golden** | 30–50 | Invoices built **outside our generator** (Word/Google Docs templates, free online invoice generators) using `world.json` vendors/POs (**at least half of the set**), plus hand-verified synthetic cases. **Ground truth written by a human reading the PDF.** Mix of layouts, languages, native and scanned, clean and exceptions | Full pipeline | Primary test set; built first |
| **Synthetic** | ~200 | Case generator → ground-truth JSON → 6 HTML templates (Jinja2) → PDF (WeasyPrint) → degrader (~30%: rasterise, 1–3° rotation, noise, JPEG, low DPI) | Full pipeline at scale, per-trap breakdowns | Dev iteration; scale-up after golden |
| **Real extraction** | ~50 | DocILE subset (fields overlapping ours), subject to licence/access; optional 15–20 of the author's own received invoices, anonymised | Extraction only | Reality check |

Synthetic split: ~140 dev / ~60 test, and the test split uses **2 templates never seen in dev**. Golden and test sets are only run at milestones.

Only synthetic, self-made and public data is sent to the Gemini free tier.

### 12.2 Trap catalogue
Arithmetic total mismatch · wrong VAT rate · wrong IRPF · invalid NIF/CIF · missing invoice number · exact duplicate re-rendered with another template · near-duplicate · IBAN change (fraud) · "unknown" vendor that is an alias of an existing one · price differs from PO · missing PO when required · partial delivery (invoiced > received) · EU vendor without reverse-charge mention · **legit look-alikes** (e.g. partial invoice matching a partial receipt) that must pass.

Each case's ground truth includes: fields, expected issue codes, expected route, expected accounts per line, expected `recommended_action` (for traps), and whether it **should** reach a draft.

### 12.3 Metrics

| Layer | Metric |
|---|---|
| Extraction | Per-field accuracy (normalised; amounts ±€0.01); % invoices with all critical fields correct; split by native/scanned, language, template |
| Exception detection | Precision and recall per issue type (end-to-end, extraction errors included) |
| Accounts | Line-level account accuracy; capex/opex accuracy |
| **Correct drafts** | % of should-draft invoices that reach a draft with all critical fields and accounts correct |
| **Write-decision matrix** | See below |
| Investigator | `recommended_action` exact-match accuracy; evidence validity rate; mean tool calls; inconclusive rate |
| Operations | LLM calls, tokens and seconds per invoice; estimated cost at paid-tier prices |

**Write-decision matrix** (reported in full, never a single number):

| | Should be drafted | Should be held |
|---|---|---|
| **Agent drafted** | correct draft | **unsafe draft** |
| **Agent held** | unnecessary review | correct hold |

Headline pair: **unsafe-draft rate** and **straight-through rate on clean invoices** — a system that holds everything scores badly on the second.

**Adversarial control tests** (in the test suite, not the LLM eval): attempt invalid writes directly — duplicate drafts, drafting an invoice with open blockers, writes from the investigator, replayed review decisions — and assert they are blocked.

### 12.4 Runner
```bash
uv run evals run --set golden|synthetic-dev|synthetic-test|real-extraction --model <provider:model>
```
- Runs the graph on `FakeErp`; stops at `interrupt` (measures agent behaviour before a human).
- Writes `evals/results/<date>-<git-sha>.json` and `report.md` with tables and diffs vs. the previous run.
- CI: 10-case smoke eval with recorded LLM responses (no API calls).
- Expected full synthetic run: ~500 LLM calls ≈ ~1 h at ~10 RPM; mitigations: cache, per-trap subsets, Flash-Lite for easy nodes, overnight full runs.

## 13. Error handling

| Failure | Behaviour |
|---|---|
| LLM 429 / timeout | Exponential backoff with jitter, honour `retry-after`, max 5 → thread `failed` with error; retry via API/UI from last checkpoint |
| Schema-invalid LLM output | 1 retry with validation error → `EXTRACTION_FAILED` blocker → manual entry in review |
| Investigator budget exhausted | `inconclusive` report → review |
| ERP transient error | Retry with the same idempotency key |
| ERP permanent error | `draft_failed`, visible in queue |
| Bill created, attachment failed | Retry attachment only |
| Corrupt / non-PDF / > 20 pages | Rejected at `ingest` with reason |
| Process crash | Resume in-flight threads on startup |
| Invalid configuration | Fail fast at startup |

Structured JSON logs keyed by `invoice_id`; log IDs and codes, not document contents.

## 14. Testing and CI

- **Unit:** validators (table-driven + `hypothesis` property tests for arithmetic), NIF/CIF checksum, matching tolerances, routing policy, account rules.
- **Node:** `extract`, `assign_accounts` with `GenericFakeChatModel`.
- **Graph:** clean → drafted exactly once; blocker → interrupt; approve → drafted; edit → revalidated; crash/resume without duplicates.
- **Investigator:** scripted tool calls; step cap; fabricated evidence refs dropped; no writer access.
- **Contract:** `ErpReader`/`ErpWriter` suite over `FakeErp` and `OdooErp`.
- **Adversarial control tests:** §12.3.
- **API:** `httpx.AsyncClient`.
- **Web:** Playwright smoke — upload → appears in inbox → review → approve.
- **CI (GitHub Actions, every PR):** `ruff`, `mypy`, `pytest` (Postgres service), `tsc` + `eslint`, smoke eval, Playwright. Odoo contract tests: manual workflow.
- **Process:** small PRs, Conventional Commits, ADRs in `docs/adr/`.

## 15. Plan

| Week | Deliverables | Done when |
|---|---|---|
| 1 (Sep 15–21) | Repo, `uv`, CI skeleton; domain models; `world.json`; `extract` + cache + rate limiter; arithmetic & formal validators; **Odoo spike (4 h)**; request DocILE access; confirm Gemini free-tier limits; **first 10 golden cases**; eval runner v0 | First `report.md` with extraction and detection numbers |
| 2 (Sep 22–28) | `match_po`, `assign_accounts`, `route`, `human_review`, `create_draft_bill` on `FakeErp` + checkpointer; FastAPI; graph + adversarial tests; remaining validators; golden set to 30–50 | Golden baseline end-to-end |
| 3 (Sep 29–Oct 5) | Investigator + tools + guardrails + tests; Next.js review queue; `OdooErp` + seed + contract tests; tracing; synthetic generator to ~200 + degrader + split | Demo: upload → investigate → approve → draft in Odoo |
| 4 (Oct 6–13) | Iterate with evals (log before/after); real-extraction benchmark; test-set runs; Playwright; README (diagram, eval tables, ADRs, limitations); 2-min video; public repo | Public, CV-ready repo |

**Cut order if behind:** summary screen → synthetic scale beyond ~100 → DocILE (keep own invoices) → Odoo (ship `FakeErp`, documented).
**Never cut:** golden set, validators, graph tests, adversarial control tests, write-decision matrix.

## 16. Risks and open questions

| Risk | Mitigation |
|---|---|
| Gemini free-tier limits/daily caps lower than expected or changed | Check in week 1; cache; subsets; `init_chat_model` makes swapping provider a config change |
| Flash extraction accuracy poor on scans | Text-layer path first; validators + review catch errors; report split native/scanned honestly |
| Odoo JSON-2 or PO-linked drafts harder than expected | Timeboxed spike + fallbacks (§9.4) |
| DocILE access/licence | Fall back to own invoices |
| Synthetic set too easy | Golden set built outside the generator; held-out templates |
| Scope creep | Non-goals list; cut order |

## 17. ADRs to write

1. Hybrid architecture: deterministic workflow + bounded agent for exceptions.
2. LangGraph for orchestration, LangChain chat models for LLM access.
3. Drafts-only ERP writes with a single writer node.
4. `FakeErp` + contract tests instead of evaluating against a live ERP.
5. Gemini free tier as default model under a $0 budget.
6. Evaluation design: golden-first, write-decision matrix instead of a single safety number.
