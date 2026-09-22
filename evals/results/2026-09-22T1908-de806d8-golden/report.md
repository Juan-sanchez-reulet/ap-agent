# Eval report — google_genai:gemini-3.5-flash-lite

- Cases: 10 · measured: 10 · not measured (quota/network): 0 · extraction errors: 0
- All critical fields correct: 100.0%
- Overall detection: precision 100.0%, recall 100.0%
- LLM calls: 10 · cache hits: 0 · time: 184.4 s

## Extraction accuracy by field

| Field | Accuracy |
|---|---|
| invoice_number | 100.0% |
| issue_date | 100.0% |
| issuer_tax_id | 100.0% |
| recipient_tax_id | 100.0% |
| subtotal | 100.0% |
| vat_total | 100.0% |
| irpf_amount | 100.0% |
| total | 100.0% |

## Exception detection by code

| Code | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| INVALID_TAX_ID | 1 | 0 | 0 | 100.0% | 100.0% |
| LINE_TOTAL_MISMATCH | 1 | 0 | 0 | 100.0% | 100.0% |
| MISSING_FIELD | 1 | 0 | 0 | 100.0% | 100.0% |
| TOTAL_MISMATCH | 1 | 0 | 0 | 100.0% | 100.0% |
| VAT_AMOUNT_MISMATCH | 1 | 0 | 0 | 100.0% | 100.0% |
| WRONG_RECIPIENT | 1 | 0 | 0 | 100.0% | 100.0% |

## Cases

| Case | Error | Wrong fields | Expected codes | Predicted codes |
|---|---|---|---|---|
| G001 | — | — | — | — |
| G002 | — | — | — | — |
| G003 | — | — | — | — |
| G004 | — | — | — | — |
| G005 | — | — | TOTAL_MISMATCH | TOTAL_MISMATCH |
| G006 | — | — | LINE_TOTAL_MISMATCH | LINE_TOTAL_MISMATCH |
| G007 | — | — | INVALID_TAX_ID | INVALID_TAX_ID |
| G008 | — | — | MISSING_FIELD | MISSING_FIELD |
| G009 | — | — | WRONG_RECIPIENT | WRONG_RECIPIENT |
| G010 | — | — | VAT_AMOUNT_MISMATCH | VAT_AMOUNT_MISMATCH |
