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
