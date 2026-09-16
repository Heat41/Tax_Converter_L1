from __future__ import annotations

import re
from pathlib import Path
from typing import List

from core.worksheet_pph_state import WorksheetBupotRow


class BupotPdfImporter:
    """Parser PDF Bupot Coretax satuan.

    Fokus awal pada BP21 text-based PDF. Hasil selalu dinormalisasi ke
    WorksheetBupotRow yang sama dengan Rekap Bupot.
    """

    def parse_many(self, paths: List[str | Path]) -> List[WorksheetBupotRow]:
        rows = []
        for path in paths:
            rows.append(self.parse(path))
        return rows

    def parse(self, file_path: str | Path) -> WorksheetBupotRow:
        path = Path(file_path)
        text = self._extract_text(path)
        if not text.strip():
            raise ValueError(f"PDF tidak memiliki text layer: {path.name}")

        kind = self._first(r"\b(BP\d+)\b", text)
        no_bupot = self._first(r"NOMOR BUKTI PEMOTONGAN.*?\n\s*([A-Z0-9]+)", text, re.S)
        masa_full = self._first(r"\b(\d{2}-20\d{2})\b", text)
        masa, tahun = ("", "")
        if masa_full:
            masa, tahun = masa_full.split("-", 1)

        npwp_penerima = self._first(r"A\.1\s+NIK/NPWP\s*:\s*(\d+)", text)
        nama_penerima = self._first(r"A\.2\s+Nama\s*:\s*([^\n]+)", text)
        fasilitas = self._first(r"B\.1\s+Jenis Fasilitas\s*:\s*([^\n]+)", text)
        kop = self._first(r"\b(\d{2}-\d{3}-\d{2})\b", text)

        bruto, dpp, tarif, pph = self._extract_tax_numbers(text, kop)
        pengurang = bruto - (bruto * dpp / 100.0) if bruto and dpp else 0.0

        sifat = self._first(r"\b(TIDAK FINAL|FINAL)\b", text)
        status = self._first(r"\b(NORMAL|PEMBETULAN|PEMBATALAN)\b", text)

        bukti = self._first(r"Jenis Dokumen\s*:\s*([^\n]+?)(?:\s+Tanggal Dokumen|\n)", text)
        no_bukti = self._first(r"Nomor Dokumen\s*:\s*([^\n]+)", text)
        tanggal_bukti = self._first(r"Tanggal Dokumen\s*:\s*([^\n]+)", text)
        npwp_pemotong = self._first(r"C\.1\s+NPWP/NIK\s*:\s*(\d+)", text)
        nama_pemotong = self._first(r"C\.3\s+Nama Pemotong\s*:\s*([^\n]+)", text)
        tanggal_pemotongan = self._first(r"C\.4\s+Tanggal\s*:\s*([^\n]+)", text)

        return WorksheetBupotRow(
            jenis=kind,
            no_bupot=no_bupot,
            masa=masa,
            tahun=tahun,
            sifat=sifat,
            status=status,
            npwp_penerima=npwp_penerima,
            nama_penerima=nama_penerima,
            fasilitas=fasilitas,
            jenis_pph="Pasal 21" if kind == "BP21" else "",
            kop=kop,
            bruto=bruto,
            dpp_persen=dpp,
            tarif=tarif,
            pengurang=pengurang,
            pph_dipotong=pph,
            bukti=bukti,
            no_bukti=no_bukti,
            tanggal_bukti=tanggal_bukti,
            npwp_pemotong=npwp_pemotong,
            npwp_pemberi_kerja=npwp_pemotong,
            nama_pemotong=nama_pemotong,
            tanggal_pemotongan=tanggal_pemotongan,
        )

    @staticmethod
    def _extract_text(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(path)
        if path.suffix.lower() != ".pdf":
            raise ValueError("Bupot satuan harus berupa PDF.")

        reader_cls = None
        try:
            from pypdf import PdfReader
            reader_cls = PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader
                reader_cls = PdfReader
            except ImportError as exc:
                raise RuntimeError(
                    "Parser PDF memerlukan package 'pypdf'. Install dengan: pip install pypdf"
                ) from exc

        reader = reader_cls(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    @staticmethod
    def _first(pattern: str, text: str, flags: int = 0) -> str:
        match = re.search(pattern, text, flags | re.I)
        return match.group(1).strip() if match else ""

    @classmethod
    def _extract_tax_numbers(cls, text: str, kop: str) -> tuple[float, float, float, float]:
        if not kop:
            return 0.0, 0.0, 0.0, 0.0

        pos = text.find(kop)
        fragment = text[pos: pos + 1000] if pos >= 0 else text
        number_line = re.search(
            r"(\d[\d\.]*)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+(\d[\d\.]*)",
            fragment,
        )
        if not number_line:
            return 0.0, 0.0, 0.0, 0.0

        return (
            cls._number(number_line.group(1)),
            cls._number(number_line.group(2)),
            cls._number(number_line.group(3)),
            cls._number(number_line.group(4)),
        )

    @staticmethod
    def _number(value: str) -> float:
        text = str(value or "").strip()
        if "." in text and "," not in text:
            # PDF Coretax memakai titik sebagai pemisah ribuan untuk nominal.
            parts = text.split(".")
            if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                text = "".join(parts)
        text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return 0.0
