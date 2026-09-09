from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict

from core.finalization import FinalizationInput
from core.worksheet_state import WorksheetHartaStateStore


class FinalizationAdapter:
    """Mengubah state domain Worksheet yang sudah disimpan menjadi FinalizationInput.

    Adapter sengaja tidak membaca QTableWidget/QLineEdit. Ia hanya memakai state
    model yang dipelihara WorksheetPage dan flag dirty melalui method domain yang
    sudah tersedia pada halaman Worksheet.
    """

    @staticmethod
    def _dataclass_dict(value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return dict(value)
        return {}

    @classmethod
    def from_worksheet(cls, worksheet) -> FinalizationInput:
        result = getattr(worksheet, "harta_pipeline_result", None)
        if result is None:
            return FinalizationInput(
                npwp="",
                nama_wp="",
                tahun_pajak=0,
                harta_current_rows=[],
                harta_original_hash="",
                bupot_rows=[],
                pph_components={},
                umkm_state={},
                penghasilan_lainnya={},
                zakat=0.0,
                status_ptkp="",
                pph_calc_result={},
                analisis_result=getattr(worksheet, "_last_reconciliation", None),
                is_harta_dirty=False,
                is_pph_dirty=False,
                is_analisis_dirty=False,
            )

        npwp = str(
            getattr(worksheet, "harta_npwp", None)
            or getattr(result, "npwp", None)
            or ""
        )
        nama_wp = str(getattr(result, "nama_wp", None) or "")
        tahun_pajak = int(getattr(result, "current_year", 0) or 0)

        original_rows = list(getattr(worksheet, "harta_original_rows", []) or [])
        saved_harta = list(
            getattr(worksheet, "harta_saved_rows", None)
            or getattr(worksheet, "harta_current_rows", [])
            or []
        )
        original_hash = (
            WorksheetHartaStateStore.original_hash(original_rows)
            if original_rows
            else ""
        )

        bupot_rows = list(getattr(worksheet, "_bupot_saved_rows", []) or [])
        pph_components = dict(getattr(worksheet, "_pph_saved_components", {}) or {})

        status_ptkp = str(
            getattr(worksheet, "_saved_status_ptkp", None)
            or getattr(worksheet, "_status_ptkp", None)
            or ""
        )
        pph_components["status_ptkp"] = status_ptkp

        umkm_state = {
            "bruto_bulanan": list(getattr(worksheet, "_saved_umkm_bruto", []) or []),
            "pph_setor_bulanan": list(
                getattr(worksheet, "_saved_umkm_pph_setor", []) or []
            ),
        }

        other_income = dict(
            getattr(worksheet, "_saved_other_income_state", {}) or {}
        )
        final_other_rows = list(
            getattr(worksheet, "_saved_final_other_income_rows", []) or []
        )
        other_income["final_other_rows"] = [
            cls._dataclass_dict(row) for row in final_other_rows
        ]
        zakat = float(other_income.get("zakat", 0.0) or 0.0)

        pph_calc_result = cls._dataclass_dict(
            getattr(worksheet, "_last_pph_calculation", None)
        )
        analisis_result = getattr(worksheet, "_last_reconciliation", None)

        is_harta_dirty = bool(
            getattr(worksheet, "_has_unsaved_harta_changes", lambda: False)()
        )
        is_pph_dirty = bool(
            getattr(worksheet, "_has_unsaved_bupot_changes", lambda: False)()
            or getattr(
                worksheet, "_has_unsaved_pph_component_changes", lambda: False
            )()
        )
        current_reconciliation = dict(
            getattr(worksheet, "_reconciliation_manual", {}) or {}
        )
        saved_reconciliation = dict(
            getattr(worksheet, "_saved_reconciliation_manual", {}) or {}
        )
        is_analisis_dirty = current_reconciliation != saved_reconciliation

        return FinalizationInput(
            npwp=npwp,
            nama_wp=nama_wp,
            tahun_pajak=tahun_pajak,
            harta_current_rows=saved_harta,
            harta_original_hash=original_hash,
            bupot_rows=bupot_rows,
            pph_components=pph_components,
            umkm_state=umkm_state,
            penghasilan_lainnya=other_income,
            zakat=zakat,
            status_ptkp=status_ptkp,
            pph_calc_result=pph_calc_result,
            analisis_result=analisis_result,
            is_harta_dirty=is_harta_dirty,
            is_pph_dirty=is_pph_dirty,
            is_analisis_dirty=is_analisis_dirty,
        )
