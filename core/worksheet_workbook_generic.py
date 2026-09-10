from __future__ import annotations

import re
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd

from core.legacy_mapping import CORETAX_TO_EFORM
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_workbook_importer import (
    WorksheetWorkbookImportIssue,
    WorksheetWorkbookImporter,
)


class GenericWorksheetWorkbookImporter(WorksheetWorkbookImporter):
    """Importer worksheet generik untuk variasi file WP dengan struktur sejenis.

    EVY tetap menjadi golden reference, tetapi parser tidak bergantung pada nama
    WP, nama file, atau posisi kolom tetap. Header dikenali melalui alias dan
    pemilihan blok tabel didasarkan pada kelengkapan struktur + keberadaan data.
    """

    HEADER_ALIASES = {
        "jenis": {
            "jenis", "jenis bupot", "jenis bukti potong", "jenis pajak",
        },
        "npwp_pemberi_kerja": {
            "npwp pemberi kerja", "npwp pemotong", "npwp pemungut",
            "npwp pemberi penghasilan", "npwp pemberi kerja/pemotong",
        },
        "no_bupot": {
            "no bupot", "nomor bupot", "nomor bukti potong", "no bukti potong",
            "nomor bukti pemotongan", "no bukti pemotongan",
        },
        "bruto": {
            "bruto", "penghasilan bruto", "jumlah bruto", "penghasilan kotor",
        },
        "pengurang": {
            "pengurang", "pengurang bruto", "biaya pengurang", "pengurang penghasilan bruto",
        },
        "pph_dipotong": {
            "pph dipotong", "pph dipungut", "pph dipotong/dipungut",
            "pph dipotong / dipungut", "jumlah pph", "jumlah pph dipotong",
            "jumlah pph dipungut", "jumlah pph dipotong/dipungut",
            "kredit pajak", "pph terpotong",
        },
        "kode_ct": {"kode ct", "kode coretax", "kode harta ct", "kode harta coretax"},
        "kode_eform": {"kode eform", "kode e-form", "kode lama", "kode harta eform"},
        "nama_harta": {"nama harta", "uraian harta", "jenis harta"},
        "tahun_perolehan": {"th perolehan", "tahun perolehan", "tahun diperoleh"},
        "nomor_akun_keterangan": {
            "nomor akun / keterangan", "nomor akun/keterangan", "nomor akun",
            "no akun", "rekening / keterangan", "rekening/keterangan", "keterangan",
        },
        "atas_nama": {"atas nama", "a/n", "an"},
        "nama_bank": {"nama bank", "bank", "nama lembaga"},
    }

    IDENTITY_ALIASES = {
        "nama_wp": {"nama", "nama wp", "nama wajib pajak", "wajib pajak"},
        "npwp": {"npwp", "npwp wp", "npwp wajib pajak"},
    }

    @classmethod
    def _canonical_header(cls, value: object) -> str:
        label = cls._label(value)
        for canonical, aliases in cls.HEADER_ALIASES.items():
            if label in aliases:
                return canonical
        return label

    @classmethod
    def _identity_key(cls, value: object) -> Optional[str]:
        label = cls._label(value).rstrip(":")
        for key, aliases in cls.IDENTITY_ALIASES.items():
            if label in aliases:
                return key
        return None

    @staticmethod
    def _find_year_sheet(sheet_names) -> Optional[str]:
        candidates = []
        for name in sheet_names:
            text = str(name).strip()
            match = re.search(r"\b(20\d{2})\b", text)
            if match:
                candidates.append((int(match.group(1)), text))
        if not candidates:
            return None
        year, _ = max(candidates, key=lambda item: item[0])
        return str(year)

    def parse(self, file_path):
        path = file_path
        try:
            excel = pd.ExcelFile(path)
        except Exception:
            return super().parse(path)

        year = self._find_year_sheet(excel.sheet_names)
        if year and year not in excel.sheet_names:
            original_name = next(
                (name for name in excel.sheet_names if re.search(rf"\b{year}\b", str(name))),
                None,
            )
            if original_name is not None:
                original_read_excel = pd.read_excel

                def read_excel_with_alias(source, *args, **kwargs):
                    if kwargs.get("sheet_name") == year:
                        kwargs["sheet_name"] = original_name
                    return original_read_excel(source, *args, **kwargs)

                original_excel_file = pd.ExcelFile

                class _ExcelProxy:
                    def __init__(self, names):
                        self.sheet_names = [year if n == original_name else n for n in names]

                try:
                    pd.read_excel = read_excel_with_alias
                    pd.ExcelFile = lambda source: _ExcelProxy(excel.sheet_names)
                    return super().parse(path)
                finally:
                    pd.read_excel = original_read_excel
                    pd.ExcelFile = original_excel_file
        return super().parse(path)

    def _parse_identity(self, df, result):
        max_rows = min(len(df), 25)
        max_cols = min(df.shape[1], 12)
        for row in range(max_rows):
            for col in range(max_cols):
                key = self._identity_key(df.iat[row, col])
                if key is None:
                    continue
                for value_col in range(col + 1, min(df.shape[1], col + 6)):
                    candidate = self._text(df.iat[row, value_col])
                    if not candidate or candidate == ":":
                        continue
                    if key == "npwp":
                        candidate = self._digits(candidate)
                    if candidate:
                        setattr(result, key, candidate)
                        break

    def _candidate_header_blocks(self, df) -> Iterable[Tuple[int, Dict[str, int]]]:
        required = {"jenis", "npwp_pemberi_kerja", "no_bupot", "bruto", "pengurang"}
        supported = required | {"pph_dipotong"}
        for row in range(len(df)):
            canonical_by_col = {
                col: self._canonical_header(df.iat[row, col])
                for col in range(df.shape[1])
                if self._text(df.iat[row, col])
            }
            anchor_cols = [col for col, key in canonical_by_col.items() if key == "jenis"]
            for anchor in anchor_cols:
                window = range(max(0, anchor - 1), min(df.shape[1], anchor + 12))
                mapping = {}
                for col in window:
                    key = canonical_by_col.get(col)
                    if key in supported and key not in mapping:
                        mapping[key] = col
                if required.issubset(mapping):
                    yield row, mapping

    def _bupot_row_is_terminator(self, df, row: int, headers: Dict[str, int]) -> bool:
        """Deteksi akhir tabel pada area blok, termasuk kolom NO di sebelah kiri.

        Sebagian template menaruh TOTAL pada kolom yang bukan salah satu header inti
        Bupot. Karena itu pemeriksaan tidak boleh hanya dilakukan pada kolom
        JENIS/NPWP/NO BUPOT/BRUTO/PENGURANG.
        """
        left = max(0, min(headers.values()) - 2)
        right = min(df.shape[1], max(headers.values()) + 2)
        labels = [self._label(df.iat[row, col]) for col in range(left, right)]
        return any(label == "total" or label.startswith("total ") for label in labels)

    def _score_bupot_block(self, df, header_row: int, headers: Dict[str, int]) -> int:
        score = 0
        for row in range(header_row + 1, min(len(df), header_row + 80)):
            if self._bupot_row_is_terminator(df, row, headers):
                break
            jenis = self._text(df.iat[row, headers["jenis"]])
            npwp = self._digits(df.iat[row, headers["npwp_pemberi_kerja"]])
            no_bupot = self._text(df.iat[row, headers["no_bupot"]])
            bruto = self._number(df.iat[row, headers["bruto"]])
            pengurang = self._number(df.iat[row, headers["pengurang"]])
            pph_dipotong = (
                self._number(df.iat[row, headers["pph_dipotong"]])
                if "pph_dipotong" in headers
                else 0.0
            )
            if any((jenis, npwp, no_bupot, bruto, pengurang, pph_dipotong)):
                score += 1
                if npwp:
                    score += 2
                if no_bupot:
                    score += 2
                if bruto or pengurang:
                    score += 1
                if pph_dipotong:
                    score += 1
        return score

    def _parse_bupot(self, df, result):
        candidates = []
        for header_row, headers in self._candidate_header_blocks(df):
            candidates.append((self._score_bupot_block(df, header_row, headers), header_row, headers))

        if not candidates:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_104", "WARNING",
                    "Tabel Bupot tidak ditemukan. Parser sudah mencoba alias header umum.",
                )
            )
            return

        score, header_row, headers = max(candidates, key=lambda item: (item[0], -item[1]))
        if score <= 0:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_105", "WARNING",
                    "Struktur tabel Bupot ditemukan tetapi tidak ada baris data yang dapat dibaca.",
                )
            )
            return

        for row in range(header_row + 1, len(df)):
            if self._bupot_row_is_terminator(df, row, headers):
                break
            jenis = self._text(df.iat[row, headers["jenis"]])
            npwp = self._digits(df.iat[row, headers["npwp_pemberi_kerja"]])
            no_bupot = self._text(df.iat[row, headers["no_bupot"]])
            bruto = self._number(df.iat[row, headers["bruto"]])
            pengurang = self._number(df.iat[row, headers["pengurang"]])
            pph_dipotong = (
                self._number(df.iat[row, headers["pph_dipotong"]])
                if "pph_dipotong" in headers
                else 0.0
            )
            if not any((jenis, npwp, no_bupot, bruto, pengurang, pph_dipotong)):
                continue
            result.bupot_rows.append(
                self._make_bupot_row(
                    jenis,
                    npwp,
                    no_bupot,
                    bruto,
                    pengurang,
                    pph_dipotong,
                )
            )

    @staticmethod
    def _make_bupot_row(jenis, npwp, no_bupot, bruto, pengurang, pph_dipotong=0.0):
        from core.worksheet_pph_state import WorksheetBupotRow
        return WorksheetBupotRow(
            jenis=jenis,
            npwp_pemberi_kerja=npwp,
            no_bupot=no_bupot,
            bruto=bruto,
            pengurang=pengurang,
            pph_dipotong=pph_dipotong,
        )

    def _parse_harta(self, df, result):
        header_row = None
        headers = None
        previous_name = str(result.tahun_pajak - 1)
        current_name = str(result.tahun_pajak)

        for row in range(len(df)):
            mapping = {}
            for col in range(df.shape[1]):
                raw = self._text(df.iat[row, col])
                if not raw:
                    continue
                canonical = self._canonical_header(raw)
                if canonical in self.HEADER_ALIASES:
                    mapping.setdefault(canonical, col)
                normalized = self._label(raw)
                if normalized in {previous_name, current_name}:
                    mapping[normalized] = col
            required = {"kode_ct", "nama_harta", "tahun_perolehan", previous_name, current_name}
            if required.issubset(mapping):
                header_row, headers = row, mapping
                break

        if header_row is None or headers is None:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_008", "ERROR",
                    "Header Harta pada SIMULASI I tidak ditemukan dengan alias yang didukung.",
                )
            )
            return

        for row in range(header_row + 1, len(df)):
            labels = [self._label(df.iat[row, col]) for col in range(min(df.shape[1], 4))]
            if any(label.startswith("total harta") or label == "utang" for label in labels):
                break
            code_ct = self._text(df.iat[row, headers["kode_ct"]])
            name = self._text(df.iat[row, headers["nama_harta"]])
            if not code_ct and not name:
                continue
            code_eform = ""
            if "kode_eform" in headers:
                code_eform = self._text(df.iat[row, headers["kode_eform"]])
            if not code_eform:
                code_eform = CORETAX_TO_EFORM.get(code_ct, "")

            def cell(key, default=""):
                col = headers.get(key)
                return default if col is None else self._text(df.iat[row, col])

            result.harta_rows.append(
                WorksheetHartaRow(
                    nomor=len(result.harta_rows) + 1,
                    kode_eform=code_eform,
                    kode_ct=code_ct,
                    nama_harta=name,
                    nomor_akun_keterangan=cell("nomor_akun_keterangan"),
                    atas_nama=cell("atas_nama"),
                    nama_bank=cell("nama_bank"),
                    tahun_perolehan=int(
                        self._number(df.iat[row, headers["tahun_perolehan"]], default=result.tahun_pajak)
                        or result.tahun_pajak
                    ),
                    nilai_tahun_sebelumnya=self._number(df.iat[row, headers[previous_name]]),
                    nilai_tahun_berjalan=self._number(df.iat[row, headers[current_name]]),
                )
            )