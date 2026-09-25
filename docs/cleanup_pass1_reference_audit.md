# Cleanup Pass 1 — Reference Audit

Status: COMPLETE
Scope: reference audit only. Tidak ada file production yang dihapus pada pass ini.

## Tujuan

Membedakan file yang:
- aktif dipakai production;
- aktif sebagai inheritance/compatibility layer;
- hanya dipakai test/legacy verification;
- hanya utility developer/debug;
- kandidat aman untuk cleanup pada pass berikutnya.

## KEEP — Production / Runtime

### Worksheet archive exporter chain
- `core/worksheet_archive_exporter.py`
- `core/worksheet_archive_exporter_styled.py`
- `core/worksheet_archive_exporter_polished.py`

Alasan:
UI `ui/worksheet_export_actions.py` memakai `PolishedWorksheetArchiveExporter`.
Polished mewarisi Styled, dan Styled mewarisi base exporter.
Bukan duplikasi bebas; ini inheritance chain aktif.

### Legacy 1770 PDF production chain
- `core/legacy_1770_static_pdf.py`
- `core/legacy_1770_multipage.py`
- `core/legacy_1770_multipage_finetuned.py`
- `core/legacy_1770_multipage_final.py`
- `core/legacy_1770_induk.py`
- `core/legacy_1770_induk_finetuned.py`
- `core/legacy_1770_lampiran_i.py`
- `core/legacy_1770_lampiran_i_finetuned.py`
- `core/legacy_1770_lampiran_ii.py`
- `core/legacy_1770_lampiran_ii_finetuned.py`
- `core/legacy_1770_lampiran_iii.py`
- `core/legacy_1770_lampiran_iv.py`

Alasan:
`Legacy1770StaticPdfService` memakai `legacy_1770_multipage_final`.
Final multipage masih bergantung pada fine-tuned dan base multipage.
Fine-tuned multipage masih memakai renderer fine-tuned Lampiran I/II.
Menghapus salah satu layer sekarang akan memutus runtime PDF final.

### Active Worksheet input chain
- `core/worksheet_workbook_importer.py`
- `core/worksheet_workbook_generic.py`
- `core/selectable_worksheet_importer.py`
- `core/three_sheet_worksheet_importer.py`

Alasan:
`ui/pages/input_data_page.py` memakai `ThreeSheetWorksheetWorkbookImporter`.
ThreeSheet -> Selectable -> Generic/base importer.

### Compatibility state
- `core/state_key_migration.py`

Alasan:
Masih mempunyai regression test untuk membaca key state historis.
Jangan dihapus sebelum migration compatibility sengaja dihentikan.

## LEGACY / TEST-ONLY CANDIDATE

### `core/legacy_pdf_exporter.py`

Temuan:
- tidak dipakai jalur Finalization production saat ini;
- production memakai `Legacy1770StaticPdfService`;
- masih dipakai oleh `tests/test_legacy_1770.py` untuk renderer PDF lama.

Klasifikasi: `LEGACY_TEST_ONLY`

Keputusan Pass 1:
KEEP sementara.
Pada Pass 2 kita dapat memisahkan test lama atau menghapus renderer ini bila coverage yang sama sudah dijamin oleh Hybrid/Static PDF tests.

### `core/worksheet_workbook_importer_repeated_headers.py`

Temuan:
- subclass khusus parser Bupot dengan repeated header;
- production input utama sekarang memakai ThreeSheet/Selectable importer;
- Kertas Kerja bahkan tidak lagi menjadi sumber Bupot utama pada `SelectableWorksheetWorkbookImporter.parse_selected()`;
- file masih dipakai oleh `tests/test_worksheet_workbook_repeated_headers.py`.

Klasifikasi: `LEGACY_TEST_ONLY / COMPATIBILITY_CANDIDATE`

Keputusan Pass 1:
KEEP sementara sampai test compatibility diputuskan tetap diperlukan atau dihapus.

## DEBUG / DEVELOPER UTILITY

Kandidat utility non-runtime:
- `scripts/debug_1770_ptkp_coordinates.py`
- `scripts/debug_1770_ptkp_coordinates_v2.py`
- `inspect_coretax_exports.py`
- `inspect_coretax_rules.py`
- berbagai `scripts/export_*_test.py` dan visual/UAT helper

Klasifikasi: `DEV_UTILITY`

Keputusan Pass 1:
Tidak dihapus. Utility seperti ini tidak menambah beban runtime dan berguna bila perlu kalibrasi/export diagnosis lagi.
Pass 2 boleh memindahkan utility historis ke folder `scripts/archive/` bila ingin root lebih bersih.

## NOT DUPLICATE — Intentional Layering

File berikut tampak mirip tetapi sengaja merupakan layer:
- base -> styled -> polished Worksheet exporter;
- base -> fine-tuned -> final Legacy 1770 multipage;
- base -> fine-tuned Induk/Lampiran renderer.

Jangan merge sebelum Final UAT/packaging. Refactor inheritance sekarang mempunyai risiko regression visual yang lebih besar daripada benefit cleanup.

## Repository hygiene

Tidak ditemukan file cache/temporary yang terlacak:
- `__pycache__`
- `*.pyc`
- `*.pyo`
- `*.bak`
- `*.tmp`
- `*.old`

## Kandidat Pass 2

Prioritas cleanup berikutnya:

1. `core/legacy_pdf_exporter.py`
   - tentukan apakah test lama masih bernilai;
   - bila tidak, hapus renderer + test khususnya.

2. `core/worksheet_workbook_importer_repeated_headers.py`
   - tentukan apakah compatibility repeated-header masih menjadi requirement nyata;
   - bila tidak, hapus subclass + test.
   - bila masih perlu, merge behavior ke importer aktif lalu hapus subclass khusus.

3. Developer scripts
   - jangan delete agresif;
   - cukup archive/kelompokkan setelah production code selesai.

## Kesimpulan Pass 1

Tidak ditemukan fungsi/file production aktif yang aman untuk langsung dihapus tanpa keputusan compatibility.
Duplikasi terbesar yang terlihat ternyata merupakan inheritance layering aktif.
Dua kandidat cleanup nyata adalah:
- legacy PDF renderer lama;
- repeated-header importer khusus.

Pass 1 sengaja tidak menghapus file agar baseline hijau Stage 8E.4 tetap terjaga.
