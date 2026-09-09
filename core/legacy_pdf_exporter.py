from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPen, QPdfWriter

from core.legacy_1770 import Legacy1770Document


class Legacy1770PdfExporter:
    """Stage 8C: renderer PDF Form 1770 lama berdasarkan acuan visual Lisa.

    Renderer menggambar ulang formulir agar file referensi Lisa tidak menjadi
    template produksi dan tidak membawa data pribadinya ke output WP lain.
    """

    PAGE_W = 595.0
    PAGE_H = 842.0
    MARGIN = 24.0
    YELLOW = QColor("#FFFCA3")
    GRAY = QColor("#D9D9D9")
    LIGHT = QColor("#F4F4F4")
    BLACK = QColor("#111111")

    def export(self, document: Legacy1770Document, output_path: str | Path) -> Path:
        if not document.can_export_pdf:
            messages = "; ".join(issue.message for issue in document.errors) or "Dokumen belum siap diekspor."
            raise ValueError(messages)

        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        writer = QPdfWriter(str(target))
        writer.setResolution(72)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Point)
        writer.setTitle(f"SPT 1770 Format Lama - {document.nama_wp} - {document.tahun_pajak}")
        writer.setCreator("TAX_CONVERTER L-1")

        painter = QPainter(writer)
        if not painter.isActive():
            raise RuntimeError("PDF writer gagal diaktifkan.")

        try:
            self._page_induk(painter, document)
            writer.newPage()
            self._page_lampiran_i(painter, document)
            writer.newPage()
            self._page_lampiran_ii(painter, document)
            writer.newPage()
            self._page_lampiran_iii(painter, document)
            writer.newPage()
            self._page_lampiran_iv(painter, document)
        finally:
            painter.end()

        return target

    @staticmethod
    def _money(value: float) -> str:
        number = int(round(float(value or 0)))
        if number == 0:
            return "-"
        return f"{number:,}".replace(",", ".")

    @staticmethod
    def _font(size=7.0, bold=False):
        font = QFont("Arial", int(round(size)))
        font.setBold(bool(bold))
        return font

    def _text(self, p: QPainter, rect: QRectF, text: object, *, size=7, bold=False,
              align=Qt.AlignLeft | Qt.AlignVCenter, color=None, pad=3):
        p.save()
        p.setFont(self._font(size, bold))
        p.setPen(color or self.BLACK)
        inner = rect.adjusted(pad, 0, -pad, 0)
        p.drawText(inner, int(align | Qt.TextWordWrap), str(text or ""))
        p.restore()

    def _box(self, p: QPainter, rect: QRectF, *, fill=None, width=0.8):
        p.save()
        p.setPen(QPen(self.BLACK, width))
        p.setBrush(fill if fill is not None else Qt.NoBrush)
        p.drawRect(rect)
        p.restore()

    def _line(self, p: QPainter, x1, y1, x2, y2, width=0.7):
        p.save()
        p.setPen(QPen(self.BLACK, width))
        p.drawLine(x1, y1, x2, y2)
        p.restore()

    def _header(self, p: QPainter, document: Legacy1770Document, form_code: str, title: str,
                subtitle: str = "") -> float:
        x = self.MARGIN
        y = 24.0
        left_w = 118.0
        center_w = 300.0
        year_w = self.PAGE_W - self.MARGIN * 2 - left_w - center_w

        self._box(p, QRectF(x, y, left_w, 66))
        self._text(p, QRectF(x, y + 6, left_w, 18), form_code, size=18, bold=True,
                   align=Qt.AlignCenter)
        self._text(p, QRectF(x, y + 28, left_w, 30), "KEMENTERIAN KEUANGAN RI\nDIREKTORAT JENDERAL PAJAK",
                   size=5.5, bold=True, align=Qt.AlignCenter)

        cx = x + left_w
        self._box(p, QRectF(cx, y, center_w, 66))
        self._text(p, QRectF(cx, y + 2, center_w, 18), "SPT TAHUNAN PPh WAJIB PAJAK ORANG PRIBADI",
                   size=10, bold=True, align=Qt.AlignCenter)
        self._text(p, QRectF(cx + 6, y + 22, center_w - 12, 38), title + ("\n" + subtitle if subtitle else ""),
                   size=6.5, bold=True, align=Qt.AlignLeft | Qt.AlignTop)

        yx = cx + center_w
        self._box(p, QRectF(yx, y, year_w, 66))
        self._text(p, QRectF(yx, y + 2, year_w, 12), "TAHUN PAJAK", size=6, bold=True,
                   align=Qt.AlignCenter)
        year = str(document.tahun_pajak or "")
        bw = max(12.0, (year_w - 12) / 4)
        start = yx + 6
        for i in range(4):
            rect = QRectF(start + i * bw, y + 17, bw, 17)
            self._box(p, rect, fill=self.YELLOW)
            self._text(p, rect, year[i] if i < len(year) else "", size=10, bold=True,
                       align=Qt.AlignCenter, pad=0)
        self._text(p, QRectF(yx + 4, y + 39, year_w - 8, 20), "PEMBUKUAN   [ ]\nPENCATATAN  [X]",
                   size=5.8, bold=True, align=Qt.AlignCenter)

        y += 72
        self._box(p, QRectF(x, y, self.PAGE_W - 2 * self.MARGIN, 35))
        self._box(p, QRectF(x + 96, y + 3, self.PAGE_W - 2 * self.MARGIN - 102, 13), fill=self.YELLOW)
        self._box(p, QRectF(x + 96, y + 18, self.PAGE_W - 2 * self.MARGIN - 102, 13), fill=self.YELLOW)
        self._text(p, QRectF(x + 4, y + 3, 90, 13), "NPWP", size=6.5, bold=True)
        self._text(p, QRectF(x + 100, y + 3, 390, 13), document.npwp, size=7.5, bold=True)
        self._text(p, QRectF(x + 4, y + 18, 90, 13), "NAMA WAJIB PAJAK", size=6.5, bold=True)
        self._text(p, QRectF(x + 100, y + 18, 390, 13), document.nama_wp, size=7.5, bold=True)
        return y + 42

    def _section_title(self, p, y, code, title):
        rect = QRectF(self.MARGIN, y, self.PAGE_W - 2 * self.MARGIN, 18)
        self._box(p, rect, fill=self.LIGHT)
        self._text(p, QRectF(rect.x() + 4, y, 36, 18), code, size=7, bold=True)
        self._text(p, QRectF(rect.x() + 40, y, rect.width() - 44, 18), title, size=7, bold=True)
        return y + 18

    def _key_value_rows(self, p, y, rows: Sequence[tuple[str, float]], *, height=18):
        x = self.MARGIN
        w = self.PAGE_W - 2 * self.MARGIN
        no_w = 28
        value_w = 126
        label_w = w - no_w - value_w
        for idx, (label, value) in enumerate(rows, start=1):
            self._box(p, QRectF(x, y, no_w, height))
            self._box(p, QRectF(x + no_w, y, label_w, height))
            self._box(p, QRectF(x + no_w + label_w, y, value_w, height), fill=self.YELLOW)
            self._text(p, QRectF(x, y, no_w, height), str(idx), size=6, align=Qt.AlignCenter, pad=0)
            self._text(p, QRectF(x + no_w, y, label_w, height), label, size=6.2)
            self._text(p, QRectF(x + no_w + label_w, y, value_w, height), self._money(value), size=7,
                       bold=True, align=Qt.AlignRight | Qt.AlignVCenter)
            y += height
        return y

    def _page_induk(self, p: QPainter, d: Legacy1770Document):
        y = self._header(p, d, "1770", "BAGI WAJIB PAJAK YANG MEMPUNYAI PENGHASILAN DARI USAHA/PEKERJAAN BEBAS, PEKERJAAN, FINAL, DAN/ATAU DALAM NEGERI LAINNYA")
        y = self._section_title(p, y, "A.", "PENGHASILAN NETO")
        neto_before_zakat = d.penghasilan_neto_gabungan + d.zakat
        y = self._key_value_rows(p, y, [
            ("Penghasilan Neto Dalam Negeri dari Usaha/Pekerjaan Bebas", 0),
            ("Penghasilan Neto Dalam Negeri Sehubungan dengan Pekerjaan", d.total_netto_bupot),
            ("Penghasilan Neto Dalam Negeri Lainnya", d.penghasilan_neto_lainnya),
            ("Penghasilan Neto Luar Negeri", 0),
            ("Jumlah Penghasilan Neto", neto_before_zakat),
            ("Zakat/Sumbangan Keagamaan yang Bersifat Wajib", d.zakat),
            ("Jumlah Penghasilan Neto setelah Zakat", d.penghasilan_neto_gabungan),
        ], height=16)
        y = self._section_title(p, y + 4, "B.", "PENGHASILAN KENA PAJAK")
        y = self._key_value_rows(p, y, [
            ("Kompensasi Kerugian", 0),
            ("Jumlah Penghasilan Neto setelah Kompensasi Kerugian", d.penghasilan_neto_gabungan),
            (f"Penghasilan Tidak Kena Pajak - {d.status_ptkp or '-'}", d.ptkp),
            ("Penghasilan Kena Pajak", d.pkp),
        ], height=16)
        y = self._section_title(p, y + 4, "C.", "PPh TERUTANG")
        y = self._key_value_rows(p, y, [
            ("PPh Terutang (Tarif Pasal 17 x PKP)", d.pph_terutang),
            ("Pengembalian/Pengurangan PPh Pasal 24", 0),
            ("Jumlah PPh Terutang", d.pph_terutang),
        ], height=16)
        y = self._section_title(p, y + 4, "D.", "KREDIT PAJAK")
        y = self._key_value_rows(p, y, [
            ("PPh yang Dipotong/Dipungut Pihak Lain", d.kredit_pajak),
            ("PPh yang Dibayar Sendiri - PPh Pasal 25", d.pph25),
            ("Jumlah Kredit Pajak", d.kredit_pajak + d.pph25),
        ], height=16)
        y = self._section_title(p, y + 4, "E.", "PPh KURANG / LEBIH BAYAR")
        self._key_value_rows(p, y, [("PPh Kurang/(Lebih) Bayar", d.kurang_lebih_bayar)], height=18)

        self._box(p, QRectF(self.MARGIN, 760, self.PAGE_W - 2 * self.MARGIN, 48))
        self._text(p, QRectF(self.MARGIN + 6, 763, 280, 14), "PERNYATAAN", size=7, bold=True)
        self._text(p, QRectF(self.MARGIN + 6, 778, 300, 20), f"WAJIB PAJAK: {d.nama_wp}   NPWP: {d.npwp}", size=6.5, bold=True)
        self._box(p, QRectF(430, 768, 130, 32))
        self._text(p, QRectF(430, 768, 130, 32), "TANDA TANGAN", size=6, align=Qt.AlignCenter)

    def _page_lampiran_i(self, p: QPainter, d: Legacy1770Document):
        y = self._header(p, d, "1770 - I", "PENGHITUNGAN PENGHASILAN DALAM NEGERI")
        y = self._section_title(p, y, "B.", "PENGHASILAN NETO DARI USAHA DAN/ATAU PEKERJAAN BEBAS")
        self._simple_table(p, y, ["NO", "JENIS USAHA", "PEREDARAN USAHA", "NORMA (%)", "PENGHASILAN NETO"],
                           [[1, "DAGANG", "-", "-", "-"], [2, "INDUSTRI", "-", "-", "-"], [3, "JASA", "-", "-", "-"], [4, "PEKERJAAN BEBAS", "-", "-", "-"], [5, "USAHA LAINNYA", "-", "-", "-"]],
                           widths=[36, 190, 135, 70, 120], row_h=24)
        y += 24 * 6 + 8
        y = self._section_title(p, y, "C.", "PENGHASILAN NETO DALAM NEGERI SEHUBUNGAN DENGAN PEKERJAAN")
        rows = []
        for b in d.bupot_rows[:8]:
            rows.append([b.nomor, b.npwp_pemotong, self._money(b.bruto), self._money(b.pengurang), self._money(b.netto)])
        self._simple_table(p, y, ["NO", "NAMA / NPWP PEMBERI KERJA", "BRUTO", "PENGURANG", "NETO"], rows,
                           widths=[36, 210, 105, 105, 95], row_h=22, min_rows=6)
        y += 22 * (max(6, len(rows)) + 1) + 8
        y = self._section_title(p, y, "D.", "PENGHASILAN NETO DALAM NEGERI LAINNYA")
        income_rows = [[1, "BUNGA", "-"], [2, "ROYALTI", "-"], [3, "SEWA", "-"], [4, "PENGHARGAAN DAN HADIAH", "-"], [5, "KEUNTUNGAN PENJUALAN/PENGALIHAN HARTA", "-"], [6, "PENGHASILAN LAINNYA", self._money(d.penghasilan_neto_lainnya)]]
        self._simple_table(p, y, ["NO", "JENIS PENGHASILAN", "JUMLAH PENGHASILAN NETO"], income_rows,
                           widths=[36, 370, 145], row_h=22)

    def _page_lampiran_ii(self, p: QPainter, d: Legacy1770Document):
        y = self._header(p, d, "1770 - II", "DAFTAR PEMOTONGAN/PEMUNGUTAN PPh OLEH PIHAK LAIN")
        y = self._section_title(p, y, "A.", "DAFTAR PEMOTONGAN/PEMUNGUTAN PPh")
        rows = []
        for b in d.bupot_rows[:15]:
            rows.append([b.nomor, b.nama_pemotong or "-", b.npwp_pemotong, b.no_bupot, b.tanggal_bupot or "-", b.jenis or "-", self._money(b.pph_dipotong)])
        self._simple_table(p, y, ["NO", "NAMA PEMOTONG", "NPWP", "NO BUKTI", "TANGGAL", "JENIS PAJAK", "PPh DIPOTONG"], rows,
                           widths=[28, 115, 96, 72, 66, 88, 82], row_h=32, min_rows=15, font_size=5.2)
        total = sum(b.pph_dipotong for b in d.bupot_rows)
        footer_y = y + 32 * 16
        self._box(p, QRectF(self.MARGIN, footer_y, 465, 24), fill=self.LIGHT)
        self._box(p, QRectF(self.MARGIN + 465, footer_y, 82, 24), fill=self.YELLOW)
        self._text(p, QRectF(self.MARGIN, footer_y, 465, 24), "JUMLAH BAGIAN A", size=6.5, bold=True, align=Qt.AlignCenter)
        self._text(p, QRectF(self.MARGIN + 465, footer_y, 82, 24), self._money(total), size=7, bold=True, align=Qt.AlignRight | Qt.AlignVCenter)

    def _page_lampiran_iii(self, p: QPainter, d: Legacy1770Document):
        y = self._header(p, d, "1770 - III", "PENGHASILAN FINAL, BUKAN OBJEK PAJAK, DAN PENGHASILAN ISTERI/SUAMI TERPISAH")
        y = self._section_title(p, y, "A.", "PENGHASILAN YANG DIKENAKAN PAJAK FINAL DAN/ATAU BERSIFAT FINAL")
        final_total_dpp = d.umkm_bruto
        final_total_pph = d.umkm_pph_setor
        for row in d.penghasilan_final_lainnya:
            final_total_dpp += row.dpp
            final_total_pph += row.pph
        rows = [
            [1, "BUNGA DEPOSITO/TABUNGAN/SURAT BERHARGA", "-", "-"],
            [2, "BUNGA/DISKONTO OBLIGASI", "-", "-"],
            [3, "PENJUALAN SAHAM DI BURSA EFEK", "-", "-"],
            [4, "HADIAH UNDIAN", "-", "-"],
            [5, "PESANGON/THT/PENSIUN SEKALIGUS", "-", "-"],
            [6, "HONORARIUM ATAS BEBAN APBN/APBD", "-", "-"],
            [7, "PENGALIHAN HAK TANAH/BANGUNAN", "-", "-"],
            [8, "BANGUN GUNA SERAH", "-", "-"],
            [9, "SEWA TANAH DAN/ATAU BANGUNAN", "-", "-"],
            [10, "USAHA JASA KONSTRUKSI", "-", "-"],
            [11, "PENYALUR/DEALER/AGEN PRODUK BBM", "-", "-"],
            [12, "BUNGA SIMPANAN KOPERASI", "-", "-"],
            [13, "TRANSAKSI DERIVATIF", "-", "-"],
            [14, "DIVIDEN", "-", "-"],
            [15, "PENGHASILAN ISTERI DARI SATU PEMBERI KERJA", "-", "-"],
            [16, "PENGHASILAN LAIN YANG DIKENAKAN PAJAK FINAL", self._money(final_total_dpp), self._money(final_total_pph)],
        ]
        self._simple_table(p, y, ["NO", "JENIS PENGHASILAN", "DPP/PENGHASILAN BRUTO", "PPh TERUTANG"], rows,
                           widths=[34, 310, 110, 97], row_h=21, font_size=5.3)
        y += 21 * 17 + 8
        y = self._section_title(p, y, "B.", "PENGHASILAN YANG TIDAK TERMASUK OBJEK PAJAK")
        bukan = [[1, "BANTUAN / SUMBANGAN / HIBAH", self._money(d.penghasilan_bukan_objek)], [2, "WARISAN", "-"], [3, "BAGIAN LABA PERSEROAN/PERSEKUTUAN", "-"], [4, "KLAIM ASURANSI", "-"], [5, "BEASISWA", "-"], [6, "PENGHASILAN LAIN YANG TIDAK TERMASUK OBJEK PAJAK", "-"]]
        self._simple_table(p, y, ["NO", "SUMBER/JENIS PENGHASILAN", "PENGHASILAN BRUTO"], bukan,
                           widths=[34, 390, 127], row_h=22)

    def _page_lampiran_iv(self, p: QPainter, d: Legacy1770Document):
        y = self._header(p, d, "1770 - IV", "HARTA PADA AKHIR TAHUN, KEWAJIBAN/UTANG, DAN SUSUNAN ANGGOTA KELUARGA")
        y = self._section_title(p, y, "A.", "HARTA PADA AKHIR TAHUN")
        rows = []
        for r in d.harta_rows[:10]:
            rows.append([r.nomor, r.kode_eform, r.nama_harta, r.tahun_perolehan, self._money(r.nilai_tahun_berjalan), r.keterangan or "-"])
        self._simple_table(p, y, ["NO", "KODE HARTA", "NAMA HARTA", "TAHUN PEROLEHAN", "HARGA PEROLEHAN", "KETERANGAN"], rows,
                           widths=[32, 58, 180, 82, 105, 94], row_h=26, min_rows=10, font_size=5.6)
        footer_y = y + 26 * 11
        total_harta = sum(r.nilai_tahun_berjalan for r in d.harta_rows)
        self._box(p, QRectF(self.MARGIN, footer_y, 446, 24), fill=self.LIGHT)
        self._box(p, QRectF(self.MARGIN + 446, footer_y, 105, 24), fill=self.YELLOW)
        self._text(p, QRectF(self.MARGIN, footer_y, 446, 24), "JUMLAH BAGIAN A", size=6.5, bold=True, align=Qt.AlignCenter)
        self._text(p, QRectF(self.MARGIN + 446, footer_y, 105, 24), self._money(total_harta), size=7, bold=True, align=Qt.AlignRight | Qt.AlignVCenter)

        y = footer_y + 32
        y = self._section_title(p, y, "B.", "KEWAJIBAN/UTANG PADA AKHIR TAHUN")
        self._simple_table(p, y, ["NO", "KODE UTANG", "NAMA PEMBERI PINJAMAN", "ALAMAT", "TAHUN", "JUMLAH"], [],
                           widths=[32, 64, 175, 150, 55, 75], row_h=24, min_rows=6, font_size=5.4)
        y += 24 * 7 + 8
        y = self._section_title(p, y, "C.", "DAFTAR SUSUNAN ANGGOTA KELUARGA")
        self._simple_table(p, y, ["NO", "NAMA ANGGOTA KELUARGA", "NIK", "HUBUNGAN KELUARGA", "PEKERJAAN"], [],
                           widths=[32, 190, 125, 115, 89], row_h=24, min_rows=5, font_size=5.6)

    def _simple_table(self, p: QPainter, y: float, headers: Sequence[str], rows: Iterable[Sequence[object]],
                      *, widths: Sequence[float], row_h: float, min_rows: int = 0, font_size: float = 5.8):
        x0 = self.MARGIN
        rows = list(rows)
        rendered_rows = rows + [[""] * len(headers) for _ in range(max(0, min_rows - len(rows)))]

        x = x0
        for header, width in zip(headers, widths):
            rect = QRectF(x, y, width, row_h)
            self._box(p, rect, fill=self.LIGHT)
            self._text(p, rect, header, size=font_size, bold=True, align=Qt.AlignCenter, pad=2)
            x += width

        y += row_h
        for row in rendered_rows:
            x = x0
            values = list(row) + [""] * max(0, len(headers) - len(row))
            for col, (value, width) in enumerate(zip(values, widths)):
                rect = QRectF(x, y, width, row_h)
                self._box(p, rect)
                align = Qt.AlignCenter
                if col in {2, 3, 4, 5, 6} and isinstance(value, str) and ("." in value or value == "-"):
                    align = Qt.AlignRight | Qt.AlignVCenter
                self._text(p, rect, value, size=font_size, align=align, pad=2)
                x += width
            y += row_h
