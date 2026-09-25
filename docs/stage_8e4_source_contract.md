# Stage 8E.4A — Coverage Audit & Source Contract

Status: ACTIVE
Tujuan: mengunci sumber data yang boleh dipakai untuk mengisi Form 1770 Hybrid tanpa menebak data pajak.

## Prinsip

1. Renderer hanya boleh mengisi field yang memiliki sumber domain yang eksplisit.
2. Nilai agregat tidak boleh dipecah ke kategori yang lebih spesifik tanpa sumber rinci.
3. Field tanpa sumber tetap kosong/0 dan dicatat sebagai `NO_SOURCE`.
4. Hasil revisi Excel tetap mengikuti canonical + visual round-trip yang sudah distabilkan pada Stage 8E.3.
5. Mapping baru harus mempunyai regression test sebelum dianggap aktif.

## Source Contract

| Form / Bagian | Field | Source saat ini | Status | Aturan |
|---|---|---|---|---|
| Identitas | NPWP, Nama, Tahun Pajak | FinalizationInput | ACTIVE | Gunakan langsung |
| Induk | Penghasilan Neto Pekerjaan | Bupot rows | ACTIVE | Total netto = bruto - pengurang |
| Induk | Penghasilan Neto DN Lainnya | pph_components / pph_calc_result | ACTIVE | Gunakan nilai domain yang tersedia |
| Induk | Penghasilan Neto Usaha non-final | Belum ada domain rinci | NO_SOURCE | Jangan mengambil UMKM final |
| Induk | Kompensasi Kerugian | Belum ada domain | NO_SOURCE | Tetap kosong |
| Induk | Kredit Pajak | pph_components + Bupot | ACTIVE | Gunakan state Worksheet |
| Induk | PPh Pasal 25 | pph_components | ACTIVE | Gunakan state Worksheet |
| Lampiran I H2 Bagian B | Jenis Usaha Dagang/Industri/Jasa | Tidak ada klasifikasi rinci | NO_SOURCE | Jangan membagi agregat |
| Lampiran I H2 Bagian B | Pekerjaan Bebas bruto/DPP | other_income.pekerjaan_bebas_dpp | PARTIAL | Boleh dipakai hanya sebagai Pekerjaan Bebas |
| Lampiran I H2 Bagian B | Norma (%) | Belum ada sumber eksplisit | NO_SOURCE | Jangan dihitung/ditaksir |
| Lampiran I H2 Bagian B | Penghasilan Neto | Belum ada sumber eksplisit | NO_SOURCE | Jangan turunkan dari DPP tanpa Norma |
| Lampiran I H2 Bagian C | Pemberi kerja, bruto, pengurang, netto | Bupot rows | ACTIVE | Netto = bruto - pengurang |
| Lampiran I H2 Bagian D | Penghasilan Neto DN Lainnya | pph_components.penghasilan_neto_lainnya | ACTIVE | Saat ini masuk baris Penghasilan Lainnya |
| Lampiran II | Detail Bupot | Bupot rows | ACTIVE | Total dinamis Excel |
| Lampiran III Bagian A | Final lain-lain rinci | penghasilan_lainnya.final_other_rows | ACTIVE | Klasifikasi hanya dari label yang tersedia |
| Lampiran III Bagian A | UMKM | umkm_state | ACTIVE | Masuk kategori final lain jika kategori lebih rinci tidak tersedia |
| Lampiran III Bagian B | Bukan Objek rinci | Belum ada domain rinci | PARTIAL | Saat ini hanya total agregat ke baris 6 |
| Lampiran III Bagian C | Penghasilan pasangan terpisah | Belum ada domain utama konsisten | PARTIAL | Isi hanya bila key eksplisit tersedia |
| Lampiran IV Bagian A | Harta | harta_current_rows | ACTIVE | Sudah round-trip |
| Lampiran IV Bagian B | Utang | pph_components.utang_rows | ACTIVE | Sudah round-trip |
| Lampiran IV Bagian C | Susunan Anggota Keluarga | Belum ada domain | NO_SOURCE | Tetap tidak aktif |

## Temuan kode saat audit

### Lampiran I H2 Bagian B
Renderer saat ini masih membuat empat baris statis:
- DAGANG
- INDUSTRI
- JASA
- PEKERJAAN BEBAS

Semua nilai masih 0/kosong. Importer sebenarnya sudah membaca `other_income.pekerjaan_bebas_dpp`, tetapi belum memiliki Norma (%) atau Penghasilan Neto yang dapat dipertanggungjawabkan. Karena itu Stage 8E.4B hanya boleh mengaktifkan data yang benar-benar tersedia dan tidak boleh menghitung neto dengan asumsi.

### Lampiran III
Renderer sudah konservatif:
- final income diklasifikasikan dari label detail bila tersedia;
- UMKM ditampung pada kategori final lainnya;
- bukan objek masih berupa agregat dan ditempatkan pada baris 6;
- pasangan terpisah hanya diisi bila ada key eksplisit.

### Induk
Kode sudah menandai bahwa:
- penghasilan neto usaha non-final belum mempunyai sumber domain tersendiri;
- kompensasi kerugian belum dimodelkan.

Kedua field harus tetap kosong sampai source contract ditambah.

## Prioritas implementasi Stage 8E.4

1. **8E.4B — Lampiran I Bagian B**
   - expose `pekerjaan_bebas_dpp` ke renderer;
   - jangan isi Norma dan Neto bila source tidak ada;
   - tambahkan test bahwa Dagang/Industri/Jasa tetap kosong bila tidak ada klasifikasi.

2. **8E.4C — Lampiran III**
   - tambah source detail non-object bila importer menemukan detail;
   - pertahankan fallback agregat hanya jika detail tidak tersedia.

3. **8E.4D — Induk**
   - hubungkan hanya field yang source-nya sudah eksplisit;
   - tidak membuat synthetic values untuk field yang belum punya domain.

4. **8E.4E — Regression Coverage**
   - test Excel;
   - test PDF;
   - test snapshot/finalization;
   - test revision N -> N+1.

## Definition of Done 8E.4A

Stage 8E.4A dianggap selesai ketika:
- sumber setiap area utama terpetakan;
- field tanpa sumber diberi status NO_SOURCE;
- tidak ada aturan mapping yang mengharuskan tebakan;
- urutan implementasi 8E.4B–8E.4E terkunci.
