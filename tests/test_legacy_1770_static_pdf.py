from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    NameObject,
    TextStringObject,
)

from core.legacy_1770_static_pdf import Legacy1770StaticPdfService


def _make_interactive_pdf(path: Path):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=936)

    annotation = DictionaryObject()
    annotation.update(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Text"),
            NameObject("/Contents"): TextStringObject("test"),
        }
    )
    page[NameObject("/Annots")] = ArrayObject([annotation])

    writer._root_object[NameObject("/AcroForm")] = DictionaryObject()
    writer._root_object[NameObject("/OpenAction")] = DictionaryObject()
    writer._root_object[NameObject("/AA")] = DictionaryObject()
    writer._root_object[NameObject("/Names")] = DictionaryObject()

    with path.open("wb") as handle:
        writer.write(handle)


def test_write_static_copy_removes_interactive_objects(tmp_path):
    source = tmp_path / "source.pdf"
    target = tmp_path / "target.pdf"
    _make_interactive_pdf(source)

    Legacy1770StaticPdfService._write_static_copy(source, target)

    reader = PdfReader(str(target))
    root = reader.trailer["/Root"]

    assert len(reader.pages) == 1
    assert "/AcroForm" not in root
    assert "/OpenAction" not in root
    assert "/AA" not in root
    assert "/Names" not in root
    assert "/Annots" not in reader.pages[0]
    assert "/AA" not in reader.pages[0]


def test_inspect_static_pdf_accepts_clean_pdf(tmp_path):
    target = tmp_path / "clean.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=936)
    with target.open("wb") as handle:
        writer.write(handle)

    result = Legacy1770StaticPdfService.inspect_static_pdf(target)

    assert result.ok is True
    assert result.is_static is True
    assert result.page_count == 1
    assert result.size_bytes > 0
    assert len(result.sha256) == 64


def test_inspect_static_pdf_rejects_annotations(tmp_path):
    target = tmp_path / "interactive.pdf"
    _make_interactive_pdf(target)

    result = Legacy1770StaticPdfService.inspect_static_pdf(target)

    assert result.ok is False
    assert result.is_static is False
    assert any(issue.code in {"S10_003", "S10_004"} for issue in result.errors)


def test_static_copy_preserves_page_geometry(tmp_path):
    source = tmp_path / "source.pdf"
    target = tmp_path / "target.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=936)
    writer.add_blank_page(width=558, height=792)
    with source.open("wb") as handle:
        writer.write(handle)

    Legacy1770StaticPdfService._write_static_copy(source, target)

    before = PdfReader(str(source))
    after = PdfReader(str(target))

    assert len(before.pages) == len(after.pages)
    for source_page, target_page in zip(before.pages, after.pages):
        assert float(source_page.mediabox.width) == float(target_page.mediabox.width)
        assert float(source_page.mediabox.height) == float(target_page.mediabox.height)
