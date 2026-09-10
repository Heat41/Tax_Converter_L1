from __future__ import annotations

from core.legacy_1770_lampiran_ii import (
    Legacy1770LampiranIIService as BaseLegacy1770LampiranIIService,
)


class Legacy1770LampiranIIService(BaseLegacy1770LampiranIIService):
    """Fine tuning visual Stage 8C.6 untuk master bersih enam halaman.

    Header Lampiran II tetap memakai koordinat khusus halaman 4 dari renderer
    base karena hasil visual sudah sesuai. Fine tuning ini meningkatkan
    keterbacaan isi tabel dan menormalkan kode Bupot A1/A2 sebagai PPh Pasal 21.
    """

    @staticmethod
    def _jenis_pajak(value: object) -> str:
        raw = " ".join(str(value or "").strip().split())
        if not raw:
            return ""

        compact = (
            raw.upper()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
            .replace("/", "")
        )
        if compact in {"BPA1", "BPA2", "1721A1", "1721A2"}:
            return "PPh Pasal 21"

        return BaseLegacy1770LampiranIIService._jenis_pajak(value)

    @classmethod
    def _draw_fit_center(
        cls,
        canvas,
        rect,
        text,
        width,
        height,
        *,
        size: float = 6.2,
        min_size: float = 4.2,
    ) -> None:
        # Lebih besar dari renderer awal, tetapi helper base tetap mengecilkan
        # teks panjang agar tidak keluar dari sel.
        return super()._draw_fit_center(
            canvas,
            rect,
            text,
            width,
            height,
            size=size + 0.75,
            min_size=min_size,
        )

    @classmethod
    def _draw_right_money(
        cls,
        canvas,
        rect,
        value,
        width,
        height,
        *,
        size: float = 6.4,
    ) -> None:
        # Nilai PPh dan JBA dibuat lebih mudah dibaca tanpa mengubah posisi kolom.
        return super()._draw_right_money(
            canvas,
            rect,
            value,
            width,
            height,
            size=size + 0.6,
        )