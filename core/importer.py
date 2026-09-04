import os
import pandas as pd
import xml.etree.ElementTree as ET
from config.database import get_db_connection

class CoretaxImporter:
    """Engine Parser & Importer untuk 6 tabel Lampiran L-1 Coretax (Excel/XML)"""

    def __init__(self, wp_id):
        self.wp_id = wp_id

    def import_excel_files(self, file_paths):
        """
        Menerima dictionary file path dari 6 tabel Coretax L-1.
        Format file_paths: {
            'kas': 'path/to/kas.xlsx',
            'piutang': 'path/to/piutang.xlsx',
            'investasi': 'path/to/investasi.xlsx',
            'bergerak': 'path/to/bergerak.xlsx',
            'htb': 'path/to/htb.xlsx',
            'lainnya': 'path/to/lainnya.xlsx'
        }
        """
        summary = {}
        for category, path in file_paths.items():
            if os.path.exists(path):
                if path.endswith('.xlsx') or path.endswith('.xls'):
                    count = self._parse_and_save_excel(category, path)
                    summary[category] = count
                elif path.endswith('.xml'):
                    count = self._parse_and_save_xml(category, path)
                    summary[category] = count
        
        # Update status WP menjadi Draft setelah berhasil impor
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE master_wp SET status_pengerjaan = 'Draft' WHERE id = ?", (self.wp_id,))
        conn.commit()
        conn.close()

        return summary

    def _parse_and_save_excel(self, category, file_path):
        df = pd.read_excel(file_path)
        conn = get_db_connection()
        cursor = conn.cursor()

        # Normalisasi nama kolom menjadi huruf kecil
        df.columns = [str(col).strip().lower() for col in df.columns]
        rows_inserted = 0

        if category == 'kas':
            cursor.execute("DELETE FROM harta_l1_kas WHERE wp_id = ?", (self.wp_id,))
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO harta_l1_kas 
                    (wp_id, kode_harta, nama_harta, tahun_perolehan, harga_perolehan, keterangan, nilai_asal_coretax)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.wp_id,
                    str(row.get('kode_harta', '')),
                    str(row.get('nama_harta', '')),
                    int(row.get('tahun_perolehan', 0)) if pd.notnull(row.get('tahun_perolehan')) else None,
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0,
                    str(row.get('keterangan', '')),
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0
                ))
                rows_inserted += 1

        elif category == 'piutang':
            cursor.execute("DELETE FROM harta_l1_piutang WHERE wp_id = ?", (self.wp_id,))
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO harta_l1_piutang 
                    (wp_id, kode_harta, nama_peminjam, npwp_peminjam, tahun_perolehan, harga_perolehan, keterangan, nilai_asal_coretax)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.wp_id,
                    str(row.get('kode_harta', '')),
                    str(row.get('nama_peminjam', '')),
                    str(row.get('npwp_peminjam', '')),
                    int(row.get('tahun_perolehan', 0)) if pd.notnull(row.get('tahun_perolehan')) else None,
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0,
                    str(row.get('keterangan', '')),
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0
                ))
                rows_inserted += 1

        elif category == 'investasi':
            cursor.execute("DELETE FROM harta_l1_investasi WHERE wp_id = ?", (self.wp_id,))
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO harta_l1_investasi 
                    (wp_id, kode_harta, nama_harta, penerbit_saham, tahun_perolehan, harga_perolehan, keterangan, nilai_asal_coretax)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.wp_id,
                    str(row.get('kode_harta', '')),
                    str(row.get('nama_harta', '')),
                    str(row.get('penerbit_saham', '')),
                    int(row.get('tahun_perolehan', 0)) if pd.notnull(row.get('tahun_perolehan')) else None,
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0,
                    str(row.get('keterangan', '')),
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0
                ))
                rows_inserted += 1

        elif category == 'bergerak':
            cursor.execute("DELETE FROM harta_l1_bergerak WHERE wp_id = ?", (self.wp_id,))
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO harta_l1_bergerak 
                    (wp_id, kode_harta, nama_harta, merek_type, tahun_perolehan, harga_perolehan, keterangan, nilai_asal_coretax)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.wp_id,
                    str(row.get('kode_harta', '')),
                    str(row.get('nama_harta', '')),
                    str(row.get('merek_type', '')),
                    int(row.get('tahun_perolehan', 0)) if pd.notnull(row.get('tahun_perolehan')) else None,
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0,
                    str(row.get('keterangan', '')),
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0
                ))
                rows_inserted += 1

        elif category == 'htb':
            cursor.execute("DELETE FROM harta_l1_htb WHERE wp_id = ?", (self.wp_id,))
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO harta_l1_htb 
                    (wp_id, kode_harta, jenis_harta, lokasi_alamat, tahun_perolehan, harga_perolehan, keterangan, nilai_asal_coretax)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.wp_id,
                    str(row.get('kode_harta', '')),
                    str(row.get('jenis_harta', '')),
                    str(row.get('lokasi_alamat', '')),
                    int(row.get('tahun_perolehan', 0)) if pd.notnull(row.get('tahun_perolehan')) else None,
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0,
                    str(row.get('keterangan', '')),
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0
                ))
                rows_inserted += 1

        elif category == 'lainnya':
            cursor.execute("DELETE FROM harta_l1_lainnya WHERE wp_id = ?", (self.wp_id,))
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO harta_l1_lainnya 
                    (wp_id, kode_harta, nama_harta, tahun_perolehan, harga_perolehan, keterangan, nilai_asal_coretax)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.wp_id,
                    str(row.get('kode_harta', '')),
                    str(row.get('nama_harta', '')),
                    int(row.get('tahun_perolehan', 0)) if pd.notnull(row.get('tahun_perolehan')) else None,
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0,
                    str(row.get('keterangan', '')),
                    float(row.get('harga_perolehan', 0.0)) if pd.notnull(row.get('harga_perolehan')) else 0.0
                ))
                rows_inserted += 1

        conn.commit()
        conn.close()
        return rows_inserted

    def _parse_and_save_xml(self, category, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        # Logika parsing XML disesuaikan skema DJP
        return 0