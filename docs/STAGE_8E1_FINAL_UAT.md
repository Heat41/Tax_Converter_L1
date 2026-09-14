# Stage 8E.1 - Final UAT / Deployment Readiness

Tujuan tahap ini adalah memastikan alur produksi utama tetap konsisten sebelum aplikasi dipaketkan untuk penggunaan kantor.

## Prinsip

- UAT membaca snapshot FINAL aktif.
- Data tetap sparse/data-driven.
- Kategori kosong tidak dipaksa dibuat.
- Nilai yang tidak tersedia tidak boleh dibuat-buat.
- UAT tidak menulis ke `export_audit_log`.
- Riwayat export operasional tetap hanya berasal dari tombol Export di UI.

## Checkpoint otomatis

1. `UAT_01` - Snapshot FINAL dapat dibaca dan direverse-map.
2. `UAT_02` - Format Lama 1770 berhasil dibuat sebagai PDF statis.
3. `UAT_03` - Paket Coretax berhasil dibuat.
4. `UAT_04` - Paket Coretax lolos validator.
5. `UAT_05` - Rekonsiliasi fisik source vs export.
   - PASS bila `--source-dir` diberikan dan cocok.
   - SKIPPED bila source tidak diberikan.

Semua checkpoint wajib PASS atau SKIPPED agar UAT dianggap PASS.

## Menjalankan UAT WP nyata

Contoh PowerShell:

```powershell
python scripts/uat_final_release.py 6101015612710001 2025 `
  --template-dir "D:\Template_Coretax" `
  --source-dir "C:\Users\ASUS260922\Downloads\harta"
```

Output default:

```text
output/
  uat_6101015612710001_2025/
    1770_format_lama_6101015612710001_2025_rev<N>.pdf
    coretax_package/
      excel/
      xml/
      manifest.json
    uat_report.json
```

## Verifikasi manual setelah PASS

Setelah runner PASS:

- buka PDF Format Lama dan cek identitas, Bupot, Harta, serta jumlah halaman;
- buka Preview Paket Coretax dan cocokkan kategori aktif/jumlah baris;
- pastikan file Excel hanya ada untuk kategori aktif;
- pastikan XML hanya ada pada kategori yang memiliki schema resmi;
- pastikan tidak ada nilai yang muncul jika sumber aslinya kosong;
- jalankan full regression `python -m pytest -q`.

Setelah seluruh poin di atas selesai, Stage 8E.1 dapat ditutup dan dilanjutkan ke packaging/deployment desktop.
