from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "templates"
    / "1770"
    / "1770_blank.pdf"
)


@dataclass(frozen=True)
class Legacy1770TemplateInfo:
    path: Path
    exists: bool
    size_bytes: int = 0
    sha256: str = ""
    page_count: int = 0

    @property
    def is_ready(self) -> bool:
        return self.exists and self.size_bytes > 0 and self.page_count >= 15


class Legacy1770TemplateManager:
    """Stage 8C.1 - pengelola template PDF 1770 resmi.

    Template sumber tidak pernah dimodifikasi. Exporter harus bekerja pada salinan
    sehingga satu template dapat dipakai berulang untuk banyak WP/tahun pajak.

    Nomor halaman PDF menggunakan basis 1 untuk metadata bisnis:
      10 = Induk Bahasa Indonesia
      12 = Lampiran I halaman 2
      13 = Lampiran II
      14 = Lampiran III
      15 = Lampiran IV
    """

    INDONESIAN_EXPORT_PAGES = (10, 12, 13, 14, 15)

    def __init__(self, template_path: Optional[str | Path] = None):
        self.template_path = Path(template_path or DEFAULT_TEMPLATE_PATH)

    def inspect(self) -> Legacy1770TemplateInfo:
        path = self.template_path
        if not path.is_file():
            return Legacy1770TemplateInfo(path=path, exists=False)

        data = path.read_bytes()
        page_count = self._page_count(path)
        return Legacy1770TemplateInfo(
            path=path,
            exists=True,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            page_count=page_count,
        )

    def require_ready(self) -> Legacy1770TemplateInfo:
        info = self.inspect()
        if not info.exists:
            raise FileNotFoundError(
                "Template 1770 kosong belum tersedia. Simpan PDF resmi sebagai: "
                f"{info.path}"
            )
        if info.page_count < 15:
            raise ValueError(
                "Template 1770 tidak sesuai: minimal harus memiliki 15 halaman "
                "agar halaman Bahasa Indonesia Induk sampai Lampiran IV tersedia."
            )
        return info

    def copy_for_export(self, destination: str | Path) -> Path:
        self.require_ready()
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.template_path, target)
        return target

    @staticmethod
    def _page_count(path: Path) -> int:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "Library pypdf diperlukan untuk membaca template PDF. "
                "Install dengan: python -m pip install pypdf"
            ) from exc
        return len(PdfReader(str(path)).pages)
