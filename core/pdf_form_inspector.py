from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class PdfWidgetInfo:
    page_number: int
    rect: tuple[float, float, float, float]
    appearance_states: tuple[str, ...] = ()


@dataclass(frozen=True)
class PdfFormFieldInfo:
    name: str
    field_type: str
    value: str = ""
    default_value: str = ""
    flags: int = 0
    widgets: tuple[PdfWidgetInfo, ...] = field(default_factory=tuple)

    @property
    def pages(self) -> tuple[int, ...]:
        return tuple(sorted({widget.page_number for widget in self.widgets}))


class PdfFormInspector:
    """Stage 8C.2 - membaca field AcroForm tanpa mengubah PDF.

    Inspector dipakai untuk mengunci nama field resmi template DJP, sehingga
    exporter tidak bergantung pada koordinat visual selama field AcroForm tersedia.
    """

    def inspect(self, pdf_path: str | Path) -> Dict[str, PdfFormFieldInfo]:
        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(path)

        try:
            from pypdf import PdfReader
            from pypdf.generic import DictionaryObject
        except ImportError as exc:
            raise RuntimeError(
                "Library pypdf diperlukan untuk membaca AcroForm. "
                "Install dengan: python -m pip install pypdf"
            ) from exc

        reader = PdfReader(str(path))
        raw_fields = reader.get_fields() or {}
        widgets_by_name: Dict[str, List[PdfWidgetInfo]] = {}

        for page_index, page in enumerate(reader.pages, start=1):
            annotations = page.get("/Annots") or []
            for annotation_ref in annotations:
                annotation = annotation_ref.get_object()
                if annotation.get("/Subtype") != "/Widget":
                    continue

                field_obj = annotation
                name = field_obj.get("/T")
                if not name and field_obj.get("/Parent") is not None:
                    parent = field_obj["/Parent"].get_object()
                    name = parent.get("/T")
                if not name:
                    continue

                rect_obj = annotation.get("/Rect") or [0, 0, 0, 0]
                rect = tuple(float(value) for value in rect_obj[:4])
                appearance_states: List[str] = []
                appearance = annotation.get("/AP")
                if appearance:
                    normal = appearance.get("/N")
                    try:
                        normal_obj = normal.get_object() if normal is not None else None
                    except AttributeError:
                        normal_obj = normal
                    if isinstance(normal_obj, DictionaryObject):
                        appearance_states = [str(key) for key in normal_obj.keys()]

                widgets_by_name.setdefault(str(name), []).append(
                    PdfWidgetInfo(
                        page_number=page_index,
                        rect=rect,
                        appearance_states=tuple(appearance_states),
                    )
                )

        result: Dict[str, PdfFormFieldInfo] = {}
        field_names = set(str(name) for name in raw_fields.keys()) | set(widgets_by_name)
        for name in sorted(field_names):
            raw = raw_fields.get(name) or {}
            result[name] = PdfFormFieldInfo(
                name=name,
                field_type=str(raw.get("/FT") or ""),
                value=self._clean_pdf_value(raw.get("/V")),
                default_value=self._clean_pdf_value(raw.get("/DV")),
                flags=int(raw.get("/Ff") or 0),
                widgets=tuple(widgets_by_name.get(name, [])),
            )
        return result

    def inspect_pages(
        self,
        pdf_path: str | Path,
        page_numbers: Sequence[int],
    ) -> Dict[str, PdfFormFieldInfo]:
        wanted = {int(page) for page in page_numbers}
        fields = self.inspect(pdf_path)
        return {
            name: info
            for name, info in fields.items()
            if any(page in wanted for page in info.pages)
        }

    @staticmethod
    def _clean_pdf_value(value: object) -> str:
        if value is None:
            return ""
        text = str(value)
        if text.startswith("/"):
            text = text[1:]
        return text
