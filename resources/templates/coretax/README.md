# Template Coretax L-1

Folder ini adalah lokasi baku template Excel resmi Coretax yang dibundel bersama aplikasi.

Tempatkan enam template resmi L-1 di folder ini:

- Harta Kas / Setara Kas
- Harta Piutang
- Harta Investasi / Sekuritas
- Harta Bergerak
- Harta Tidak Bergerak
- Harta Lainnya

Nama file boleh mengikuti versi resmi DJP. Resolver aplikasi mencocokkan file berdasarkan
`excel_filename_hint` dan memvalidasi sheet/header sebelum digunakan.

Struktur packaging yang diharapkan:

```text
resources/
  templates/
    1770/
      1770_master_bersih_6_halaman.pdf
    coretax/
      <6 template Excel resmi>
```

Jangan menyimpan file output WP, database user, atau hasil export di folder ini.
