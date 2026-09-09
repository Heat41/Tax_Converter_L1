from __future__ import annotations

from core.worksheet_workbook_importer import (
    WorksheetWorkbookImporter as BaseWorksheetWorkbookImporter,
    WorksheetWorkbookImportIssue,
)
from core.worksheet_pph_state import WorksheetBupotRow


class WorksheetWorkbookImporter(BaseWorksheetWorkbookImporter):
    """Perbaikan parser Stage 8B.1 untuk workbook produksi EVY-style.

    Sheet ``2025`` dapat memiliki dua blok tabel pada baris header yang sama.
    Nama header seperti JENIS/NO BUPOT dapat muncul lagi di sisi kanan. Parser
    dasar sebelumnya membentuk dictionary dari seluruh baris sehingga kemunculan
    terakhir menimpa kolom tabel penghasilan di sisi kiri dan menghasilkan
    Bupot 0 baris. Override ini memilih satu blok header yang konsisten dan
    memiliki data aktual di bawahnya.
    """

    BUPOT_REQUIRED = (
        "jenis",
        "npwp pemberi kerja",
        "no bupot",
        "bruto",
        "pengurang",
    )

    def _parse_bupot(self, df, result):
        header_row = None
        candidate_columns = None

        for row in range(len(df)):
            label_positions = {}
            for col in range(df.shape[1]):
                label = self._label(df.iat[row, col])
                if label:
                    label_positions.setdefault(label, []).append(col)

            if not all(key in label_positions for key in self.BUPOT_REQUIRED):
                continue

            # Coba tiap kemunculan JENIS sebagai anchor. Blok valid harus punya
            # header wajib dalam rentang yang berdekatan dan minimal satu baris
            # data nyata setelah header.
            for jenis_col in label_positions["jenis"]:
                block = {}
                for key in self.BUPOT_REQUIRED:
                    nearby = [
                        col
                        for col in label_positions[key]
                        if abs(col - jenis_col) <= 6
                    ]
                    if not nearby:
                        block = {}
                        break
                    block[key] = min(nearby, key=lambda col: abs(col - jenis_col))

                if not block:
                    continue

                if self._bupot_block_has_data(df, row, block):
                    header_row = row
                    candidate_columns = block
                    break

            if candidate_columns is not None:
                break

        if header_row is None or candidate_columns is None:
            result.issues.append(
                WorksheetWorkbookImportIssue(
                    "WKI_104",
                    "WARNING",
                    "Tabel Bupot tidak ditemukan atau tidak memiliki baris data pada sheet tahun.",
                )
            )
            return

        for row in range(header_row + 1, len(df)):
            # TOTAL biasanya berada pada kolom NO di blok yang sama. Hentikan
            # pembacaan bila ditemukan sebelum masuk ke bagian worksheet lain.
            row_labels = {
                self._label(df.iat[row, col])
                for col in range(max(0, min(candidate_columns.values()) - 1),
                                 min(df.shape[1], max(candidate_columns.values()) + 2))
            }
            if "total" in row_labels:
                break

            jenis = self._text(df.iat[row, candidate_columns["jenis"]])
            npwp = self._digits(df.iat[row, candidate_columns["npwp pemberi kerja"]])
            no_bupot = self._text(df.iat[row, candidate_columns["no bupot"]])
            bruto = self._number(df.iat[row, candidate_columns["bruto"]])
            pengurang = self._number(df.iat[row, candidate_columns["pengurang"]])

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

    def _bupot_block_has_data(self, df, header_row, columns) -> bool:
        end_row = min(len(df), header_row + 35)
        for row in range(header_row + 1, end_row):
            labels = {
                self._label(df.iat[row, col])
                for col in range(max(0, min(columns.values()) - 1),
                                 min(df.shape[1], max(columns.values()) + 2))
            }
            if "total" in labels:
                return False

            jenis = self._text(df.iat[row, columns["jenis"]])
            npwp = self._digits(df.iat[row, columns["npwp pemberi kerja"]])
            no_bupot = self._text(df.iat[row, columns["no bupot"]])
            bruto = self._number(df.iat[row, columns["bruto"]])
            pengurang = self._number(df.iat[row, columns["pengurang"]])
            if any((jenis, npwp, no_bupot, bruto, pengurang)):
                return True
        return False
