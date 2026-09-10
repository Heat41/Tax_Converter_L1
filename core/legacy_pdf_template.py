from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


MASTER_TEMPLATE_FILENAME = "1770_master_bersih_6_halaman.pdf"
DEFAULT_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "templates"
    / "1770"
    / MASTER_TEMPLATE_FILENAME
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
        return self.exists and self.size_bytes > 0 and self.page_count == 6


class Legacy1770TemplateManager:
    """Pengelola master visual Form 1770 lama untuk Stage 8C.

    Master produksi memakai PDF bersih 6 halaman Bahasa Indonesia:
      1 = Induk
      2 = Lampiran I halaman 1
      3 = Lampiran I halaman 2
      4 = Lampiran II
      5 = Lampiran III
      6 = Lampiran IV

    Master tidak berisi data contoh WP dan tidak memiliki fitur form interaktif.
    Exporter bekerja pada salinan lalu mencetak data FINAL WP secara statis.
    """

    EXPORT_PAGES = (1, 2, 3, 4, 5, 6)
    INDONESIAN_EXPORT_PAGES = EXPORT_PAGES  # compatibility untuk kode lama

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
                "Master bersih 1770 enam halaman belum tersedia. Simpan file sebagai: "
                f"{info.path}"
            )
        if info.page_count != 6:
            raise ValueError(
                "Master template 1770 tidak sesuai: file produksi harus tepat 6 halaman "
                "Bahasa Indonesia (Induk, Lampiran I halaman 1-2, II, III, IV)."
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
