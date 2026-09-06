from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

from config.constants import JenisKepemilikan, KategoriL1
from core.models.asset import HartaL1Item
from core.validation.models import BatchImportResult, FileCategoryResult


CATEGORY_TO_ENUM = {
    "KAS SETARA KAS": KategoriL1.KAS,
    "PIUTANG": KategoriL1.PIUTANG,
    "INVESTASI": KategoriL1.INVESTASI,
    "HARTA BERGERAK": KategoriL1.BERGERAK,
    "HARTA TIDAK BERGERAK": KategoriL1.HTB,
    "LAINNYA": KategoriL1.LAINNYA,
}


@dataclass
class HartaMappingResult:
    items: List[HartaL1Item] = field(default_factory=list)
    skipped_rows: int = 0
    skipped_categories: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def mapped_rows(self) -> int:
        return len(self.items)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class CoretaxHartaMapper:
    """Stage 3C: normalisasi hasil Stage 3B menjadi HartaL1Item."""

    def map_batch(
        self,
        batch: BatchImportResult,
        *,
        wp_id: int,
        import_batch_id: Optional[int] = None,
        include_invalid_rows: bool = False,
    ) -> HartaMappingResult:
        result = HartaMappingResult()

        for category, category_result in batch.category_results.items():
            if category not in CATEGORY_TO_ENUM:
                result.skipped_categories.append(category)
                continue

            read_result = category_result.read_result
            if read_result is None or category_result.is_template or category_result.is_nihil:
                result.skipped_categories.append(category)
                continue

            invalid_rows = self._invalid_excel_rows(category_result)
            headers = list(read_result.headers)

            for excel_row, values in enumerate(read_result.rows, start=2):
                if not include_invalid_rows and excel_row in invalid_rows:
                    result.skipped_rows += 1
                    continue

                row = {
                    headers[i]: values[i] if i < len(values) else ""
                    for i in range(len(headers))
                }
                try:
                    item = self.map_row(
                        category,
                        row,
                        wp_id=wp_id,
                        source_file=str(read_result.file_path),
                        import_batch_id=import_batch_id,
                    )
                except Exception as exc:
                    result.errors.append(
                        f"{category} baris {excel_row}: {exc}"
                    )
                    result.skipped_rows += 1
                    continue

                result.items.append(item)

        return result

    def map_row(
        self,
        category: str,
        row: Mapping[str, object],
        *,
        wp_id: int,
        source_file: Optional[str] = None,
        import_batch_id: Optional[int] = None,
    ) -> HartaL1Item:
        if category not in CATEGORY_TO_ENUM:
            raise ValueError(f"Kategori Coretax tidak dikenali: {category}")

        common = {
            "wp_id": wp_id,
            "kategori_l1": CATEGORY_TO_ENUM[category],
            "kode_harta": self._text(self._value(row, "Kode", "Kode Harta")),
            "tahun_perolehan": self._int(self._value(row, "Tahun Perolehan", "Tahun")),
            "keterangan_pps": self._text(self._value(row, "Keterangan")) or None,
            "source_file": source_file,
            "source_category": category,
            "import_batch_id": import_batch_id,
        }

        if category == "KAS SETARA KAS":
            saldo = self._number(self._value(row, "Saldo"))
            return HartaL1Item(
                **common,
                nomor_akun=self._text(self._value(row, "Nomor Akun")) or None,
                atas_nama=self._text(self._value(row, "Atas Nama")) or None,
                nama_bank_institusi=self._text(self._value(row, "Nama Bank/ Institusi", "Nama Bank/Institusi")) or None,
                lokasi_negara=self._text(self._value(row, "Lokasi Harta", "Negara Lokasi")) or None,
                saldo_original=saldo,
                saldo_current=saldo,
            )

        if category == "PIUTANG":
            nilai = self._number(self._value(row, "Nilai Piutang"))
            saldo = self._number(self._value(row, "Saldo Piutang"))
            return HartaL1Item(
                **common,
                lokasi_negara=self._text(self._value(row, "Negara Lokasi", "Lokasi Harta")) or None,
                nomor_identitas_pihak_ketiga=self._text(self._value(row, "Nomor Identitas")) or None,
                nama_pihak_ketiga=self._text(self._value(row, "Nama Penerima")) or None,
                nilai_piutang_original=nilai,
                nilai_piutang_current=nilai,
                saldo_piutang_original=saldo,
                saldo_piutang_current=saldo,
            )

        if category == "INVESTASI":
            biaya = self._number(self._value(row, "Biaya Perolehan"))
            kini = self._number(self._value(row, "Nilai Saat Ini"))
            return HartaL1Item(
                **common,
                lokasi_negara=self._text(self._value(row, "Lokasi Harta")) or None,
                nomor_identitas_pihak_ketiga=self._text(self._value(row, "Nomor Identitas")) or None,
                nama_institusi=self._text(self._value(row, "Nama Bank/Institusi/Penerima Investasi")) or None,
                nomor_akun_bukti=self._text(self._value(row, "Bukti Kepemilikan/Nomor Akun")) or None,
                biaya_perolehan_original=biaya,
                biaya_perolehan_current=biaya,
                nilai_saat_ini_original=kini,
                nilai_saat_ini_current=kini,
            )

        if category == "HARTA BERGERAK":
            biaya = self._number(self._value(row, "Biaya Perolehan"))
            kini = self._number(self._value(row, "Nilai Saat Ini"))
            return HartaL1Item(
                **common,
                merek_model=self._text(self._value(row, "Merk/Model", "Merek/Model")) or None,
                nomor_polisi_registrasi=self._text(self._value(row, "Nomor Polisi/Registrasi")) or None,
                jenis_kepemilikan=self._ownership(self._value(row, "Kepemilikan")),
                npwp_pemilik=self._text(self._value(row, "NPWP Pemilik")) or None,
                nama_pemilik=self._text(self._value(row, "Nama Pemotong Pajak", "Nama Pemilik")) or None,
                biaya_perolehan_original=biaya,
                biaya_perolehan_current=biaya,
                nilai_saat_ini_original=kini,
                nilai_saat_ini_current=kini,
            )

        if category == "HARTA TIDAK BERGERAK":
            biaya = self._number(self._value(row, "Biaya Perolehan"))
            kini = self._number(self._value(row, "Nilai Saat Ini"))
            return HartaL1Item(
                **common,
                lokasi_alamat=self._text(self._value(row, "Lokasi Harta")) or None,
                luas_tanah=self._text(self._value(row, "Ukuran Properti - Tanah")) or None,
                luas_bangunan=self._text(self._value(row, "Ukuran Properti - Bangunan")) or None,
                sumber_kepemilikan=self._text(self._value(row, "Sumber Kepemilikan")) or None,
                nomor_sertifikat=self._text(self._value(row, "Nomor Sertifikat")) or None,
                biaya_perolehan_original=biaya,
                biaya_perolehan_current=biaya,
                nilai_saat_ini_original=kini,
                nilai_saat_ini_current=kini,
            )

        biaya = self._number(self._value(row, "Biaya Perolehan"))
        kini = self._number(self._value(row, "Nilai Saat Ini"))
        return HartaL1Item(
            **common,
            nomor_akun_bukti=self._text(self._value(row, "Bukti Kepemilikan/Nomor Akun")) or None,
            informasi_tambahan=self._text(self._value(row, "Informasi Tambahan")) or None,
            biaya_perolehan_original=biaya,
            biaya_perolehan_current=biaya,
            nilai_saat_ini_original=kini,
            nilai_saat_ini_current=kini,
        )

    @staticmethod
    def _invalid_excel_rows(category_result: FileCategoryResult) -> Set[int]:
        validation = category_result.validation
        if validation is None:
            return set()
        return {
            issue.row
            for issue in validation.errors
            if issue.row is not None
        }

    @classmethod
    def _value(cls, row: Mapping[str, object], *names: str) -> object:
        wanted = {cls._header_key(name) for name in names}
        for key, value in row.items():
            if cls._header_key(str(key)) in wanted:
                return value
        return ""

    @staticmethod
    def _header_key(value: str) -> str:
        return " ".join(value.strip().rstrip("*").lower().split())

    @staticmethod
    def _text(value: object) -> str:
        return "" if value is None else str(value).strip()

    @classmethod
    def _int(cls, value: object) -> int:
        text = cls._text(value)
        if not text:
            raise ValueError("tahun perolehan kosong")
        return int(float(text.replace(",", "")))

    @classmethod
    def _number(cls, value: object) -> float:
        text = cls._text(value)
        if not text:
            return 0.0
        cleaned = text.replace("Rp", "").replace("rp", "").replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            tail = cleaned.rsplit(",", 1)[-1]
            cleaned = cleaned.replace(",", ".") if len(tail) <= 2 else cleaned.replace(",", "")
        return float(cleaned)

    @classmethod
    def _ownership(cls, value: object) -> Optional[JenisKepemilikan]:
        text = cls._text(value).upper()
        if not text:
            return None
        if text in {"TAXPAYER", "WP", "WAJIB PAJAK", "SENDIRI", "MILIK SENDIRI", "1"}:
            return JenisKepemilikan.TAXPAYER
        return JenisKepemilikan.OTHER
