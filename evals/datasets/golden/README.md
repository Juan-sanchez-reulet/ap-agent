# Golden cases

Ten hand-authored invoice cases: four clean ones (single VAT rate, two VAT rates,
freelancer with 15% IRPF, rent with 19% IRPF) and six traps (wrong total, wrong line
total, invalid CIF check digit, missing invoice number, wrong recipient, wrong VAT
amount on an English template).

- `expected.json` is the ground truth: the values **as printed**, including the
  deliberate errors, plus the issue codes the validators must raise.
- `invoice.pdf` is rendered by `scripts/make_golden_pdfs.py` in one of four layouts
  (classic, modern, plain, english) so extraction is not tuned to a single template.

**Known limitation.** Both the ground truth and the layouts are ours, so this set cannot
prove the extractor generalises to real-world layouts. Week 2 adds invoices built outside
this repo (word-processor templates, online invoice generators) and a real-document
extraction benchmark; those keep the same `expected.json` format with
`"source": "manual_template"` or `"own_invoice"`.

`tests/evals/test_golden_consistency.py` re-runs the validators over every `expected.json`,
so a mislabelled case fails the build instead of quietly corrupting the metrics.
