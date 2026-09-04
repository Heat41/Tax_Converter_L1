"""
Seeder untuk tabel ref_kode_harta.
Memuat 35 baris pemetaan standar dari Kertas Kerja (Sheet REF)
beserta normalisasi relasi 1:1 dan 1:N antara Kode E-Form Lama (3-digit)
dan Kode Coretax Baru (4-digit).
"""

from typing import List, Dict, Any, Optional
import sqlite3

# 35 Baris Master Mapping Baku
RAW_MAPPING_DATA = [
    {"row": 1, "kode_eform": "011", "kode_ct": "0101", "nama_lama": "Uang Tunai", "nama_ct": "Uang Tunai / Bank Note / Koin", "kategori": "KAS", "is_primary": 1, "notes": "1:1"},
    {"row": 2, "kode_eform": "012", "kode_ct": "0102", "nama_lama": "Tabungan", "nama_ct": "Tabungan (Bank / Lembaga Keuangan)", "kategori": "KAS", "is_primary": 1, "notes": "1:1"},
    {"row": 3, "kode_eform": "013", "kode_ct": "0103", "nama_lama": "Giro", "nama_ct": "Giro", "kategori": "KAS", "is_primary": 1, "notes": "1:1"},
    {"row": 4, "kode_eform": "014", "kode_ct": "0104", "nama_lama": "Deposito", "nama_ct": "Deposito", "kategori": "KAS", "is_primary": 1, "notes": "1:1"},
    {"row": 5, "kode_eform": "019", "kode_ct": "0712", "nama_lama": "Setara Kas Lainnya", "nama_ct": "Uang Elektronik / Dompet Digital", "kategori": "KAS", "is_primary": 1, "notes": "1:N (0712/0799) - Primary"},
    {"row": 5, "kode_eform": "019", "kode_ct": "0799", "nama_lama": "Setara Kas Lainnya", "nama_ct": "Setara Kas Lainnya", "kategori": "KAS", "is_primary": 0, "notes": "1:N (0712/0799) - Secondary"},
    {"row": 6, "kode_eform": "021", "kode_ct": "0201", "nama_lama": "Piutang", "nama_ct": "Piutang Usaha / Dagang", "kategori": "PIUTANG", "is_primary": 1, "notes": "1:1"},
    {"row": 7, "kode_eform": "022", "kode_ct": "0202", "nama_lama": "Piutang Afiliasi", "nama_ct": "Piutang Hubungan Istimewa / Afiliasi", "kategori": "PIUTANG", "is_primary": 1, "notes": "1:1"},
    {"row": 8, "kode_eform": "029", "kode_ct": "0209", "nama_lama": "Piutang Lainnya", "nama_ct": "Piutang Lain-lain", "kategori": "PIUTANG", "is_primary": 1, "notes": "1:1"},
    {"row": 9, "kode_eform": "031", "kode_ct": "0301", "nama_lama": "Saham yang Dibeli untuk Dijual", "nama_ct": "Saham Diperdagangkan (Bursa Efek)", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 10, "kode_eform": "032", "kode_ct": "0302", "nama_lama": "Saham", "nama_ct": "Saham Non-Bursa / Modal PT", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 11, "kode_eform": "033", "kode_ct": "0304", "nama_lama": "Obligasi Perusahaan", "nama_ct": "Obligasi Korporasi", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 12, "kode_eform": "034", "kode_ct": "0305", "nama_lama": "Obligasi Pemerintah Indonesia", "nama_ct": "Surat Berharga Negara (ORI / Sukuk / SUN)", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 13, "kode_eform": "035", "kode_ct": "0306", "nama_lama": "Surat Utang Lainnya", "nama_ct": "Surat Utang / Medium Term Notes", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 14, "kode_eform": "036", "kode_ct": "0307", "nama_lama": "Reksadana", "nama_ct": "Reksadana / Unit Penyertaan", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 15, "kode_eform": "037", "kode_ct": "0308", "nama_lama": "Instrumen Derivatif", "nama_ct": "Derivatif (Right, Warrant, Opsi, Kontrak Berjangka)", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 16, "kode_eform": "038", "kode_ct": "0309", "nama_lama": "Penyertaan Modal Lainnya", "nama_ct": "Penyertaan Modal CV, Firma, Kongsi", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 17, "kode_eform": "039", "kode_ct": "0399", "nama_lama": "Investasi Lainnya", "nama_ct": "Investasi Lainnya", "kategori": "INVESTASI", "is_primary": 1, "notes": "1:1"},
    {"row": 18, "kode_eform": "041", "kode_ct": "0401", "nama_lama": "Sepeda", "nama_ct": "Sepeda", "kategori": "BERGERAK", "is_primary": 1, "notes": "1:1"},
    {"row": 19, "kode_eform": "042", "kode_ct": "0402", "nama_lama": "Sepeda Motor", "nama_ct": "Sepeda Motor", "kategori": "BERGERAK", "is_primary": 1, "notes": "1:1"},
    {"row": 20, "kode_eform": "043", "kode_ct": "0403", "nama_lama": "Mobil", "nama_ct": "Mobil Penumpang", "kategori": "BERGERAK", "is_primary": 1, "notes": "1:1"},
    {"row": 21, "kode_eform": "049", "kode_ct": "0499", "nama_lama": "Alat Transportasi Lainnya", "nama_ct": "Alat Transportasi Lainnya", "kategori": "BERGERAK", "is_primary": 1, "notes": "1:1"},
    {"row": 22, "kode_eform": "051", "kode_ct": "0701", "nama_lama": "Logam Mulia", "nama_ct": "Emas Batangan / Logam Mulia Murni", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:N (0701/0702) - Primary"},
    {"row": 22, "kode_eform": "051", "kode_ct": "0702", "nama_lama": "Logam Mulia", "nama_ct": "Emas Perhiasan / Platina Perhiasan", "kategori": "LAINNYA", "is_primary": 0, "notes": "1:N (0701/0702) - Secondary"},
    {"row": 23, "kode_eform": "052", "kode_ct": "0705", "nama_lama": "Batu Mulia", "nama_ct": "Batu Permata (Intan, Berlian, Batu Mulia)", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:1"},
    {"row": 24, "kode_eform": "053", "kode_ct": "0706", "nama_lama": "Barang Seni & Antik", "nama_ct": "Barang Seni, Antik, Lukisan, Guci", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:1"},
    {"row": 25, "kode_eform": "054", "kode_ct": "0707", "nama_lama": "Kapal Pesiar / Pesawat / Olahraga", "nama_ct": "Kapal Pesiar, Pesawat, Jetski, Olahraga Khusus", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:1"},
    {"row": 26, "kode_eform": "055", "kode_ct": "0708", "nama_lama": "Peralatan Elektronik & Furnitur", "nama_ct": "Peralatan Elektronik & Komputer", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:N (0708/0709) - Primary"},
    {"row": 26, "kode_eform": "055", "kode_ct": "0709", "nama_lama": "Peralatan Elektronik & Furnitur", "nama_ct": "Furnitur & Perabot Rumah Tangga", "kategori": "LAINNYA", "is_primary": 0, "notes": "1:N (0708/0709) - Secondary"},
    {"row": 27, "kode_eform": "059", "kode_ct": "0499", "nama_lama": "Harta Bergerak Lainnya", "nama_ct": "Hewan Ternak, Kuda, Koleksi Bergerak Lainnya", "kategori": "BERGERAK", "is_primary": 0, "notes": "N:1 dengan 049"},
    {"row": 28, "kode_eform": "061", "kode_ct": "0501", "nama_lama": "Tanah & Bangunan Tempat Tinggal", "nama_ct": "Tanah Kosong untuk Tempat Tinggal", "kategori": "HTB", "is_primary": 1, "notes": "1:N (0501/0502) - Primary"},
    {"row": 28, "kode_eform": "061", "kode_ct": "0502", "nama_lama": "Tanah & Bangunan Tempat Tinggal", "nama_ct": "Tanah dan/atau Bangunan Rumah Tinggal", "kategori": "HTB", "is_primary": 0, "notes": "1:N (0501/0502) - Secondary"},
    {"row": 29, "kode_eform": "062", "kode_ct": "0506", "nama_lama": "Tanah & Bangunan untuk Usaha", "nama_ct": "Bangunan Usaha (Toko, Pabrik, Gudang, Ruko)", "kategori": "HTB", "is_primary": 1, "notes": "1:1"},
    {"row": 30, "kode_eform": "063", "kode_ct": "0505", "nama_lama": "Tanah / Lahan untuk Usaha", "nama_ct": "Lahan Pertanian, Perkebunan, Perikanan", "kategori": "HTB", "is_primary": 1, "notes": "1:1"},
    {"row": 31, "kode_eform": "069", "kode_ct": "0509", "nama_lama": "Harta Tidak Bergerak Lainnya", "nama_ct": "Harta Tidak Bergerak Lainnya", "kategori": "HTB", "is_primary": 1, "notes": "1:1"},
    {"row": 32, "kode_eform": "071", "kode_ct": "0601", "nama_lama": "Paten", "nama_ct": "Hak Paten", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:1"},
    {"row": 33, "kode_eform": "072", "kode_ct": "0602", "nama_lama": "Royalti", "nama_ct": "Hak Royalti", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:1"},
    {"row": 34, "kode_eform": "073", "kode_ct": "0603", "nama_lama": "Merek Dagang", "nama_ct": "Hak Merek Dagang", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:1"},
    {"row": 35, "kode_eform": "079", "kode_ct": "0699", "nama_lama": "Harta Tidak Berwujud Lainnya", "nama_ct": "Harta Tidak Berwujud Lainnya / Lisensi Digital", "kategori": "LAINNYA", "is_primary": 1, "notes": "1:1"},
]

def seed_ref_kode_harta(conn: sqlite3.Connection) -> int:
    """Mengisi tabel ref_kode_harta dengan 35 mapping master."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ref_kode_harta")
    count = cursor.fetchone()[0]
    
    if count == 0:
        for item in RAW_MAPPING_DATA:
            cursor.execute("""
                INSERT INTO ref_kode_harta 
                (kode_eform, kode_coretax, nama_harta_lama, nama_harta_coretax, kategori_l1, is_primary_mapping, catatan_mapping)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                item["kode_eform"],
                item["kode_ct"],
                item["nama_lama"],
                item["nama_ct"],
                item["kategori"],
                item["is_primary"],
                item["notes"]
            ))
        conn.commit()
        return len(RAW_MAPPING_DATA)
    return count
