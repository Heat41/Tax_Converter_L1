# Template PDF 1770

Simpan formulir 1770 kosong resmi DJP pada path berikut:

`resources/templates/1770/1770_blank.pdf`

File PDF template tidak dimodifikasi oleh aplikasi. Exporter bekerja pada salinan.

Halaman Bahasa Indonesia yang menjadi baseline output seperti contoh Lisa:

- halaman 10: Induk 1770
- halaman 12: Lampiran I halaman 2 (Pencatatan)
- halaman 13: Lampiran II
- halaman 14: Lampiran III
- halaman 15: Lampiran IV

Gunakan `python scripts/install_1770_template.py --source <file.pdf>` untuk memasang template dan `python scripts/inspect_1770_template.py` untuk memvalidasi AcroForm.
