# Eval report — google_genai:gemini-3.6-flash

- Cases: 10 · extraction errors: 3
- All critical fields correct: 70.0%
- Overall detection: precision 100.0%, recall 50.0%
- LLM calls: 0 · time: 0.0 s

## Extraction accuracy by field

| Field | Accuracy |
|---|---|
| invoice_number | 70.0% |
| issue_date | 70.0% |
| issuer_tax_id | 70.0% |
| recipient_tax_id | 70.0% |
| subtotal | 70.0% |
| vat_total | 70.0% |
| irpf_amount | 70.0% |
| total | 70.0% |

## Exception detection by code

| Code | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| INVALID_TAX_ID | 0 | 0 | 1 | n/a | 0.0% |
| LINE_TOTAL_MISMATCH | 1 | 0 | 0 | 100.0% | 100.0% |
| MISSING_FIELD | 1 | 0 | 0 | 100.0% | 100.0% |
| TOTAL_MISMATCH | 1 | 0 | 0 | 100.0% | 100.0% |
| VAT_AMOUNT_MISMATCH | 0 | 0 | 1 | n/a | 0.0% |
| WRONG_RECIPIENT | 0 | 0 | 1 | n/a | 0.0% |

## Cases

| Case | Error | Wrong fields | Expected codes | Predicted codes |
|---|---|---|---|---|
| G001 | — | — | — | — |
| G002 | — | — | — | — |
| G003 | — | — | — | — |
| G004 | — | — | — | — |
| G005 | — | — | TOTAL_MISMATCH | TOTAL_MISMATCH |
| G006 | — | — | LINE_TOTAL_MISMATCH | LINE_TOTAL_MISMATCH |
| G007 | LLM_ERROR: Error calling model 'gemini-3.6-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash\nPlease retry in 10.272655788s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-3.6-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '10s'}]}} | invoice_number (LB-2026-0098→None), issue_date (2026-09-10→None), issuer_tax_id (B29444339→None), recipient_tax_id (B46123451→None), subtotal (420.00→None), vat_total (88.20→None), irpf_amount (0.00→None), total (508.20→None) | INVALID_TAX_ID | — |
| G008 | — | — | MISSING_FIELD | MISSING_FIELD |
| G009 | LLM_ERROR: Error calling model 'gemini-3.6-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash\nPlease retry in 52.41016981s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-3.6-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '52s'}]}} | invoice_number (TH-2026-5521→None), issue_date (2026-09-12→None), issuer_tax_id (B46234563→None), recipient_tax_id (B12345674→None), subtotal (378.00→None), vat_total (79.38→None), irpf_amount (0.00→None), total (457.38→None) | WRONG_RECIPIENT | — |
| G010 | LLM_ERROR: Error calling model 'gemini-3.6-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash\nPlease retry in 34.070410605s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-3.6-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '34s'}]}} | invoice_number (TH-2026-5540→None), issue_date (2026-09-14→None), issuer_tax_id (B46234563→None), recipient_tax_id (B46123451→None), subtotal (380.00→None), vat_total (76.00→None), irpf_amount (0.00→None), total (456.00→None) | VAT_AMOUNT_MISMATCH | — |
