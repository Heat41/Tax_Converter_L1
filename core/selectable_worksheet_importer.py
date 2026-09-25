from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pandas as pd

from core.legacy_mapping import CORETAX_TO_EFORM
from core.mapping.harta_mapper import HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.pipeline.harta_pipeline import HartaPipelineResult
from core.worksheet_workbook_generic import GenericWorksheetWorkbookImporter
from core.worksheet_workbook_importer import (
    WorksheetWorkbookImportIssue,
    WorksheetWorkbookImportResult,
)


class SelectableWorksheetWorkbookImporter(GenericWorksheetWorkbookImporter):
    """Importer Kertas Kerja dengan sheet utama dipilih user.

    Auto-detect hanya dipakai untuk memberi saran awal di UI. Parsing selalu
    memakai sheet yang dipilih user, sedangkan SIMULASI I tetap menjadi sumber Harta.
    """

    def list_sheets(self, file_path: str | Path) -> List[str]:
        path = Path(file_path)
        with pd.ExcelFile(path) as excel:
            return [str(name) for name in excel.sheet_names]

    @staticmethod
    def suggested_sheet(sheet_names: List[str]) -> str:
        candidates = []
        for name in sheet_names:
            match = re.search(r"\b(20\d{2})\b", str(name))
            if match:
                candidates.append((int(match.group(1)), str(name)))
        return max(candidates, default=(0, ""))[1]

    def parse_selected(
        self,
        file_path: str | Path,
        sheet_name: str,
    ) -> WorksheetWorkbookImportResult:
        path = Path(file_path)
        result = WorksheetWorkbookImportResult(source_path=path)

        if not path.exists():
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_001", "ERROR", "File kertas kerja tidak ditemukan.")
            )
            return result
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_002", "ERROR", "Kertas kerja harus berupa file Excel .xlsx/.xls.")
            )
            return result

        try:
            with pd.ExcelFile(path) as excel:
                sheet_names = list(excel.sheet_names)
                if sheet_name not in sheet_names:
                    result.issues.append(
                        WorksheetWorkbookImportIssue(
                            "WKI_004",
                            "ERROR",
                            f"Sheet '{sheet_name}' tidak ditemukan pada workbook.",
                        )
                    )
                    return result

                annual = pd.read_excel(
                    excel,
                    sheet_name=sheet_name,
                    header=None,
                    dtype=object,
                )
                simulasi_name = next(
                    (
                        name
                        for name in sheet_names
                        if str(name).strip().casefold() == "simulasi i"
                    ),
                    None,
                )
                simulasi = (
                    pd.read_excel(
                        excel,
                        sheet_name=simulasi_name,
                        header=None,
                        dtype=object,
                    )
                    if simulasi_name is not None
                    else None
                )
        except Exception as exc:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_003",
                    "ERROR",
                    f"Workbook/sheet tidak dapat dibaca: {exc}",
                )
            )
            return result

        result.tahun_pajak = self._detect_year(sheet_name, annual)
        if not result.tahun_pajak:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_004",
                    "ERROR",
                    "Tahun pajak tidak dapat dikenali dari sheet yang dipilih.",
                )
            )
            return result

        self._parse_identity(annual, result)
        # Kertas Kerja tidak lagi menjadi sumber Bupot utama.
        self._parse_pph_components(annual, result)

        if simulasi is not None:
            self._parse_simulasi_identity(simulasi, result)
            self._parse_harta(simulasi, result)
            self._parse_reconciliation(simulasi, result)
        else:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_101",
                    "WARNING",
                    "Sheet SIMULASI I tidak ditemukan. Harta harus dilengkapi di aplikasi.",
                )
            )

        if not result.npwp:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_005", "ERROR", "NPWP tidak ditemukan pada kertas kerja.")
            )
        if not result.nama_wp:
            result.issues.append(
                WorksheetWorkbookImportIssue("WKI_102", "WARNING", "Nama Wajib Pajak tidak ditemukan pada kertas kerja.")
            )

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
                    "Tidak ada baris Harta pada SIMULASI I.",
                )
            )

        return result


    def _parse_harta(self, df, result):
        """Parse SIMULASI I secara fleksibel.

        Tidak bergantung pada posisi kolom tetap. Header dikenali lewat alias,
        tahun pajak, dan pola isi data. Jika struktur tidak dapat dikenali,
        Harta menjadi warning (bukan error) agar Kertas Kerja tetap bisa masuk.
        """
        current_year = int(result.tahun_pajak or 0)
        previous_year = current_year - 1 if current_year else 0
        current_name = str(current_year) if current_year else ""
        previous_name = str(previous_year) if previous_year else ""

        header_candidates = []
        scan_rows = min(len(df), 80)

        for row in range(scan_rows):
            mapping = {}
            for col in range(df.shape[1]):
                raw = self._text(df.iat[row, col])
                if not raw:
                    continue

                canonical = self._canonical_header(raw)
                if canonical in self.HEADER_ALIASES:
                    mapping.setdefault(canonical, col)

                normalized = self._label(raw)
                year_match = re.search(r"\b(20\d{2})\b", normalized)
                if year_match:
                    mapping.setdefault(year_match.group(1), col)

            score = 0
            for key in (
                "kode_ct",
                "nama_harta",
                "tahun_perolehan",
                "nomor_akun_keterangan",
                "atas_nama",
                "nama_bank",
            ):
                if key in mapping:
                    score += 1
            if current_name and current_name in mapping:
                score += 3
            if previous_name and previous_name in mapping:
                score += 2

            if score:
                header_candidates.append((score, row, mapping))

        if header_candidates:
            _, header_row, headers = max(header_candidates, key=lambda item: (item[0], -item[1]))
        else:
            header_row, headers = self._infer_harta_structure(df, result)

        if header_row is None or not headers:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_008",
                    "WARNING",
                    "Struktur Harta pada SIMULASI I belum dapat dikenali otomatis. "
                    "Kertas Kerja tetap dapat diimpor dan Harta dapat dilengkapi di aplikasi.",
                )
            )
            return

        # Lengkapi kolom penting dari pola isi apabila header tidak lengkap.
        inferred_row, inferred = self._infer_harta_structure(
            df,
            result,
            preferred_header_row=header_row,
        )
        if inferred:
            for key, col in inferred.items():
                headers.setdefault(key, col)
            if inferred_row is not None:
                header_row = min(header_row, inferred_row)

        code_col = headers.get("kode_ct")
        name_col = headers.get("nama_harta")
        current_col = headers.get(current_name)
        previous_col = headers.get(previous_name)

        # Minimal untuk membentuk baris Harta adalah kode/nama + nilai tahun berjalan.
        if current_col is None or (code_col is None and name_col is None):
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_008",
                    "WARNING",
                    "Kolom Harta ditemukan sebagian, tetapi kode/nama atau nilai tahun berjalan "
                    "belum dapat dikenali. Import Kertas Kerja tetap dilanjutkan.",
                )
            )
            return

        start_row = header_row + 1
        empty_streak = 0

        for row in range(start_row, len(df)):
            labels = [
                self._label(df.iat[row, col])
                for col in range(min(df.shape[1], 6))
            ]
            if any(
                label.startswith("total harta")
                or label == "utang"
                or label.startswith("total aset")
                for label in labels
            ):
                break

            code_ct = self._text(df.iat[row, code_col]) if code_col is not None else ""
            name = self._text(df.iat[row, name_col]) if name_col is not None else ""
            current_value = self._number(df.iat[row, current_col]) if current_col is not None else 0.0
            previous_value = self._number(df.iat[row, previous_col]) if previous_col is not None else 0.0

            if not any((code_ct, name, current_value, previous_value)):
                empty_streak += 1
                if empty_streak >= 8 and result.harta_rows:
                    break
                continue

            # Nilai tahun saja tidak cukup untuk membuktikan bahwa baris ini
            # adalah Harta. Bagian Penghasilan di atas tabel SIMULASI dapat
            # memiliki angka pada kolom tahun yang sama. Wajib ada identitas
            # aset pada KODE CT atau NAMA HARTA.
            if not code_ct and not name:
                continue

            empty_streak = 0

            # Abaikan baris judul/subtotal yang kebetulan berada di area data.
            if code_ct and not self._looks_like_coretax_code(code_ct):
                if not name and not current_value and not previous_value:
                    continue

            code_eform = ""
            eform_col = headers.get("kode_eform")
            if eform_col is not None:
                code_eform = self._text(df.iat[row, eform_col])
            if not code_eform and code_ct:
                code_eform = CORETAX_TO_EFORM.get(code_ct, "")

            def text_cell(key: str) -> str:
                col = headers.get(key)
                if col is None:
                    return ""
                return self._text(df.iat[row, col])

            acquisition_year = current_year
            year_col = headers.get("tahun_perolehan")
            if year_col is not None:
                parsed_year = int(self._number(df.iat[row, year_col], default=current_year) or current_year)
                if 1900 <= parsed_year <= 2100:
                    acquisition_year = parsed_year

            result.harta_rows.append(
                WorksheetHartaRow(
                    nomor=len(result.harta_rows) + 1,
                    kode_eform=code_eform,
                    kode_ct=code_ct,
                    nama_harta=name,
                    nomor_akun_keterangan=text_cell("nomor_akun_keterangan"),
                    atas_nama=text_cell("atas_nama"),
                    nama_bank=text_cell("nama_bank"),
                    tahun_perolehan=acquisition_year,
                    nilai_tahun_sebelumnya=previous_value,
                    nilai_tahun_berjalan=current_value,
                )
            )

        if result.harta_rows and (
            "kode_ct" not in headers
            or "nama_harta" not in headers
            or "tahun_perolehan" not in headers
        ):
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_108",
                    "WARNING",
                    "SIMULASI I dibaca dengan deteksi fleksibel. Beberapa kolom tidak memiliki "
                    "header standar dan diisi dari pola data/default.",
                )
            )

    def _infer_harta_structure(self, df, result, preferred_header_row=None):
        current_year = int(result.tahun_pajak or 0)
        previous_year = current_year - 1 if current_year else 0
        headers = {}

        candidate_rows = []
        for row in range(min(len(df), 100)):
            year_cols = {}
            for col in range(df.shape[1]):
                text = self._text(df.iat[row, col])
                match = re.search(r"\b(20\d{2})\b", text)
                if match:
                    year_cols[int(match.group(1))] = col
            score = int(current_year in year_cols) * 3 + int(previous_year in year_cols) * 2
            if score:
                candidate_rows.append((score, row, year_cols))

        if candidate_rows:
            _, year_row, year_cols = max(candidate_rows, key=lambda item: (item[0], -item[1]))
            header_row = year_row
            if previous_year in year_cols:
                headers[str(previous_year)] = year_cols[previous_year]
            if current_year in year_cols:
                headers[str(current_year)] = year_cols[current_year]
        elif preferred_header_row is not None:
            header_row = preferred_header_row
        else:
            return None, {}

        sample_start = header_row + 1
        sample_end = min(len(df), sample_start + 50)

        # Deteksi kolom KODE CT berdasarkan isi 4 digit seperti 0104/0305/0601.
        best_code = (-1, None)
        for col in range(df.shape[1]):
            count = 0
            for row in range(sample_start, sample_end):
                value = self._text(df.iat[row, col])
                if self._looks_like_coretax_code(value):
                    count += 1
            if count > best_code[0]:
                best_code = (count, col)
        if best_code[0] > 0:
            headers["kode_ct"] = best_code[1]

        # Tahun perolehan: kolom dengan banyak angka tahun valid, tetapi bukan
        # kolom nilai tahun berjalan/sebelumnya.
        excluded = {headers.get(str(previous_year)), headers.get(str(current_year))}
        best_year = (-1, None)
        for col in range(df.shape[1]):
            if col in excluded:
                continue
            count = 0
            for row in range(sample_start, sample_end):
                number = self._number(df.iat[row, col], default=0)
                if 1900 <= number <= 2100:
                    count += 1
            if count > best_year[0]:
                best_year = (count, col)
        if best_year[0] > 0:
            headers["tahun_perolehan"] = best_year[1]

        # Nama Harta: utamakan kolom teks di kanan KODE CT.
        code_col = headers.get("kode_ct")
        candidate_cols = range(df.shape[1])
        if code_col is not None:
            candidate_cols = range(code_col + 1, min(df.shape[1], code_col + 4))

        best_name = (-1, None)
        for col in candidate_cols:
            text_count = 0
            for row in range(sample_start, sample_end):
                value = self._text(df.iat[row, col])
                if (
                    value
                    and not self._looks_like_coretax_code(value)
                    and not re.fullmatch(r"[\d.,\-]+", value)
                ):
                    text_count += 1
            if text_count > best_name[0]:
                best_name = (text_count, col)
        if best_name[0] > 0:
            headers["nama_harta"] = best_name[1]

        # Alias tambahan dari baris header terpilih.
        for row in {
            header_row,
            preferred_header_row if preferred_header_row is not None else header_row,
        }:
            if row is None or row < 0 or row >= len(df):
                continue
            for col in range(df.shape[1]):
                raw = self._text(df.iat[row, col])
                if not raw:
                    continue
                canonical = self._canonical_header(raw)
                if canonical in self.HEADER_ALIASES:
                    headers.setdefault(canonical, col)

        return header_row, headers

    @staticmethod
    def _looks_like_coretax_code(value: object) -> bool:
        text = re.sub(r"\s+", "", str(value or ""))
        return bool(re.fullmatch(r"0[1-7]\d{2}", text))

    @staticmethod
    def _detect_year(sheet_name: str, df) -> int:
        match = re.search(r"\b(20\d{2})\b", str(sheet_name))
        if match:
            return int(match.group(1))

        for row in range(min(len(df), 20)):
            for col in range(min(df.shape[1], 10)):
                text = str(df.iat[row, col] or "")
                match = re.search(r"\b(20\d{2})\b", text)
                if match:
                    return int(match.group(1))
        return 0
