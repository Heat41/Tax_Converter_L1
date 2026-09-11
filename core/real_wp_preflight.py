from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from config.database import get_db_connection
from core.coretax_official_schema import get_official_schema
from core.reverse_coretax_mapping import (
    CATEGORY_ORDER,
    ReverseCoretaxMappingService,
    ReverseCoretaxPackage,
)


@dataclass(frozen=True)
class RealWpPreflightIssue:
    code: str
    severity: str
    message: str
    category: Optional[str] = None
    row_number: Optional[int] = None


@dataclass
class RealWpPreflightResult:
    npwp: str
    tahun_pajak: int
    package: ReverseCoretaxPackage
    active_categories: List[str] = field(default_factory=list)
    category_counts: Dict[str, int] = field(default_factory=dict)
    template_files: Dict[str, Path] = field(default_factory=dict)
    missing_templates: List[str] = field(default_factory=list)
    missing_metadata: Dict[str, Dict[int, List[str]]] = field(default_factory=dict)
    issues: List[RealWpPreflightIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[RealWpPreflightIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[RealWpPreflightIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def ready(self) -> bool:
        return not self.errors and self.package.can_export


class RealWpPreflightService:
    """Stage 8D.4J - audit snapshot FINAL nyata sebelum export.

    Missing metadata dilaporkan, bukan diisi otomatis. Template hanya wajib untuk
    kategori yang memiliki data.
    """

    METADATA_KEYS = {
        "KAS": (
            "account_number",
            "account_on_behalf_of",
            "bank_name",
            "country",
            "year",
            "balance",
        ),
        "PIUTANG": (
            "country",
            "identity_number",
            "receivable_name",
            "receivable_value",
            "year",
            "receivable_balance",
        ),
        "INVESTASI": (
            "country",
            "institution_tin",
            "institution_name",
            "account_number",
            "cost_of_acquisition",
            "year",
            "current_balance",
        ),
        "BERGERAK": (
            "asset_model",
            "police_registration_number",
            "ownership_type",
            "ownership_tin",
            "ownership_name",
            "year",
            "cost_of_acquisition",
            "fair_market_value",
        ),
        "HTB": (
            "location_of_asset",
            "property_size_land",
            "property_size_building",
            "source_of_ownership",
            "certificate_number",
            "year",
            "cost_of_acquisition",
            "fair_market_value",
        ),
        "LAINNYA": (
            "year",
            "account_number",
            "additional_information",
            "cost_of_acquisition",
            "current_value",
        ),
    }

    def __init__(
        self,
        *,
        db_path: Optional[str | Path] = None,
        template_dir: Optional[str | Path] = None,
    ):
        self.db_path = db_path
        self.template_dir = Path(template_dir) if template_dir else None

    @staticmethod
    def _normalize_filename(value: str) -> str:
        value = str(value or "").lower()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return " ".join(value.split())

    def _find_template(self, category: str) -> Optional[Path]:
        if self.template_dir is None or not self.template_dir.exists():
            return None

        hint = self._normalize_filename(
            get_official_schema(category).excel_filename_hint
        )
        candidates = []
        for path in self.template_dir.rglob("*.xlsx"):
            if hint in self._normalize_filename(path.stem):
                candidates.append(path)

        if not candidates:
            return None

        candidates.sort(
            key=lambda path: (
                abs(
                    len(self._normalize_filename(path.stem))
                    - len(hint)
                ),
                str(path).lower(),
            )
        )
        return candidates[0]

    @staticmethod
    def _is_missing(value: object) -> bool:
        return value is None or value == ""

    def inspect(
        self,
        npwp: str,
        tahun_pajak: int,
    ) -> RealWpPreflightResult:
        package = ReverseCoretaxMappingService(
            db_path=self.db_path
        ).build_active_final(
            npwp,
            tahun_pajak,
        )

        result = RealWpPreflightResult(
            npwp=package.npwp,
            tahun_pajak=int(tahun_pajak),
            package=package,
        )

        for issue in package.issues:
            if issue.severity in {"ERROR", "WARNING"}:
                result.issues.append(
                    RealWpPreflightIssue(
                        issue.code,
                        issue.severity,
                        issue.message,
                        row_number=issue.row_number,
                    )
                )

        for category in CATEGORY_ORDER:
            rows = package.rows_by_category.get(category, [])
            if not rows:
                continue

            result.active_categories.append(category)
            result.category_counts[category] = len(rows)

            template = self._find_template(category)
            if self.template_dir is not None:
                if template is None:
                    result.missing_templates.append(category)
                    result.issues.append(
                        RealWpPreflightIssue(
                            "RCX4J_001",
                            "ERROR",
                            (
                                "Template Excel untuk kategori berdata tidak "
                                "ditemukan."
                            ),
                            category,
                        )
                    )
                else:
                    result.template_files[category] = template

            required_keys = self.METADATA_KEYS.get(category, ())
            for row in rows:
                missing = [
                    key
                    for key in required_keys
                    if self._is_missing(row.official_metadata.get(key))
                ]
                if missing:
                    result.missing_metadata.setdefault(
                        category, {}
                    )[row.nomor] = missing
                    result.issues.append(
                        RealWpPreflightIssue(
                            "RCX4J_101",
                            "WARNING",
                            (
                                "Metadata sumber tidak tersedia untuk: "
                                + ", ".join(missing)
                                + ". Nilai akan tetap kosong; tidak dibuat-buat."
                            ),
                            category,
                            row.nomor,
                        )
                    )

        if package.can_export and not result.active_categories:
            result.issues.append(
                RealWpPreflightIssue(
                    "RCX4J_002",
                    "ERROR",
                    "Snapshot FINAL tidak memiliki kategori Harta aktif.",
                )
            )

        if result.ready:
            result.issues.append(
                RealWpPreflightIssue(
                    "RCX4J_INFO",
                    "INFO",
                    (
                        "Preflight siap: hanya kategori yang memiliki data "
                        "yang akan diekspor."
                    ),
                )
            )

        return result


def list_final_snapshots(
    *,
    db_path: Optional[str | Path] = None,
):
    conn = get_db_connection(db_path)
    try:
        return conn.execute(
            """
            SELECT npwp, nama_wp, tahun_pajak, revision, snapshot_hash,
                   finalized_at
            FROM worksheet_final_snapshots
            WHERE status = 'FINAL'
            ORDER BY finalized_at DESC, revision DESC
            """
        ).fetchall()
    finally:
        conn.close()
