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

        if mapping.errors:
            result.errors.extend(mapping.errors)
            return result

        try:
            result.worksheet_rows = self.worksheet_mapper.map_items(mapping.items)
        except Exception as exc:
            result.errors.append(str(exc))
            return result

        result.current_year = self._infer_tax_year(batch)
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
    def _norm_header(value: object) -> str:
        return " ".join(str(value or "").strip().rstrip("*").lower().split())
