import re
from dataclasses import dataclass, field
from typing import List, Optional

from core.mapping.harta_mapper import CoretaxHartaMapper, HartaMappingResult
from core.mapping.worksheet_harta_mapper import WorksheetHartaMapper, WorksheetHartaRow
from core.validation.models import BatchImportResult


@dataclass
class HartaPipelineResult:
    mapping: HartaMappingResult
    worksheet_rows: List[WorksheetHartaRow] = field(default_factory=list)
    current_year: Optional[int] = None
    npwp: Optional[str] = None
    nama_wp: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.mapping.is_valid and not self.errors


class HartaPreviewPipeline:
    """Bridge Stage 3B -> 3C -> 3F for UI preview/export."""

    def __init__(self):
        self.harta_mapper = CoretaxHartaMapper()
        self.worksheet_mapper = WorksheetHartaMapper()

    def build_from_batch(
        self,
        batch: BatchImportResult,
        *,
        wp_id: int = 0,
        import_batch_id: Optional[int] = None,
    ) -> HartaPipelineResult:
        mapping = self.harta_mapper.map_batch(
            batch,
            wp_id=wp_id,
            import_batch_id=import_batch_id,
        )
        result = HartaPipelineResult(mapping=mapping)
        result.current_year = self._infer_tax_year(batch)
        result.npwp = self._infer_npwp(batch)
        result.nama_wp = self._infer_nama_wp(batch)

        if mapping.errors:
            result.errors.extend(mapping.errors)
            return result

        try:
            result.worksheet_rows = self.worksheet_mapper.map_items(mapping.items)
        except Exception as exc:
            result.errors.append(str(exc))
            return result

        if not result.nama_wp:
            result.nama_wp = self._infer_unique_owner_name(result.worksheet_rows)

        return result

    @staticmethod
    def _infer_tax_year(batch: BatchImportResult) -> Optional[int]:
        for category_result in batch.category_results.values():
            read_result = category_result.read_result
            if read_result is None:
                continue

            headers = [HartaPreviewPipeline._norm_header(h) for h in read_result.headers]
            year_index = None
            for candidate in ("tahun pajak", "tahun"):
                if candidate in headers:
                    year_index = headers.index(candidate)
                    break
            if year_index is None:
                continue

            for row in read_result.rows:
                if year_index >= len(row):
                    continue
                value = str(row[year_index] or "").strip()
                if not value:
                    continue
                try:
                    return int(float(value.replace(",", "")))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _infer_npwp(batch: BatchImportResult) -> Optional[str]:
        for category_result in batch.category_results.values():
            read_result = category_result.read_result
            if read_result is None:
                continue

            headers = [HartaPreviewPipeline._norm_header(h) for h in read_result.headers]
            npwp_index = None
            for candidate in ("npwp", "npwp wajib pajak"):
                if candidate in headers:
                    npwp_index = headers.index(candidate)
                    break
            if npwp_index is None:
                continue

            for row in read_result.rows:
                if npwp_index >= len(row):
                    continue
                digits = re.sub(r"\D", "", str(row[npwp_index] or ""))
                if digits:
                    return digits
        return None

    @staticmethod
    def _infer_nama_wp(batch: BatchImportResult) -> Optional[str]:
        """Ambil Nama WP hanya dari kolom identitas yang eksplisit bila tersedia."""
        candidates = (
            "nama wajib pajak",
            "nama wp",
            "nama taxpayer",
            "taxpayer name",
        )
        for category_result in batch.category_results.values():
            read_result = category_result.read_result
            if read_result is None:
                continue

            headers = [HartaPreviewPipeline._norm_header(h) for h in read_result.headers]
            name_index = None
            for candidate in candidates:
                if candidate in headers:
                    name_index = headers.index(candidate)
                    break
            if name_index is None:
                continue

            for row in read_result.rows:
                if name_index >= len(row):
                    continue
                value = " ".join(str(row[name_index] or "").strip().split())
                if value:
                    return value
        return None

    @staticmethod
    def _infer_unique_owner_name(rows: List[WorksheetHartaRow]) -> Optional[str]:
        """Fallback konservatif: pakai ATAS NAMA hanya jika seluruh nama konsisten."""
        unique = {}
        for row in rows:
            name = " ".join(str(row.atas_nama or "").strip().split())
            if not name:
                continue
            unique.setdefault(name.casefold(), name)
        if len(unique) == 1:
            return next(iter(unique.values()))
        return None

    @staticmethod
    def _norm_header(value: object) -> str:
        return " ".join(str(value or "").strip().rstrip("*").lower().split())
