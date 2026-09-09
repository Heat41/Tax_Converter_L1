from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pandas as pd

from core.legacy_mapping import CORETAX_TO_EFORM
from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.worksheet_pph_state import WorksheetBupotRow, WorksheetPPhStateStore
from core.worksheet_state import WorksheetHartaStateStore


@dataclass(frozen=True)
class WorksheetWorkbookImportIssue:
    code: str
    severity: str
    message: str


@dataclass
class WorksheetWorkbookImportResult:
    source_path: Path
    npwp: str = ""
    nama_wp: str = ""
    tahun_pajak: int = 0
    harta_rows: List[WorksheetHartaRow] = field(default_factory=list)
    bupot_rows: List[WorksheetBupotRow] = field(default_factory=list)
    pph_components: dict = field(default_factory=dict)
    issues: List[WorksheetWorkbookImportIssue] = field(default_factory=list)
    pipeline_result: Optional[HartaPipelineResult] = None

    @property
    def errors(self):
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self):
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def is_valid(self) -> bool:
        return bool(self.npwp and self.tahun_pajak) and not self.errors


class WorksheetWorkbookImporter:
    """Stage 8B.1: impor kertas kerja kantor ke state Worksheet aplikasi.

    Acuan utama adalah workbook EVY BACHTIAR:
    - sheet tahun (contoh: ``2025``) untuk Bupot/PPh/penghasilan;
    - ``SIMULASI I`` untuk Harta dan Analisis.

    Parsing dibuat berbasis label/header agar sel kosong milik WP lain tetap sah.
    Data yang memang tidak tersedia dibiarkan 0/kosong; struktur yang rusak menjadi
    issue sehingga aplikasi tidak diam-diam menebak isi.
    """

    def __init__(
        self,
        *,
        harta_store: Optional[WorksheetHartaStateStore] = None,
        pph_store: Optional[WorksheetPPhStateStore] = None,
    ):
        self.harta_store = harta_store or WorksheetHartaStateStore()
        self.pph_store = pph_store or WorksheetPPhStateStore()

    @staticmethod
    def _text(value: object) -> str:
        if pd.isna(value):
            return ""
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _number(value: object, default: float = 0.0) -> float:
        if value is None or pd.isna(value) or value == "":
            return float(default)
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("Rp", "").replace(" ", "")
        if not text:
            return float(default)
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif text.count(".") > 1:
            text = text.replace(".", "")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return float(default)

    @staticmethod
    def _digits(value: object) -> str:
        return re.sub(r"\D", "", str(value or ""))

    @staticmethod
    def _label(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def parse(self, file_path: str | Path) -> WorksheetWorkbookImportResult:
        path = Path(file_path)
        result = WorksheetWorkbookImportResult(source_path=path)
        if not path.exists():
            result.issues.append(WorksheetWorkbookImportIssue("WKI_001", "ERROR", "File kertas kerja tidak ditemukan."))
            return result
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_002", "ERROR", "Kertas kerja harus berupa file Excel .xlsx/.xls."))
            return result

        try:
            excel = pd.ExcelFile(path)
        except Exception as exc:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_003", "ERROR", f"Workbook tidak dapat dibaca: {exc}"))
            return result

        year_sheet = self._find_year_sheet(excel.sheet_names)
        if year_sheet is None:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_004", "ERROR", "Sheet tahun seperti '2025' tidak ditemukan."))
            return result

        result.tahun_pajak = int(year_sheet)
        annual = pd.read_excel(path, sheet_name=year_sheet, header=None, dtype=object)
        self._parse_identity(annual, result)
        self._parse_bupot(annual, result)
        self._parse_pph_components(annual, result)

        if "SIMULASI I" in excel.sheet_names:
            simulasi = pd.read_excel(path, sheet_name="SIMULASI I", header=None, dtype=object)
            self._parse_simulasi_identity(simulasi, result)
            self._parse_harta(simulasi, result)
            self._parse_reconciliation(simulasi, result)
        else:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_101",
                    "WARNING",
                    "Sheet SIMULASI I tidak ditemukan. Penghasilan/PPh tetap dapat diimpor, tetapi Harta harus dilengkapi di aplikasi.",
                )
            )

        if not result.npwp:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_005", "ERROR", "NPWP tidak ditemukan pada kertas kerja."))
        if not result.nama_wp:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_102", "WARNING", "Nama Wajib Pajak tidak ditemukan pada kertas kerja."))

        if result.harta_rows:
            result.pipeline_result = HartaPipelineResult(
                mapping=HartaMappingResult(),
                worksheet_rows=list(result.harta_rows),
                current_year=result.tahun_pajak,
                npwp=result.npwp,
                nama_wp=result.nama_wp,
            )
        else:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_103",
                    "WARNING",
                    "Tidak ada baris Harta pada SIMULASI I. Import tetap dapat dipakai untuk data Penghasilan & PPh.",
                )
            )
        return result

    def has_existing_state(self, result: WorksheetWorkbookImportResult) -> bool:
        if not result.npwp or not result.tahun_pajak:
            return False
        return self.pph_store.load(result.npwp, result.tahun_pajak) is not None

    def persist(self, result: WorksheetWorkbookImportResult) -> None:
        if not result.is_valid:
            raise ValueError("Hasil import kertas kerja belum valid.")

        if result.harta_rows:
            origins = list(range(len(result.harta_rows)))
            self.harta_store.save_state(
                npwp=result.npwp,
                tahun_pajak=result.tahun_pajak,
                original_rows=result.harta_rows,
                current_rows=result.harta_rows,
                origin_indices=origins,
            )

        self.pph_store.save(
            npwp=result.npwp,
            tahun_pajak=result.tahun_pajak,
            bupot_rows=result.bupot_rows,
            components=result.pph_components,
        )

    @staticmethod
    def _find_year_sheet(sheet_names) -> Optional[str]:
        years = [name for name in sheet_names if re.fullmatch(r"20\d{2}", str(name).strip())]
        if not years:
            return None
        return sorted(years)[-1]

    def _find_label_row(self, df, label: str, columns=(0, 1, 2, 3, 4, 5)) -> Optional[int]:
        target = self._label(label)
        for row in range(len(df)):
            for col in columns:
                if col < df.shape[1] and self._label(df.iat[row, col]) == target:
                    return row
        return None

    def _parse_identity(self, df, result):
        for label, attr in (("NAMA", "nama_wp"), ("NPWP", "npwp")):
            row = self._find_label_row(df, label, columns=(0, 1))
            if row is None:
                continue
            value = ""
            for col in range(1, min(df.shape[1], 6)):
                candidate = self._text(df.iat[row, col])
                if candidate and candidate != ":":
                    value = candidate
                    break
            if attr == "npwp":
                value = self._digits(value)
            setattr(result, attr, value)

    def _parse_simulasi_identity(self, df, result):
        identity = {}
        for label in ("NAMA :", "NPWP :", "NAMA", "NPWP"):
            row = self._find_label_row(df, label, columns=(0, 1))
            if row is None:
                continue
            key = "npwp" if "npwp" in label.casefold() else "nama_wp"
            for col in range(1, min(df.shape[1], 6)):
                value = self._text(df.iat[row, col])
                if value and value != ":":
                    identity[key] = self._digits(value) if key == "npwp" else value
                    break

        if identity.get("npwp") and result.npwp and identity["npwp"] != result.npwp:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_006", "ERROR", "NPWP sheet tahun berbeda dengan NPWP SIMULASI I."))
        elif identity.get("npwp") and not result.npwp:
            result.npwp = identity["npwp"]
        if identity.get("nama_wp") and not result.nama_wp:
            result.nama_wp = identity["nama_wp"]

    def _parse_bupot(self, df, result):
        header_row = None
        for row in range(len(df)):
            values = [self._label(df.iat[row, col]) if col < df.shape[1] else "" for col in range(min(df.shape[1], 10))]
            if "jenis" in values and "npwp pemberi kerja" in values and "no bupot" in values and "bruto" in values:
                header_row = row
                break
        if header_row is None:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_104", "WARNING", "Tabel Bupot tidak ditemukan pada sheet tahun."))
            return

        headers = {self._label(df.iat[header_row, col]): col for col in range(df.shape[1]) if self._text(df.iat[header_row, col])}
        required = ("jenis", "npwp pemberi kerja", "no bupot", "bruto", "pengurang")
        if any(key not in headers for key in required):
            result.issues.append(WorksheetWorkbookImportIssue("WKI_007", "ERROR", "Kolom tabel Bupot tidak lengkap."))
            return

        for row in range(header_row + 1, len(df)):
            first_values = [self._label(df.iat[row, col]) for col in range(min(df.shape[1], 3))]
            if "total" in first_values:
                break
            jenis = self._text(df.iat[row, headers["jenis"]])
            npwp = self._digits(df.iat[row, headers["npwp pemberi kerja"]])
            no_bupot = self._text(df.iat[row, headers["no bupot"]])
            bruto = self._number(df.iat[row, headers["bruto"]])
            pengurang = self._number(df.iat[row, headers["pengurang"]])
            if not any((jenis, npwp, no_bupot, bruto, pengurang)):
                continue
            result.bupot_rows.append(
                WorksheetBupotRow(
                    jenis=jenis,
                    npwp_pemberi_kerja=npwp,
                    no_bupot=no_bupot,
                    bruto=bruto,
                    pengurang=pengurang,
                )
            )

    def _value_right_of_label(self, df, label: str, preferred_col: Optional[int] = None, default=0.0):
        row = self._find_label_row(df, label, columns=range(min(df.shape[1], 10)))
        if row is None:
            return default
        if preferred_col is not None and preferred_col < df.shape[1]:
            value = df.iat[row, preferred_col]
            if not pd.isna(value) and value != "":
                return value
        for col in range(1, min(df.shape[1], 10)):
            value = df.iat[row, col]
            if col == 1 and self._label(value) == self._label(label):
                continue
            if not pd.isna(value) and value != "":
                return value
        return default

    def _parse_pph_components(self, df, result):
        status_ptkp = self._text(self._value_right_of_label(df, "PTKP", preferred_col=5, default="TK/0")) or "TK/0"
        zakat = self._number(self._value_right_of_label(df, "PENGURANG PENGHASILAN NETO", preferred_col=5, default=0.0))
        domestic_status = self._text(self._value_right_of_label(df, "Penghasilan Dalam Negeri Lainnya", preferred_col=4, default="TIDAK")).upper()
        domestic_dpp = self._number(self._value_right_of_label(df, "Penghasilan Dalam Negeri Lainnya", preferred_col=5, default=0.0))

        other = {
            "domestic_other_enabled": domestic_status not in {"", "TIDAK", "TIDAK ADA", "NO"} or domestic_dpp != 0,
            "domestic_other_dpp": domestic_dpp,
            "sewa_dpp": self._number(self._value_right_of_label(df, "Sewa atas Tanah dan/atau Bangunan", preferred_col=5)),
            "sewa_pph": self._number(self._value_right_of_label(df, "Sewa atas Tanah dan/atau Bangunan", preferred_col=6)),
            "honor_dpp": self._number(self._value_right_of_label(df, "Honor", preferred_col=5)),
            "honor_pph": self._number(self._value_right_of_label(df, "Honor", preferred_col=6)),
            "pekerjaan_bebas_dpp": self._number(self._value_right_of_label(df, "Pekerjaan bebas", preferred_col=5)),
            "prive_dpp": self._number(self._value_right_of_label(df, "Prive", preferred_col=5)),
            "hibah_warisan_dpp": self._number(self._value_right_of_label(df, "Hibah / Warisan", preferred_col=5)),
            "hibah_warisan_note": self._text(self._value_right_of_label(df, "Hibah / Warisan", preferred_col=7, default="")),
            "zakat": zakat,
        }

        final_rows = []
        final_row = self._find_label_row(df, "Penghasilan Final Lainnya", columns=range(min(df.shape[1], 10)))
        if final_row is not None:
            for row in range(final_row + 1, min(len(df), final_row + 12)):
                if self._find_main_income_label(df, row):
                    break
                description = self._text(df.iat[row, 4]) if df.shape[1] > 4 else ""
                dpp = self._number(df.iat[row, 5]) if df.shape[1] > 5 else 0.0
                pph = self._number(df.iat[row, 6]) if df.shape[1] > 6 else 0.0
                if not any((description, dpp, pph)):
                    continue
                final_rows.append({"keterangan": description or "Final Lainnya", "dpp": dpp, "tarif": (pph / dpp) if dpp else 0.0})

        umkm_bruto = [0.0] * 12
        umkm_pph_setor = [0.0] * 12
        umkm_header = self._find_label_row(df, "PEREDARAN BRUTO UMKM", columns=range(min(df.shape[1], 10)))
        if umkm_header is not None:
            for row in range(umkm_header + 2, min(len(df), umkm_header + 14)):
                month_no = self._number(df.iat[row, 1], default=0) if df.shape[1] > 1 else 0
                idx = int(month_no) - 1
                if 0 <= idx < 12:
                    umkm_bruto[idx] = self._number(df.iat[row, 4]) if df.shape[1] > 4 else 0.0
                    umkm_pph_setor[idx] = self._number(df.iat[row, 6]) if df.shape[1] > 6 else 0.0

        result.pph_components = {
            "penghasilan_neto_lainnya": domestic_dpp if other["domestic_other_enabled"] else 0.0,
            "pengurang_penghasilan_neto": zakat,
            "ptkp": self._number(self._value_right_of_label(df, "PTKP", preferred_col=5, default=0.0)),
            "pph_terutang": self._number(self._value_right_of_label(df, "PPh21 Terutang", preferred_col=5, default=0.0)),
            "kredit_pajak": self._number(self._value_right_of_label(df, "PPh21 sudah dipotong/ dipungut", preferred_col=5, default=0.0)),
            "pph25": self._number(self._value_right_of_label(df, "Angsuran PPh Pasal 25", preferred_col=5, default=0.0)),
            "status_ptkp": status_ptkp,
            "umkm_bruto_bulanan": umkm_bruto,
            "umkm_pph_setor_bulanan": umkm_pph_setor,
            "evy_other_income": other,
            "evy_final_other_income_rows": final_rows,
        }

    def _find_main_income_label(self, df, row: int) -> bool:
        labels = {
            "pekerjaan bebas",
            "prive",
            "hibah / warisan",
            "pengurang penghasilan neto",
            "perhitungan penghasilan vs kenaikan harta",
        }
        for col in range(min(df.shape[1], 6)):
            if self._label(df.iat[row, col]) in labels:
                return True
        return False

    def _parse_harta(self, df, result):
        header_row = None
        for row in range(len(df)):
            labels = [self._label(df.iat[row, col]) for col in range(min(df.shape[1], 12))]
            if "kode ct" in labels and "nama harta" in labels and "th perolehan" in labels:
                header_row = row
                break
        if header_row is None:
            result.issues.append(WorksheetWorkbookImportIssue("WKI_008", "ERROR", "Header Harta pada SIMULASI I tidak ditemukan."))
            return

        headers = {self._label(df.iat[header_row, col]): col for col in range(df.shape[1]) if self._text(df.iat[header_row, col])}
        previous_name = str(result.tahun_pajak - 1)
        current_name = str(result.tahun_pajak)
        for required in ("kode ct", "nama harta", "th perolehan", previous_name, current_name):
            if required not in headers:
                result.issues.append(WorksheetWorkbookImportIssue("WKI_009", "ERROR", f"Kolom Harta '{required}' tidak ditemukan."))
                return

        for row in range(header_row + 1, len(df)):
            marker = self._label(df.iat[row, 0]) if df.shape[1] else ""
            if marker in {"total harta", "utang", "total"}:
                if marker == "total harta":
                    break
            kode_ct = self._text(df.iat[row, headers["kode ct"]])
            nama = self._text(df.iat[row, headers["nama harta"]])
            if not kode_ct and not nama:
                continue
            kode_eform = self._text(df.iat[row, headers.get("kode eform", -1)]) if "kode eform" in headers else ""
            if not kode_eform:
                kode_eform = CORETAX_TO_EFORM.get(kode_ct, "")
            try:
                tahun = int(self._number(df.iat[row, headers["th perolehan"]], default=result.tahun_pajak))
            except (TypeError, ValueError):
                tahun = result.tahun_pajak
            result.harta_rows.append(
                WorksheetHartaRow(
                    nomor=len(result.harta_rows) + 1,
                    kode_eform=kode_eform,
                    kode_ct=kode_ct,
                    nama_harta=nama,
                    nomor_akun_keterangan=self._text(df.iat[row, headers.get("nomor akun / keterangan", -1)]) if "nomor akun / keterangan" in headers else "",
                    atas_nama=self._text(df.iat[row, headers.get("atas nama", -1)]) if "atas nama" in headers else "",
                    nama_bank=self._text(df.iat[row, headers.get("nama bank", -1)]) if "nama bank" in headers else "",
                    tahun_perolehan=tahun,
                    nilai_tahun_sebelumnya=self._number(df.iat[row, headers[previous_name]]),
                    nilai_tahun_berjalan=self._number(df.iat[row, headers[current_name]]),
                )
            )

    def _parse_reconciliation(self, df, result):
        manual = {
            "utang_sebelumnya": 0.0,
            "utang_berjalan": 0.0,
            "pengeluaran_lain_lain": 0.0,
            "kerugian_keuntungan_penjualan_aset": 0.0,
            "utang_baru_atas_kredit": 0.0,
            "harta_baru_dari_kredit": 0.0,
            "penambahan_penghasilan_bruto_umkm": 0.0,
            "margin_usaha": 0.0,
        }

        utang_row = self._find_label_row(df, "UTANG", columns=(0, 1))
        if utang_row is not None:
            total_row = self._find_label_after(df, "TOTAL", utang_row + 1)
            if total_row is not None and df.shape[1] > 9:
                manual["utang_sebelumnya"] = self._number(df.iat[total_row, 8])
                manual["utang_berjalan"] = self._number(df.iat[total_row, 9])

        mapping = {
            "Pengeluaran lain-lain": "pengeluaran_lain_lain",
            "Kerugian (keuntungan) penjualan aset": "kerugian_keuntungan_penjualan_aset",
            "Utang baru atas kredit": "utang_baru_atas_kredit",
            "Harta baru dari kredit": "harta_baru_dari_kredit",
            "Penambahan Penghasilan Bruto UMKM": "penambahan_penghasilan_bruto_umkm",
            "Margin Usaha": "margin_usaha",
        }
        for label, key in mapping.items():
            row = self._find_label_row(df, label, columns=(0, 1, 2))
            if row is None or df.shape[1] <= 9:
                continue
            value = self._number(df.iat[row, 9])
            if key == "margin_usaha" and value > 1:
                value /= 100.0
            manual[key] = value

        result.pph_components["evy_reconciliation"] = manual

    def _find_label_after(self, df, label: str, start_row: int) -> Optional[int]:
        target = self._label(label)
        for row in range(start_row, len(df)):
            for col in range(min(df.shape[1], 3)):
                if self._label(df.iat[row, col]) == target:
                    return row
        return None
