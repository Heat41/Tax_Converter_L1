from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from core.finalization import FinalizationInput
from core.worksheet_pph_state import WorksheetBupotRow
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow


ROUNDTRIP_SCHEMA = "TAX_CONVERTER_L1_LEGACY_XLSX_V1"
META_SHEET = "_TC_META"
DATA_HARTA_SHEET = "DATA REVISI - HARTA"
DATA_BUPOT_SHEET = "DATA REVISI - BUPOT"


@dataclass(frozen=True)
class LegacyXlsxIssue:
    code: str
    severity: str
    message: str


@dataclass
class LegacyXlsxExportResult:
    output_path: Path
    revision: int = 0
    snapshot_hash: str = ""
    sha256: str = ""
    issues: List[LegacyXlsxIssue] = field(default_factory=list)

    @property
    def errors(self):
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def ok(self) -> bool:
        return not self.errors and self.output_path.is_file()


@dataclass
class LegacyXlsxRoundTripResult:
    source_path: Path
    npwp: str = ""
    nama_wp: str = ""
    tahun_pajak: int = 0
    base_revision: int = 0
    base_snapshot_hash: str = ""
    harta_rows: List[WorksheetHartaRow] = field(default_factory=list)
    bupot_rows: List[WorksheetBupotRow] = field(default_factory=list)
    issues: List[LegacyXlsxIssue] = field(default_factory=list)

    @property
    def errors(self):
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def ok(self) -> bool:
        return bool(self.npwp and self.tahun_pajak) and not self.errors


class Legacy1770HybridXlsxService:
    """XLSX Format Lama HYBRID yang aman untuk round-trip revisi.

    Visual workbook:
    - 01-02: area e-Form baru.
    - 03 dst: area legacy/format lama.
    - DATA REVISI: canonical editable tables untuk Harta dan Bupot.
    - _TC_META: metadata tersembunyi untuk traceability snapshot/revision.

    Import revisi TIDAK menebak posisi field dari sheet visual; hanya canonical
    DATA REVISI yang dibaca. Dengan demikian perubahan user/client tetap stabil
    walau layout form visual berkembang.
    """

    HARTA_HEADERS = (
        "NO", "KODE EFORM", "KODE CT", "NAMA HARTA",
        "NOMOR AKUN / KETERANGAN", "ATAS NAMA", "NAMA BANK",
        "TH PEROLEHAN", "TAHUN SEBELUMNYA", "TAHUN BERJALAN",
    )
    BUPOT_HEADERS = (
        "NO", "JENIS BUPOT", "NO BUKPOT", "MASA", "TAHUN", "SIFAT", "STATUS",
        "NPWP PENERIMA", "NAMA PENERIMA", "FASILITAS", "JENIS PPH", "KOP",
        "BRUTO", "DPP PERSEN", "TARIF", "PENGURANG BRUTO", "PPH", "BUKTI",
        "NO BUKTI", "TANGGAL BUKTI", "NPWP PEMOTONG", "NAMA PEMOTONG",
        "TANGGAL PEMOTONGAN", "MEKANISME SP2D", "NO SP2D",
    )

    FORM_SHEETS = (
        ("01 eForm Induk", "NEW_EFORM", "FORMULIR 1770 - INDUK"),
        ("02 eForm Lamp I H1", "NEW_EFORM", "LAMPIRAN I - HALAMAN 1"),
        ("03 Legacy Lamp I H2", "LEGACY", "LAMPIRAN I - HALAMAN 2"),
        ("04 Legacy Lamp II", "LEGACY", "LAMPIRAN II"),
        ("05 Legacy Lamp III", "LEGACY", "LAMPIRAN III"),
        ("06 Legacy Lamp IV", "LEGACY", "LAMPIRAN IV"),
    )

    @staticmethod
    def _text(value) -> str:
        if value is None:
            return ""
        return " ".join(str(value).strip().split())

    @staticmethod
    def _number(value) -> float:
        if value in (None, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("Rp", "").replace(" ", "")
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif text.count(".") > 1:
            text = text.replace(".", "")
        elif "," in text:
            text = text.replace(",", ".")
        return float(text or 0)

    @staticmethod
    def _digits(value) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _style_header(ws, row: int, max_col: int) -> None:
        fill = PatternFill("solid", fgColor="D9EAF7")
        for col in range(1, max_col + 1):
            cell = ws.cell(row, col)
            cell.font = Font(bold=True)
            cell.fill = fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    @staticmethod
    def _setup_print(ws, orientation="portrait") -> None:
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = orientation
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.freeze_panes = "A2"

    def export(
        self,
        data: FinalizationInput,
        output_path: str | Path,
        *,
        revision: int,
        snapshot_hash: str,
    ) -> LegacyXlsxExportResult:
        target = Path(output_path)
        if target.suffix.lower() != ".xlsx":
            target = target.with_suffix(".xlsx")

        result = LegacyXlsxExportResult(
            output_path=target,
            revision=int(revision or 0),
            snapshot_hash=str(snapshot_hash or ""),
        )

        if not data.npwp or not data.tahun_pajak:
            result.issues.append(
                LegacyXlsxIssue("LX_001", "ERROR", "Identitas snapshot FINAL belum lengkap.")
            )
            return result

        wb = Workbook()
        wb.remove(wb.active)

        for title, mode, heading in self.FORM_SHEETS:
            ws = wb.create_sheet(title)
            self._render_form_sheet(ws, data, mode, heading, revision)

        self._write_harta_sheet(wb.create_sheet(DATA_HARTA_SHEET), data)
        self._write_bupot_sheet(wb.create_sheet(DATA_BUPOT_SHEET), data)
        self._write_meta_sheet(
            wb.create_sheet(META_SHEET),
            data,
            revision=revision,
            snapshot_hash=snapshot_hash,
        )

        wb[META_SHEET].sheet_state = "veryHidden"
        target.parent.mkdir(parents=True, exist_ok=True)
        wb.save(target)
        result.sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
        return result

    def _render_form_sheet(self, ws, data, mode: str, heading: str, revision: int) -> None:
        ws.merge_cells("A1:H1")
        ws["A1"] = heading
        ws["A1"].font = Font(size=14, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")

        ws.merge_cells("A2:H2")
        ws["A2"] = (
            "FORMAT BARU e-FORM" if mode == "NEW_EFORM"
            else "FORMAT LAMA / LEGACY DJP"
        )
        ws["A2"].font = Font(bold=True)
        ws["A2"].alignment = Alignment(horizontal="center")

        rows = [
            ("Nama Wajib Pajak", data.nama_wp),
            ("NPWP", str(data.npwp)),
            ("Tahun Pajak", data.tahun_pajak),
            ("Revision", revision),
            ("Status", "FINAL"),
        ]
        for offset, (label, value) in enumerate(rows, start=4):
            ws.cell(offset, 1).value = label
            ws.cell(offset, 2).value = value
            ws.cell(offset, 1).font = Font(bold=True)

        ws["A11"] = "CATATAN"
        ws["A11"].font = Font(bold=True)
        ws.merge_cells("A12:H14")
        if mode == "NEW_EFORM":
            ws["A12"] = (
                "Halaman ini mengikuti kelompok form baru e-Form. Data canonical "
                "untuk koreksi tersedia pada sheet DATA REVISI."
            )
        else:
            ws["A12"] = (
                "Halaman ini termasuk bagian legacy. Mulai Lampiran I Halaman 2 "
                "dan lampiran berikutnya menggunakan format lama."
            )
        ws["A12"].alignment = Alignment(wrap_text=True, vertical="top")

        for col in range(1, 9):
            ws.column_dimensions[get_column_letter(col)].width = 17
        self._setup_print(ws)

    def _write_harta_sheet(self, ws, data: FinalizationInput) -> None:
        ws.append(self.HARTA_HEADERS)
        self._style_header(ws, 1, len(self.HARTA_HEADERS))
        for index, row in enumerate(data.harta_current_rows, start=1):
            ws.append([
                index,
                row.kode_eform,
                row.kode_ct,
                row.nama_harta,
                row.nomor_akun_keterangan,
                row.atas_nama,
                row.nama_bank,
                row.tahun_perolehan,
                float(row.nilai_tahun_sebelumnya or 0),
                float(row.nilai_tahun_berjalan or 0),
            ])
        for column in range(1, len(self.HARTA_HEADERS) + 1):
            ws.column_dimensions[get_column_letter(column)].width = 20
        ws.column_dimensions["D"].width = 34
        ws.column_dimensions["E"].width = 30
        self._setup_print(ws, "landscape")

    def _write_bupot_sheet(self, ws, data: FinalizationInput) -> None:
        ws.append(self.BUPOT_HEADERS)
        self._style_header(ws, 1, len(self.BUPOT_HEADERS))
        for index, row in enumerate(data.bupot_rows, start=1):
            ws.append([
                index,
                row.jenis,
                row.no_bupot,
                row.masa,
                row.tahun,
                row.sifat,
                row.status,
                row.npwp_penerima,
                row.nama_penerima,
                row.fasilitas,
                row.jenis_pph,
                row.kop,
                float(row.bruto or 0),
                float(row.dpp_persen or 0),
                float(row.tarif or 0),
                float(row.pengurang or 0),
                float(row.pph_dipotong or 0),
                row.bukti,
                row.no_bukti,
                row.tanggal_bukti,
                row.npwp_pemotong or row.npwp_pemberi_kerja,
                row.nama_pemotong,
                row.tanggal_pemotongan,
                row.mekanisme_sp2d,
                row.no_sp2d,
            ])
        for column in range(1, len(self.BUPOT_HEADERS) + 1):
            ws.column_dimensions[get_column_letter(column)].width = 18
        self._setup_print(ws, "landscape")

    def _write_meta_sheet(
        self,
        ws,
        data: FinalizationInput,
        *,
        revision: int,
        snapshot_hash: str,
    ) -> None:
        meta = {
            "schema": ROUNDTRIP_SCHEMA,
            "npwp": str(data.npwp),
            "nama_wp": str(data.nama_wp),
            "tahun_pajak": int(data.tahun_pajak),
            "base_revision": int(revision or 0),
            "base_snapshot_hash": str(snapshot_hash or ""),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "harta_original_hash": str(data.harta_original_hash or ""),
        }
        ws["A1"] = "KEY"
        ws["B1"] = "VALUE"
        for row, (key, value) in enumerate(meta.items(), start=2):
            ws.cell(row, 1).value = key
            ws.cell(row, 2).value = value
        ws["D1"] = "JSON"
        ws["D2"] = json.dumps(meta, ensure_ascii=False, sort_keys=True)

    def import_revision(
        self,
        file_path: str | Path,
        *,
        expected_npwp: Optional[str] = None,
        expected_year: Optional[int] = None,
        expected_snapshot_hash: Optional[str] = None,
    ) -> LegacyXlsxRoundTripResult:
        path = Path(file_path)
        result = LegacyXlsxRoundTripResult(source_path=path)
        if not path.is_file():
            result.issues.append(LegacyXlsxIssue("LX_101", "ERROR", "File Excel revisi tidak ditemukan."))
            return result

        try:
            wb = load_workbook(path, data_only=False)
        except Exception as exc:
            result.issues.append(LegacyXlsxIssue("LX_102", "ERROR", f"Workbook tidak dapat dibaca: {exc}"))
            return result

        required = {META_SHEET, DATA_HARTA_SHEET, DATA_BUPOT_SHEET}
        missing = sorted(required - set(wb.sheetnames))
        if missing:
            result.issues.append(
                LegacyXlsxIssue(
                    "LX_103", "ERROR",
                    "Workbook bukan hasil round-trip Tax Converter atau sheet canonical hilang: "
                    + ", ".join(missing),
                )
            )
            return result

        meta_ws = wb[META_SHEET]
        meta = {}
        for row in range(2, meta_ws.max_row + 1):
            key = self._text(meta_ws.cell(row, 1).value)
            if key:
                meta[key] = meta_ws.cell(row, 2).value

        if self._text(meta.get("schema")) != ROUNDTRIP_SCHEMA:
            result.issues.append(LegacyXlsxIssue("LX_104", "ERROR", "Versi schema round-trip tidak dikenali."))
            return result

        result.npwp = self._digits(meta.get("npwp"))
        result.nama_wp = self._text(meta.get("nama_wp"))
        result.tahun_pajak = int(self._number(meta.get("tahun_pajak")))
        result.base_revision = int(self._number(meta.get("base_revision")))
        result.base_snapshot_hash = self._text(meta.get("base_snapshot_hash"))

        if expected_npwp and self._digits(expected_npwp) != result.npwp:
            result.issues.append(LegacyXlsxIssue("LX_105", "ERROR", "NPWP workbook revisi tidak sesuai dengan WP aktif."))
        if expected_year and int(expected_year) != result.tahun_pajak:
            result.issues.append(LegacyXlsxIssue("LX_106", "ERROR", "Tahun Pajak workbook revisi tidak sesuai dengan Worksheet aktif."))
        if expected_snapshot_hash and str(expected_snapshot_hash) != result.base_snapshot_hash:
            result.issues.append(
                LegacyXlsxIssue(
                    "LX_107", "ERROR",
                    "Workbook revisi bukan berasal dari snapshot FINAL aktif yang diharapkan.",
                )
            )
        if result.errors:
            return result

        self._read_harta(wb[DATA_HARTA_SHEET], result)
        self._read_bupot(wb[DATA_BUPOT_SHEET], result)
        return result

    def _read_harta(self, ws, result: LegacyXlsxRoundTripResult) -> None:
        headers = {
            self._text(ws.cell(1, col).value).upper(): col
            for col in range(1, ws.max_column + 1)
        }
        for required in self.HARTA_HEADERS:
            if required not in headers:
                result.issues.append(LegacyXlsxIssue("LX_108", "ERROR", f"Kolom Harta '{required}' hilang."))
                return

        for row in range(2, ws.max_row + 1):
            name = self._text(ws.cell(row, headers["NAMA HARTA"]).value)
            code_ct = self._text(ws.cell(row, headers["KODE CT"]).value)
            if not name and not code_ct:
                continue
            try:
                result.harta_rows.append(
                    WorksheetHartaRow(
                        nomor=len(result.harta_rows) + 1,
                        kode_eform=self._text(ws.cell(row, headers["KODE EFORM"]).value),
                        kode_ct=code_ct,
                        nama_harta=name,
                        nomor_akun_keterangan=self._text(ws.cell(row, headers["NOMOR AKUN / KETERANGAN"]).value),
                        atas_nama=self._text(ws.cell(row, headers["ATAS NAMA"]).value),
                        nama_bank=self._text(ws.cell(row, headers["NAMA BANK"]).value),
                        tahun_perolehan=int(self._number(ws.cell(row, headers["TH PEROLEHAN"]).value)),
                        nilai_tahun_sebelumnya=self._number(ws.cell(row, headers["TAHUN SEBELUMNYA"]).value),
                        nilai_tahun_berjalan=self._number(ws.cell(row, headers["TAHUN BERJALAN"]).value),
                    )
                )
            except (TypeError, ValueError) as exc:
                result.issues.append(
                    LegacyXlsxIssue("LX_109", "ERROR", f"Baris Harta {row} tidak valid: {exc}")
                )

    def _read_bupot(self, ws, result: LegacyXlsxRoundTripResult) -> None:
        headers = {
            self._text(ws.cell(1, col).value).upper(): col
            for col in range(1, ws.max_column + 1)
        }
        for required in self.BUPOT_HEADERS:
            if required not in headers:
                result.issues.append(LegacyXlsxIssue("LX_110", "ERROR", f"Kolom Bupot '{required}' hilang."))
                return

        def text(row, key):
            return self._text(ws.cell(row, headers[key]).value)

        def number(row, key):
            return self._number(ws.cell(row, headers[key]).value)

        for row in range(2, ws.max_row + 1):
            jenis = text(row, "JENIS BUPOT")
            no_bupot = text(row, "NO BUKPOT")
            if not any((jenis, no_bupot, number(row, "BRUTO"), number(row, "PPH"))):
                continue
            npwp_pemotong = self._digits(text(row, "NPWP PEMOTONG"))
            try:
                result.bupot_rows.append(
                    WorksheetBupotRow(
                        jenis=jenis,
                        no_bupot=no_bupot,
                        masa=text(row, "MASA"),
                        tahun=text(row, "TAHUN"),
                        sifat=text(row, "SIFAT"),
                        status=text(row, "STATUS"),
                        npwp_penerima=self._digits(text(row, "NPWP PENERIMA")),
                        nama_penerima=text(row, "NAMA PENERIMA"),
                        fasilitas=text(row, "FASILITAS"),
                        jenis_pph=text(row, "JENIS PPH"),
                        kop=text(row, "KOP"),
                        bruto=number(row, "BRUTO"),
                        dpp_persen=number(row, "DPP PERSEN"),
                        tarif=number(row, "TARIF"),
                        pengurang=number(row, "PENGURANG BRUTO"),
                        pph_dipotong=number(row, "PPH"),
                        bukti=text(row, "BUKTI"),
                        no_bukti=text(row, "NO BUKTI"),
                        tanggal_bukti=text(row, "TANGGAL BUKTI"),
                        npwp_pemotong=npwp_pemotong,
                        nama_pemotong=text(row, "NAMA PEMOTONG"),
                        tanggal_pemotongan=text(row, "TANGGAL PEMOTONGAN"),
                        mekanisme_sp2d=text(row, "MEKANISME SP2D"),
                        no_sp2d=text(row, "NO SP2D"),
                        npwp_pemberi_kerja=npwp_pemotong,
                    )
                )
            except (TypeError, ValueError) as exc:
                result.issues.append(
                    LegacyXlsxIssue("LX_111", "ERROR", f"Baris Bupot {row} tidak valid: {exc}")
                )
