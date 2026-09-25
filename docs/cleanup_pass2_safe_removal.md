# Cleanup Pass 2 — Safe Removal / Merge

Status: COMPLETE

## Changes

### 1. Repeated-header Bupot parser merged into active importer

Moved the repeated-header block selection logic into:

- `core/worksheet_workbook_importer.py`

The base importer now:
- detects duplicate/repeated Bupot header blocks;
- selects the block that actually contains data;
- keeps optional PPh column detection scoped to the selected block;
- preserves the old repeated-header regression behavior.

Removed:
- `core/worksheet_workbook_importer_repeated_headers.py`

Updated:
- `tests/test_worksheet_workbook_repeated_headers.py` now tests the active base importer directly.

### 2. Obsolete redraw PDF renderer removed

Removed:
- `core/legacy_pdf_exporter.py`

Reason:
- Finalization production does not use this renderer;
- production PDF flow uses `Legacy1770StaticPdfService` / Hybrid flow;
- old renderer existed only for historical test coverage.

Updated:
- `tests/test_legacy_1770.py` keeps document/domain mapping tests;
- obsolete tests that instantiated the old redraw renderer were removed;
- current Static/Hybrid PDF suites remain the authoritative PDF coverage.

## Not changed

The following layered production chains remain intact:
- WorksheetArchiveExporter -> Styled -> Polished
- Legacy multipage base -> fine-tuned -> final
- Induk/Lampiran fine-tuned renderers
- state-key compatibility helper
- developer/debug scripts

## Required validation

Run targeted cleanup regression first:

```powershell
python -m pytest `
  tests/test_worksheet_workbook_importer.py `
  tests/test_worksheet_workbook_repeated_headers.py `
  tests/test_legacy_1770.py `
  tests/test_legacy_1770_static_pdf.py `
  tests/test_legacy_1770_hybrid_pdf.py `
  -q
```

Then run the full Stage 8E regression before packaging.
