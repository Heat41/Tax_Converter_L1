import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from config.constants import KategoriL1, StatusProses, AuditAction, AuditSource
from core.models.wp import WajibPajak
from core.models.asset import HartaL1Item
from core.models.audit import AuditTrailEntry
from core.models.reference import ReferenceKodeHarta

class TaxRepository:
    """Repository Layer untuk akses data SQLite: Master WP, Harta L-1, Referensi Kode, dan Audit Trail."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # =========================================================================
    # 1. MASTER WAJIB PAJAK (WP)
    # =========================================================================
    def create_wp(self, wp: WajibPajak) -> int:
        """Membuat data profil Master Wajib Pajak baru."""
        wp.validate()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO master_wp (npwp, nama_wp, tahun_pajak, status_ptkp, status_proses)
            VALUES (?, ?, ?, ?, ?)
        """, (
            wp.npwp,
            wp.nama_wp,
            wp.tahun_pajak,
            wp.status_ptkp,
            wp.status_proses.value if isinstance(wp.status_proses, StatusProses) else str(wp.status_proses)
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_wp_by_id(self, wp_id: int) -> Optional[WajibPajak]:
        """Mengambil data Master WP berdasarkan ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM master_wp WHERE id = ?", (wp_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return WajibPajak(
            id=row["id"],
            npwp=row["npwp"],
            nama_wp=row["nama_wp"],
            tahun_pajak=row["tahun_pajak"],
            status_ptkp=row["status_ptkp"],
            status_proses=StatusProses(row["status_proses"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def get_wp_by_npwp(self, npwp: str, tahun_pajak: int = 2025) -> Optional[WajibPajak]:
        """Mengambil data Master WP berdasarkan NPWP dan Tahun Pajak."""
        clean_npwp = str(npwp).replace(".", "").replace("-", "").strip()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM master_wp WHERE npwp = ? AND tahun_pajak = ?", (clean_npwp, tahun_pajak))
        row = cursor.fetchone()
        if not row:
            return None
        return WajibPajak(
            id=row["id"],
            npwp=row["npwp"],
            nama_wp=row["nama_wp"],
            tahun_pajak=row["tahun_pajak"],
            status_ptkp=row["status_ptkp"],
            status_proses=StatusProses(row["status_proses"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def list_all_wp(self) -> List[WajibPajak]:
        """Mengambil seluruh daftar Wajib Pajak."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM master_wp ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [
            WajibPajak(
                id=r["id"],
                npwp=r["npwp"],
                nama_wp=r["nama_wp"],
                tahun_pajak=r["tahun_pajak"],
                status_ptkp=r["status_ptkp"],
                status_proses=StatusProses(r["status_proses"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
            for r in rows
        ]

    def update_wp_status(self, wp_id: int, status: StatusProses) -> None:
        """Memperbarui status pengerjaan WP (BELUM_IMPOR, DRAFT, FINAL)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE master_wp 
            SET status_proses = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status.value if isinstance(status, StatusProses) else str(status), wp_id))
        self.conn.commit()

    def delete_wp(self, wp_id: int, force: bool = False) -> None:
        """Menghapus profil WP. Jika force=False dan memiliki aset, raise error (safety check)."""
        cursor = self.conn.cursor()
        if not force:
            cursor.execute("SELECT COUNT(*) FROM harta_l1_items WHERE wp_id = ?", (wp_id,))
            asset_count = cursor.fetchone()[0]
            if asset_count > 0:
                raise ValueError(f"Tidak dapat menghapus WP (ID {wp_id}) karena masih memiliki {asset_count} data aset. Gunakan force=True jika ingin menghapus.")
        
        # Hapus audit trail dan aset jika force
        cursor.execute("DELETE FROM audit_trail_koreksi WHERE wp_id = ?", (wp_id,))
        cursor.execute("DELETE FROM harta_l1_items WHERE wp_id = ?", (wp_id,))
        cursor.execute("DELETE FROM import_batches WHERE wp_id = ?", (wp_id,))
        cursor.execute("DELETE FROM master_wp WHERE id = ?", (wp_id,))
        self.conn.commit()

    # =========================================================================
    # 2. UNIFIED ASSET (harta_l1_items)
    # =========================================================================
    def create_asset(self, asset: HartaL1Item) -> int:
        """Menyimpan 1 record aset baru (Original Value = Current Value)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO harta_l1_items (
                wp_id, import_batch_id, kategori_l1, kode_harta, tahun_perolehan,
                nomor_akun, atas_nama, nama_bank_institusi, lokasi_negara,
                saldo_original, saldo_current,
                nomor_identitas_pihak_ketiga, nama_pihak_ketiga,
                nilai_piutang_original, nilai_piutang_current,
                saldo_piutang_original, saldo_piutang_current,
                nama_institusi, nomor_akun_bukti,
                biaya_perolehan_original, biaya_perolehan_current,
                nilai_saat_ini_original, nilai_saat_ini_current,
                merek_model, nomor_polisi_registrasi, jenis_kepemilikan, npwp_pemilik, nama_pemilik,
                lokasi_alamat, luas_tanah, luas_bangunan, sumber_kepemilikan, nomor_sertifikat,
                informasi_tambahan,
                keterangan_pps, keterangan_tambahan, source_file, source_category,
                is_edited, is_active
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?,
                ?, ?, ?, ?,
                ?, ?
            )
        """, (
            asset.wp_id, asset.import_batch_id,
            asset.kategori_l1.value if isinstance(asset.kategori_l1, KategoriL1) else str(asset.kategori_l1),
            asset.kode_harta, asset.tahun_perolehan,
            asset.nomor_akun, asset.atas_nama, asset.nama_bank_institusi, asset.lokasi_negara,
            asset.saldo_original, asset.saldo_current,
            asset.nomor_identitas_pihak_ketiga, asset.nama_pihak_ketiga,
            asset.nilai_piutang_original, asset.nilai_piutang_current,
            asset.saldo_piutang_original, asset.saldo_piutang_current,
            asset.nama_institusi, asset.nomor_akun_bukti,
            asset.biaya_perolehan_original, asset.biaya_perolehan_current,
            asset.nilai_saat_ini_original, asset.nilai_saat_ini_current,
            asset.merek_model, asset.nomor_polisi_registrasi,
            asset.jenis_kepemilikan.value if asset.jenis_kepemilikan else None,
            asset.npwp_pemilik, asset.nama_pemilik,
            asset.lokasi_alamat, asset.luas_tanah, asset.luas_bangunan, asset.sumber_kepemilikan, asset.nomor_sertifikat,
            asset.informasi_tambahan,
            asset.keterangan_pps, asset.keterangan_tambahan, asset.source_file, asset.source_category,
            asset.is_edited, asset.is_active
        ))
        self.conn.commit()
        return cursor.lastrowid

    def bulk_create_assets(self, assets: List[HartaL1Item]) -> int:
        """Menyimpan banyak aset sekaligus dalam satu transaksi."""
        inserted = 0
        for item in assets:
            self.create_asset(item)
            inserted += 1
        return inserted

    def get_asset_by_id(self, asset_id: int) -> Optional[HartaL1Item]:
        """Mengambil aset berdasarkan ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM harta_l1_items WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_asset(row)

    def get_assets_by_wp(self, wp_id: int, kategori: Optional[KategoriL1] = None, only_active: bool = True) -> List[HartaL1Item]:
        """Mengambil seluruh aset milik WP, dengan filter opsional kategori L-1."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM harta_l1_items WHERE wp_id = ?"
        params: List[Any] = [wp_id]

        if kategori:
            query += " AND kategori_l1 = ?"
            params.append(kategori.value if isinstance(kategori, KategoriL1) else str(kategori))
        
        if only_active:
            query += " AND is_active = 1"
            
        query += " ORDER BY id ASC"
        cursor.execute(query, tuple(params))
        return [self._row_to_asset(r) for r in cursor.fetchall()]

    def update_asset_field_with_audit(
        self,
        asset_id: int,
        field_name: str,
        new_value: Any,
        user_reason: Optional[str] = None
    ) -> bool:
        """
        KOREKSI NILAI DENGAN AUDIT TRAIL:
        - Melindungi field '*_original' agar IMMUTABLE (tidak dapat diubah via fungsi ini).
        - Mengupdate field '*_current' atau field deskriptif.
        - Menandai 'is_edited = 1'.
        - Mencatat entri mutasi ke 'audit_trail_koreksi'.
        """
        # 1. Proteksi Immutable Nilai Original
        if field_name.endswith("_original"):
            raise ValueError(f"DILARANG MENGUBAH FIELD ORIGINAL '{field_name}'. Nilai asli Coretax bersifat immutable.")

        # 2. Ambil data aset saat ini
        asset = self.get_asset_by_id(asset_id)
        if not asset:
            raise ValueError(f"Aset dengan ID {asset_id} tidak ditemukan.")

        cursor = self.conn.cursor()
        cursor.execute(f"SELECT {field_name}, wp_id FROM harta_l1_items WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        old_val = row[field_name]
        wp_id = row["wp_id"]

        # Jika nilai sama persis, tidak perlu update
        if str(old_val) == str(new_value):
            return False

        # 3. Lakukan Update
        cursor.execute(f"""
            UPDATE harta_l1_items
            SET {field_name} = ?, is_edited = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_value, asset_id))

        # 4. Catat ke Audit Trail
        cursor.execute("""
            INSERT INTO audit_trail_koreksi (
                wp_id, asset_id, nama_kolom, nilai_lama, nilai_baru, action, source, keterangan
            ) VALUES (?, ?, ?, ?, ?, 'UPDATE', 'USER_EDIT', ?)
        """, (
            wp_id,
            asset_id,
            field_name,
            str(old_val) if old_val is not None else None,
            str(new_value) if new_value is not None else None,
            user_reason
        ))

        self.conn.commit()
        return True

    # =========================================================================
    # 3. STRATEGI RE-IMPORT NON-DESTRUKTIF
    # =========================================================================
    def create_import_batch(self, wp_id: int, source_files_json: str = "{}") -> int:
        """Membuat batch import baru untuk mencatat riwayat impor Coretax."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(batch_number), 0) + 1 FROM import_batches WHERE wp_id = ?", (wp_id,))
        next_batch = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO import_batches (wp_id, batch_number, source_files, status)
            VALUES (?, ?, ?, 'ACTIVE')
        """, (wp_id, next_batch, source_files_json))
        self.conn.commit()
        return cursor.lastrowid

    def reimport_assets(
        self,
        wp_id: int,
        new_assets: List[HartaL1Item],
        strategy: str = "PRESERVE_CORRECTIONS"
    ) -> Dict[str, Any]:
        """
        Mengeksekusi strategi Re-Import:
        - strategy='PRESERVE_CORRECTIONS': Mengarsipkan aset lama / memperbarui nilai original tanpa menghapus audit trail.
        - strategy='RESET_TO_CORETAX': Mengatur nilai current kembali persis sama dengan nilai baru Coretax.
        """
        cursor = self.conn.cursor()
        
        # 1. Catat Batch Baru
        batch_id = self.create_import_batch(wp_id, source_files_json='{"reimport": true}')
        
        # 2. Update status batch lama menjadi 'REPLACED'
        cursor.execute("""
            UPDATE import_batches SET status = 'REPLACED'
            WHERE wp_id = ? AND id != ?
        """, (wp_id, batch_id))

        if strategy == "RESET_TO_CORETAX":
            # Tandai item lama sebagai is_active = 0 (Soft delete/archive)
            cursor.execute("UPDATE harta_l1_items SET is_active = 0 WHERE wp_id = ?", (wp_id,))
            # Insert item baru
            for item in new_assets:
                item.import_batch_id = batch_id
                self.create_asset(item)

        elif strategy == "PRESERVE_CORRECTIONS":
            # Ambil item lama yang pernah diedit (is_edited = 1)
            old_edited = self.get_assets_by_wp(wp_id, only_active=True)
            edited_map = {}
            for item in old_edited:
                if item.is_edited == 1:
                    # Key pencocokan: (kode_harta, tahun_perolehan, nomor_akun/merek/lokasi)
                    match_key = (item.kode_harta, item.tahun_perolehan, item.nomor_akun or item.merek_model or item.lokasi_alamat or "")
                    edited_map[match_key] = item

            # Arsipkan item lama
            cursor.execute("UPDATE harta_l1_items SET is_active = 0 WHERE wp_id = ?", (wp_id,))

            # Insert item baru dan restore koreksi jika cocok
            for item in new_assets:
                item.import_batch_id = batch_id
                match_key = (item.kode_harta, item.tahun_perolehan, item.nomor_akun or item.merek_model or item.lokasi_alamat or "")
                
                if match_key in edited_map:
                    prev = edited_map[match_key]
                    # Salin nilai current yang pernah diedit user
                    item.saldo_current = prev.saldo_current
                    item.nilai_piutang_current = prev.nilai_piutang_current
                    item.saldo_piutang_current = prev.saldo_piutang_current
                    item.biaya_perolehan_current = prev.biaya_perolehan_current
                    item.nilai_saat_ini_current = prev.nilai_saat_ini_current
                    item.is_edited = 1

                new_id = self.create_asset(item)
                
                # Catat ke audit trail bahwa aset ini dipulihkan koreksinya
                if match_key in edited_map:
                    cursor.execute("""
                        INSERT INTO audit_trail_koreksi (
                            wp_id, asset_id, nama_kolom, nilai_lama, nilai_baru, action, source, keterangan
                        ) VALUES (?, ?, 'reimport_merge', 'PREVIOUS_ACTIVE', 'RESTORED_EDIT', 'RE_IMPORT_PRESERVE', 'CORETAX_IMPORT', 'Preserved user correction across re-import')
                    """, (wp_id, new_id))

        self.conn.commit()
        return {"status": "SUCCESS", "batch_id": batch_id, "items_count": len(new_assets)}

    # =========================================================================
    # 4. AUDIT TRAIL
    # =========================================================================
    def get_audit_trail_by_wp(self, wp_id: int) -> List[AuditTrailEntry]:
        """Mengambil seluruh riwayat audit trail untuk WP tertentu."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM audit_trail_koreksi WHERE wp_id = ? ORDER BY waktu_koreksi ASC, id ASC", (wp_id,))
        return [
            AuditTrailEntry(
                id=r["id"],
                wp_id=r["wp_id"],
                asset_id=r["asset_id"],
                nama_kolom=r["nama_kolom"],
                nilai_lama=r["nilai_lama"],
                nilai_baru=r["nilai_baru"],
                action=AuditAction(r["action"]),
                source=AuditSource(r["source"]),
                waktu_koreksi=r["waktu_koreksi"],
                keterangan=r["keterangan"]
            )
            for r in cursor.fetchall()
        ]

    # =========================================================================
    # 5. MASTER REFERENSI KODE HARTA
    # =========================================================================
    def get_all_ref_codes(self) -> List[ReferenceKodeHarta]:
        """Mengambil seluruh master kode referensi (35 mapping)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ref_kode_harta ORDER BY id ASC")
        return [
            ReferenceKodeHarta(
                id=r["id"],
                kode_eform=r["kode_eform"],
                kode_coretax=r["kode_coretax"],
                nama_harta_lama=r["nama_harta_lama"],
                nama_harta_coretax=r["nama_harta_coretax"],
                kategori_l1=KategoriL1(r["kategori_l1"]),
                is_primary_mapping=r["is_primary_mapping"],
                catatan_mapping=r["catatan_mapping"]
            )
            for r in cursor.fetchall()
        ]

    def get_eform_code_for_coretax(self, kode_coretax: str) -> Optional[ReferenceKodeHarta]:
        """Lookup kode E-Form (3 digit) berdasarkan kode Coretax (4 digit)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ref_kode_harta WHERE kode_coretax = ? ORDER BY is_primary_mapping DESC LIMIT 1", (kode_coretax,))
        r = cursor.fetchone()
        if not r:
            return None
        return ReferenceKodeHarta(
            id=r["id"],
            kode_eform=r["kode_eform"],
            kode_coretax=r["kode_coretax"],
            nama_harta_lama=r["nama_harta_lama"],
            nama_harta_coretax=r["nama_harta_coretax"],
            kategori_l1=KategoriL1(r["kategori_l1"]),
            is_primary_mapping=r["is_primary_mapping"],
            catatan_mapping=r["catatan_mapping"]
        )

    def get_coretax_codes_for_eform(self, kode_eform: str) -> List[ReferenceKodeHarta]:
        """Lookup seluruh kemungkinan kode Coretax untuk kode E-Form (mendukung relasi 1:N)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ref_kode_harta WHERE kode_eform = ? ORDER BY is_primary_mapping DESC", (kode_eform,))
        return [
            ReferenceKodeHarta(
                id=r["id"],
                kode_eform=r["kode_eform"],
                kode_coretax=r["kode_coretax"],
                nama_harta_lama=r["nama_harta_lama"],
                nama_harta_coretax=r["nama_harta_coretax"],
                kategori_l1=KategoriL1(r["kategori_l1"]),
                is_primary_mapping=r["is_primary_mapping"],
                catatan_mapping=r["catatan_mapping"]
            )
            for r in cursor.fetchall()
        ]

    # Helper Internal
    def _row_to_asset(self, row: sqlite3.Row) -> HartaL1Item:
        return HartaL1Item(
            id=row["id"],
            wp_id=row["wp_id"],
            import_batch_id=row["import_batch_id"],
            kategori_l1=KategoriL1(row["kategori_l1"]),
            kode_harta=row["kode_harta"],
            tahun_perolehan=row["tahun_perolehan"],
            nomor_akun=row["nomor_akun"],
            atas_nama=row["atas_nama"],
            nama_bank_institusi=row["nama_bank_institusi"],
            lokasi_negara=row["lokasi_negara"],
            saldo_original=row["saldo_original"],
            saldo_current=row["saldo_current"],
            nomor_identitas_pihak_ketiga=row["nomor_identitas_pihak_ketiga"],
            nama_pihak_ketiga=row["nama_pihak_ketiga"],
            nilai_piutang_original=row["nilai_piutang_original"],
            nilai_piutang_current=row["nilai_piutang_current"],
            saldo_piutang_original=row["saldo_piutang_original"],
            saldo_piutang_current=row["saldo_piutang_current"],
            nama_institusi=row["nama_institusi"],
            nomor_akun_bukti=row["nomor_akun_bukti"],
            biaya_perolehan_original=row["biaya_perolehan_original"],
            biaya_perolehan_current=row["biaya_perolehan_current"],
            nilai_saat_ini_original=row["nilai_saat_ini_original"],
            nilai_saat_ini_current=row["nilai_saat_ini_current"],
            merek_model=row["merek_model"],
            nomor_polisi_registrasi=row["nomor_polisi_registrasi"],
            jenis_kepemilikan=row["jenis_kepemilikan"],
            npwp_pemilik=row["npwp_pemilik"],
            nama_pemilik=row["nama_pemilik"],
            lokasi_alamat=row["lokasi_alamat"],
            luas_tanah=row["luas_tanah"],
            luas_bangunan=row["luas_bangunan"],
            sumber_kepemilikan=row["sumber_kepemilikan"],
            nomor_sertifikat=row["nomor_sertifikat"],
            informasi_tambahan=row["informasi_tambahan"],
            keterangan_pps=row["keterangan_pps"],
            keterangan_tambahan=row["keterangan_tambahan"],
            source_file=row["source_file"],
            source_category=row["source_category"],
            is_edited=row["is_edited"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
