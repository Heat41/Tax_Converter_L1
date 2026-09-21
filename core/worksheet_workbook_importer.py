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
from core.worksheet_sorting import sort_harta_rows
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

    Struktur acuan adalah workbook Kertas Kerja produksi:
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

    def persist(
        self,
        result: WorksheetWorkbookImportResult,
        *,
        include_bupot: bool = True,
    ) -> None:
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

        bupot_rows = list(result.bupot_rows)
        if not include_bupot:
            existing = self.pph_store.load(result.npwp, result.tahun_pajak)
            bupot_rows = list(existing.bupot_rows) if existing is not None else []

        self.pph_store.save(
            npwp=result.npwp,
            tahun_pajak=result.tahun_pajak,
            bupot_rows=bupot_rows,
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
        for row in range(min(len(df), 12)):
            label = self._label(df.iat[row, 0]) if df.shape[1] else ""
            if "nama" in label and not result.nama_wp:
                for col in range(1, min(df.shape[1], 6)):
                    value = self._text(df.iat[row, col])
                    if value and value != ":":
                        result.nama_wp = value
                        break
            if "npwp" in label and not result.npwp:
                for col in range(1, min(df.shape[1], 6)):
                    value = self._digits(df.iat[row, col])
                    if value:
                        result.npwp = value
                        break

    def _parse_bupot(self, df, result):
        header_row = None
        for row in range(len(df)):
            labels = [self._label(df.iat[row, col]) for col in range(min(df.shape[1], 10))]
            if "jenis" in labels and "npwp pemberi kerja" in labels and "no bupot" in labels:
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

        pph_column = None
        for alias in (
            "pph dipotong",
            "pph21 dipotong",
            "pph 21 dipotong",
            "jumlah pph",
            "pph dipotong/dipungut",
            "pph yang dipotong/dipungut",
        ):
            if alias in headers:
                pph_column = headers[alias]
                break

        for row in range(header_row + 1, len(df)):
            first_values = [self._label(df.iat[row, col]) for col in range(min(df.shape[1], 3))]
            if "total" in first_values:
                break
            jenis = self._text(df.iat[row, headers["jenis"]])
            npwp = self._digits(df.iat[row, headers["npwp pemberi kerja"]])
            no_bupot = self._text(df.iat[row, headers["no bupot"]])
            bruto = self._number(df.iat[row, headers["bruto"]])
            pengurang = self._number(df.iat[row, headers["pengurang"]])
            pph_dipotong = (
                self._number(df.iat[row, pph_column])
                if pph_column is not None
                else 0.0
            )
            if not any((jenis, npwp, no_bupot, bruto, pengurang, pph_dipotong)):
                continue
            result.bupot_rows.append(
                WorksheetBupotRow(
                    jenis=jenis,
                    npwp_pemberi_kerja=npwp,
                    no_bupot=no_bupot,
                    bruto=bruto,
                    pengurang=pengurang,
                    pph_dipotong=pph_dipotong,
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

    def _value_right_of_labels(
        self,
        df,
        labels,
        preferred_col: Optional[int] = None,
        default=0.0,
    ):
        """Ambil nilai dari salah satu variasi label Kertas Kerja."""
        for label in labels:
            row = self._find_label_row(
                df,
                label,
                columns=range(min(df.shape[1], 12)),
            )
            if row is None:
                continue

            if preferred_col is not None and preferred_col < df.shape[1]:
                value = df.iat[row, preferred_col]
                if not pd.isna(value) and value != "":
                    return value

            target = self._label(label)
            for col in range(df.shape[1]):
                value = df.iat[row, col]
                if self._label(value) == target:
                    continue
                if not pd.isna(value) and value != "":
                    return value
        return default

    def _find_tax_year_value_column(self, df, tahun_pajak: int) -> Optional[int]:
        """Cari kolom nilai tahun aktif pada blok ringkasan Penghasilan."""
        if not tahun_pajak:
            return None

        current = str(int(tahun_pajak))
        previous = str(int(tahun_pajak) - 1)
        fallback = None

        for row in range(min(len(df), 80)):
            labels = [
                self._label(df.iat[row, col])
                for col in range(df.shape[1])
            ]
            if current not in labels:
                continue

            current_col = labels.index(current)
            if previous in labels:
                return current_col
            if fallback is None:
                fallback = current_col

        return fallback

    def _parse_pph_components(self, df, result):
        year_col = self._find_tax_year_value_column(
            df,
            int(getattr(result, "tahun_pajak", 0) or 0),
        )

        def annual_value(labels, fallback_col=5, default=0.0):
            preferred = year_col if year_col is not None else fallback_col
            return self._value_right_of_labels(
                df,
                labels,
                preferred_col=preferred,
                default=default,
            )

        status_ptkp = self._text(
            self._value_right_of_label(
                df, "PTKP", preferred_col=5, default="TK/0"
            )
        ) or "TK/0"
        zakat = self._number(
            self._value_right_of_label(
                df,
                "PENGURANG PENGHASILAN NETO",
                preferred_col=5,
                default=0.0,
            )
        )

        domestic_labels = (
            "Penghasilan Dalam Negeri Lainnya",
            "Jumlah Penghasilan Dalam Negeri Lainnya",
        )
        domestic_dpp = self._number(
            annual_value(domestic_labels, fallback_col=5, default=0.0)
        )
        domestic_status = self._text(
            self._value_right_of_labels(
                df,
                domestic_labels,
                preferred_col=4 if year_col is None else year_col,
                default="TIDAK",
            )
        ).upper()

        other = {
            "domestic_other_enabled": domestic_status not in {"", "0", "-", "TIDAK", "TIDAK ADA", "NO"} or domestic_dpp != 0,
            "domestic_other_dpp": domestic_dpp,
            "sewa_dpp": self._number(
                annual_value((
                    "Sewa atas Tanah dan/atau Bangunan",
                    "Jumlah Penghasilan Sewa atas Tanah dan/atau Bangunan",
                ))
            ),
            "sewa_pph": self._number(self._value_right_of_label(df, "Sewa atas Tanah dan/atau Bangunan", preferred_col=6, default=0.0)),
            "honor_dpp": self._number(annual_value(("Honor", "Jumlah Penghasilan Honor"))),
            "honor_pph": self._number(self._value_right_of_label(df, "Honor", preferred_col=6, default=0.0)),
            "pekerjaan_bebas_dpp": self._number(
                annual_value((
                    "Pekerjaan bebas",
                    "Jumlah Penghasilan Dari Pekerjaan Bebas",
                    "Jumlah Penghasilan Pekerjaan Bebas",
                ))
            ),
            "prive_dpp": self._number(annual_value(("Prive",), fallback_col=5)),
            "hibah_warisan_dpp": self._number(annual_value(("Hibah / Warisan",), fallback_col=5)),
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

        imported_neto_gabungan = self._number(
            self._value_right_of_labels(
                df,
                (
                    "Penghasilan Neto Gabungan",
                    "Jumlah Penghasilan Neto Gabungan",
                ),
                preferred_col=year_col if year_col is not None else 5,
                default=0.0,
            )
        )
        imported_pkp = self._number(
            self._value_right_of_labels(
                df,
                ("Penghasilan Kena Pajak",),
                preferred_col=year_col if year_col is not None else 5,
                default=0.0,
            )
        )
        imported_pph_terutang = self._number(
            self._value_right_of_labels(
                df,
                ("PPh21 Terutang", "PPh 21 Terutang"),
                preferred_col=year_col if year_col is not None else 5,
                default=0.0,
            )
        )

        result.pph_components = {
            "penghasilan_neto_lainnya": domestic_dpp if other["domestic_other_enabled"] else 0.0,
            "pengurang_penghasilan_neto": zakat,
            "ptkp": self._number(self._value_right_of_label(df, "PTKP", preferred_col=5, default=0.0)),
            "pph_terutang": imported_pph_terutang,
            "penghasilan_neto_gabungan_imported": imported_neto_gabungan,
            "pkp_imported": imported_pkp,
            "pph_terutang_imported": imported_pph_terutang,
            "kredit_pajak": self._number(self._value_right_of_label(df, "PPh21 sudah dipotong/ dipungut", preferred_col=5, default=0.0)),
            "pph25": self._number(self._value_right_of_label(df, "Angsuran PPh Pasal 25", preferred_col=5, default=0.0)),
            "status_ptkp": status_ptkp,
            "umkm_bruto_bulanan": umkm_bruto,
            "umkm_pph_setor_bulanan": umkm_pph_setor,
            "other_income": other,
            "final_other_income_rows": final_rows,
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
            if marker.startswith("total harta") or marker == "utang":
                break
            code_ct = self._text(df.iat[row, headers["kode ct"]])
            name = self._text(df.iat[row, headers["nama harta"]])
            if not code_ct and not name:
                continue
            code_eform = self._text(df.iat[row, headers.get("kode eform", -1)]) if "kode eform" in headers else ""
            if not code_eform:
                code_eform = CORETAX_TO_EFORM.get(code_ct, "")
            result.harta_rows.append(
                WorksheetHartaRow(
                    nomor=len(result.harta_rows) + 1,
                    kode_eform=code_eform,
                    kode_ct=code_ct,
                    nama_harta=name,
                    nomor_akun_keterangan=self._text(df.iat[row, headers.get("nomor akun / keterangan", -1)]) if "nomor akun / keterangan" in headers else "",
                    atas_nama=self._text(df.iat[row, headers.get("atas nama", -1)]) if "atas nama" in headers else "",
                    nama_bank=self._text(df.iat[row, headers.get("nama bank", -1)]) if "nama bank" in headers else "",
                    tahun_perolehan=int(self._number(df.iat[row, headers["th perolehan"]], default=result.tahun_pajak) or result.tahun_pajak),
                    nilai_tahun_sebelumnya=self._number(df.iat[row, headers[previous_name]]),
                    nilai_tahun_berjalan=self._number(df.iat[row, headers[current_name]]),
                )
            )

        result.harta_rows = sort_harta_rows(result.harta_rows)

    def _parse_reconciliation(self, df, result):
        state = {
            "utang_sebelumnya": 0.0,
            "utang_berjalan": 0.0,
            "pengeluaran_lain_lain": 0.0,
            "kerugian_keuntungan_penjualan_aset": 0.0,
            "utang_baru_atas_kredit": 0.0,
            "harta_baru_dari_kredit": 0.0,
            "penambahan_penghasilan_bruto_umkm": 0.0,
            "margin_usaha": 0.0,
            "penghasilan_netto_analisis": 0.0,
            "harta_sebelumnya_override": 0.0,
        }

        current_year = int(getattr(result, "tahun_pajak", 0) or 0)
        previous_year = current_year - 1 if current_year else 0
        previous_col = None
        current_col = None

        # Cari kolom tahun pada SIMULASI secara global. Struktur Harta, Utang,
        # dan Analisis menggunakan kolom tahun yang sama pada workbook produksi.
        for scan_row in range(min(len(df), 140)):
            labels = [
                self._label(df.iat[scan_row, col])
                for col in range(df.shape[1])
            ]
            if current_year and str(current_year) in labels:
                candidate_current = labels.index(str(current_year))
                candidate_previous = (
                    labels.index(str(previous_year))
                    if previous_year and str(previous_year) in labels
                    else None
                )
                if candidate_previous is not None:
                    previous_col = candidate_previous
                    current_col = candidate_current
                    break
                if current_col is None:
                    current_col = candidate_current

        utang_row = self._find_label_row(df, "UTANG", columns=(0, 1, 2))
        utang_rows = []
        if utang_row is not None:
            total_row = None
            # Header UTANG biasanya memuat tahun sebelumnya dan tahun berjalan.
            # Cari kolomnya secara dinamis agar tidak bergantung pada posisi tetap.
            for scan_row in range(
                max(0, utang_row - 1),
                min(len(df), utang_row + 3),
            ):
                labels = [
                    self._label(df.iat[scan_row, col])
                    for col in range(df.shape[1])
                ]
                if current_year and str(current_year) in labels:
                    current_col = labels.index(str(current_year))
                if previous_year and str(previous_year) in labels:
                    previous_col = labels.index(str(previous_year))

            # Jangan batasi 11 baris. Pada workbook riil blok Utang bisa lebih
            # panjang; cari TOTAL sampai blok berikutnya/akhir sheet.
            for row in range(utang_row + 1, min(len(df), utang_row + 80)):
                row_labels = {
                    self._label(df.iat[row, col])
                    for col in range(min(df.shape[1], 4))
                }
                if "total" in row_labels:
                    total_row = row
                    break
                if any(
                    label.startswith("perhitungan penghasilan")
                    for label in row_labels
                ):
                    break

            if total_row is not None:
                # Ambil detail Utang untuk Lampiran IV. Kolom 1/2 adalah fallback
                # struktur SIMULASI lama (Kode Utang / Nama Pemberi Pinjaman).
                # Kolom alamat/tahun hanya diisi bila header eksplisit tersedia;
                # parser tidak menebak isi kolom yang tidak berlabel.
                header_map = {}
                for scan_row in range(max(0, utang_row - 2), min(len(df), utang_row + 3)):
                    for col in range(df.shape[1]):
                        label = self._label(df.iat[scan_row, col])
                        if label:
                            header_map.setdefault(label, col)

                code_col = next(
                    (header_map[key] for key in ("kode utang", "kode") if key in header_map),
                    1 if df.shape[1] > 1 else 0,
                )
                name_col = next(
                    (
                        header_map[key]
                        for key in ("nama pemberi pinjaman", "nama pinjaman", "nama utang")
                        if key in header_map
                    ),
                    2 if df.shape[1] > 2 else code_col,
                )
                address_col = next(
                    (
                        header_map[key]
                        for key in ("alamat pemberi pinjaman", "alamat pinjaman", "alamat")
                        if key in header_map
                    ),
                    None,
                )
                loan_year_col = next(
                    (
                        header_map[key]
                        for key in ("tahun pinjaman", "tahun peminjaman")
                        if key in header_map
                    ),
                    None,
                )

                effective_current_col = current_col
                if effective_current_col is None and df.shape[1] > 9:
                    effective_current_col = 9

                for detail_row in range(utang_row + 1, total_row):
                    code = self._text(df.iat[detail_row, code_col]) if code_col < df.shape[1] else ""
                    name = self._text(df.iat[detail_row, name_col]) if name_col < df.shape[1] else ""
                    address = (
                        self._text(df.iat[detail_row, address_col])
                        if address_col is not None and address_col < df.shape[1]
                        else ""
                    )
                    loan_year = (
                        int(self._number(df.iat[detail_row, loan_year_col]))
                        if loan_year_col is not None and loan_year_col < df.shape[1]
                        else 0
                    )
                    amount = (
                        self._number(df.iat[detail_row, effective_current_col])
                        if effective_current_col is not None and effective_current_col < df.shape[1]
                        else 0.0
                    )
                    if any((code, name, address, loan_year, amount)):
                        utang_rows.append(
                            {
                                "kode_utang": code,
                                "nama_pemberi_pinjaman": name,
                                "alamat_pemberi_pinjaman": address,
                                "tahun_pinjaman": loan_year,
                                "jumlah": float(amount or 0),
                            }
                        )

                if previous_col is None and df.shape[1] > 8:
                    previous_col = 8
                if current_col is None and df.shape[1] > 9:
                    current_col = 9

                if previous_col is not None and previous_col < df.shape[1]:
                    state["utang_sebelumnya"] = self._number(
                        df.iat[total_row, previous_col]
                    )
                if current_col is not None and current_col < df.shape[1]:
                    state["utang_berjalan"] = self._number(
                        df.iat[total_row, current_col]
                    )

        result.pph_components["utang_rows"] = utang_rows

        # Nilai ini berbeda dari Penghasilan Neto Gabungan pada blok PPh.
        # Blok ANALISIS memakai nilai presisi (sebelum pembulatan pajak) untuk
        # mencocokkan Total Pengeluaran, mis. 337.160.131 vs 337.160.000.
        for row in range(len(df)):
            row_labels = [
                self._label(df.iat[row, col])
                for col in range(min(df.shape[1], 6))
            ]
            if any(
                label.startswith("penghasilan netto")
                and "gabungan" not in label
                for label in row_labels
            ):
                value = 0.0
                candidate_columns = []
                if current_col is not None:
                    candidate_columns.append(current_col)
                candidate_columns.extend((9, 10, 8, 7, 6))
                seen_columns = set()
                for col in candidate_columns:
                    if col in seen_columns or col >= df.shape[1]:
                        continue
                    seen_columns.add(col)
                    candidate = df.iat[row, col]
                    if not pd.isna(candidate) and candidate != "":
                        value = self._number(candidate)
                        break
                if value:
                    state["penghasilan_netto_analisis"] = value
                    break

        label_map = {
            "pengeluaran lain-lain": "pengeluaran_lain_lain",
            "kerugian (keuntungan) penjualan aset": "kerugian_keuntungan_penjualan_aset",
            "utang baru atas kredit": "utang_baru_atas_kredit",
            "harta baru dari kredit": "harta_baru_dari_kredit",
            "penambahan penghasilan bruto umkm": "penambahan_penghasilan_bruto_umkm",
            "margin usaha": "margin_usaha",
        }
        for row in range(len(df)):
            labels = [self._label(df.iat[row, col]) for col in range(min(df.shape[1], 3))]
            for label, key in label_map.items():
                if label in labels:
                    value = 0.0
                    for col in (9, 10, 8, 7, 6):
                        if col < df.shape[1]:
                            candidate = df.iat[row, col]
                            if not pd.isna(candidate) and candidate != "":
                                value = self._number(candidate)
                                break
                    state[key] = value

        result.pph_components["reconciliation"] = state
