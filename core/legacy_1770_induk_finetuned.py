from __future__ import annotations

from core.legacy_1770_induk import Legacy1770IndukService as BaseLegacy1770IndukService


class Legacy1770IndukService(BaseLegacy1770IndukService):
    """Fine tuning visual Stage 8C.4 untuk master bersih 6 halaman.

    Kelas ini sengaja hanya menangani elemen kecil yang sudah dikalibrasi secara
    visual. Mapping/perhitungan tetap berasal dari renderer utama.
    """

    # Kalibrasi dari debug PTKP V2 pada master bersih.
    # Titik 15 (x=238, y=428; origin kiri-atas) berada di pusat kotak TK.
    # Kotak K dan K/I mengikuti jarak pusat pada master yang sama.
    PTKP_DEPENDENT_POINTS = {
        "TK": (238.0, 428.0),
        "K": (281.3, 428.0),
        "KI": (324.5, 428.0),
    }

    # Fine tuning checkbox PERNYATAAN - WAJIB PAJAK.
    # Posisi lama tepat mengenai garis atas kotak; area target diturunkan 6.4 pt
    # tanpa mengubah posisi horizontal maupun checkbox KUASA.
    DECLARATION_WP_RECT = (103.7, 848.2, 118.4, 861.6)

    # Final visual tuning: data dinamis pada halaman Induk dibaca 10 pt.
    INDUK_DATA_FONT_SIZE = 10.0

    @classmethod
    def _draw_ptkp_status(cls, canvas, status: str, width: float, height: float) -> None:
        """Cetak digit tanggungan langsung dari titik pusat hasil kalibrasi.

        Ini menggantikan pendekatan Rect lama sehingga perubahan posisi tidak lagi
        terpengaruh bounding-box/override historis pada renderer.
        """
        normalized = str(status or "").upper().replace(" ", "")
        if not normalized:
            return

        if normalized.startswith("K/I/"):
            key = "KI"
        elif normalized.startswith("K/"):
            key = "K"
        else:
            key = "TK"

        dependent = "".join(ch for ch in normalized.split("/")[-1] if ch.isdigit())[:1]
        if not dependent:
            return

        x_top, y_top = cls.PTKP_DEPENDENT_POINTS[key]
        sx = width / cls.BASE_WIDTH
        sy = height / cls.BASE_HEIGHT
        x = x_top * sx

        # drawCentredString memakai baseline, bukan geometric center. Baseline
        # diturunkan ±1.5 pt dari titik pusat agar digit tampak tepat di tengah box.
        y = height - ((y_top + 1.5) * sy)
        font_size = 6.2 * sy
        canvas.setFont("Helvetica", font_size)
        canvas.drawCentredString(x, y, dependent)


    def _make_induk_overlay(self, page, document: Legacy1770Document):
        """Render halaman Induk dengan data dinamis 10 pt."""
        try:
            from io import BytesIO
            from reportlab.pdfgen import canvas as reportlab_canvas
        except ImportError as exc:
            raise RuntimeError(
                "Library reportlab diperlukan untuk mencetak Form 1770 statis."
            ) from exc

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        packet = BytesIO()
        c = reportlab_canvas.Canvas(packet, pagesize=(width, height))

        self._draw_year_four_digits(c, self.YEAR_RECT, document.tahun_pajak, width, height)
        self._draw_period_four_digits(c, self.PERIOD_START_RECT, 1, document.tahun_pajak, width, height)
        self._draw_period_four_digits(c, self.PERIOD_END_RECT, 12, document.tahun_pajak, width, height)
        self._draw_four_group_comb(
            c,
            self.NPWP_GROUP_RECTS,
            document.npwp,
            width,
            height,
            font_size=self.INDUK_DATA_FONT_SIZE,
        )
        self._draw_left(
            c,
            self.NAME_RECT,
            str(document.nama_wp).upper(),
            width,
            height,
            self.INDUK_DATA_FONT_SIZE,
        )
        self._draw_left(
            c,
            self.DECLARATION_NAME_RECT,
            str(document.nama_wp).upper(),
            width,
            height,
            self.INDUK_DATA_FONT_SIZE,
        )
        self._draw_four_group_comb(
            c,
            self.DECLARATION_NPWP_GROUP_RECTS,
            document.npwp,
            width,
            height,
            font_size=self.INDUK_DATA_FONT_SIZE,
        )
        self._draw_center(
            c,
            self.DECLARATION_WP_RECT,
            "X",
            width,
            height,
            self.INDUK_DATA_FONT_SIZE,
            bold=True,
        )

        pekerjaan = float(document.total_netto_bupot or 0)
        lainnya = float(document.penghasilan_neto_lainnya or 0)
        jumlah_neto = pekerjaan + lainnya
        neto_setelah_zakat = jumlah_neto - float(document.zakat or 0)
        kurang_lebih_16 = float(document.pph_terutang or 0) - float(document.kredit_pajak or 0)
        kredit_sendiri = float(document.pph25 or 0)
        kurang_lebih_19 = kurang_lebih_16 - kredit_sendiri

        row_values = {
            "2": pekerjaan,
            "3": lainnya,
            "5": jumlah_neto,
            "6": document.zakat,
            "7": neto_setelah_zakat,
            "9": neto_setelah_zakat,
            "10": document.ptkp,
            "11": document.pkp,
            "12": document.pph_terutang,
            "14": document.pph_terutang,
            "15": document.kredit_pajak,
            "16": abs(kurang_lebih_16),
            "18": kredit_sendiri,
            "19": abs(kurang_lebih_19),
        }
        for row, value in row_values.items():
            self._draw_right(
                c,
                self.ROW_RECTS[row],
                self._rupiah(value),
                width,
                height,
                font_size=self.INDUK_DATA_FONT_SIZE,
            )

        self._draw_ptkp_status(c, document.status_ptkp, width, height)
        self._draw_sign(c, self.SIGN_16_RECTS, kurang_lebih_16, width, height)
        self._draw_sign(c, self.SIGN_19_RECTS, kurang_lebih_19, width, height)

        c.save()
        packet.seek(0)
        return packet
