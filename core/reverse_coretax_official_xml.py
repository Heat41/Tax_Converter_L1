from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from core.coretax_official_schema import get_official_schema
from core.reverse_coretax_mapping import (
    CATEGORY_ORDER,
    ReverseCoretaxMappingService,
    ReverseCoretaxPackage,
    ReverseCoretaxRow,
)


XML_CATEGORY_ORDER = tuple(
    category
    for category in CATEGORY_ORDER
    if get_official_schema(category).has_xml_reference
)


@dataclass(frozen=True)
class OfficialXmlExportIssue:
    code: str
    severity: str
    message: str
    category: Optional[str] = None


@dataclass
class OfficialXmlExportResult:
    output_dir: Path
    files: Dict[str, Path] = field(default_factory=dict)
    row_counts: Dict[str, int] = field(default_factory=dict)
    unsupported_categories: List[str] = field(default_factory=list)
    issues: List[OfficialXmlExportIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[OfficialXmlExportIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> List[OfficialXmlExportIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors


class OfficialCoretaxXmlExporter:
    """Stage 8D.4D - exporter XML berdasarkan referensi XML Coretax yang dikunci.

    Hanya kategori yang memiliki xml_root, xml_list, dan xml_fields pada
    coretax_official_schema yang diekspor. Kategori tanpa referensi XML tidak
    pernah ditebak.
    """

    @staticmethod
    def _text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @staticmethod
    def _meta(
        row: ReverseCoretaxRow,
        key: str,
        fallback: object = "",
    ) -> object:
        value = row.official_metadata.get(key)
        if value is None or value == "":
            return fallback
        return value

    @classmethod
    def _field_values(cls, row: ReverseCoretaxRow) -> Dict[str, object]:
        category = row.kategori

        if category == "KAS":
            return {
                "Code": row.kode_harta,
                "AccountNumber": cls._meta(
                    row, "account_number", row.nomor_akun_keterangan
                ),
                "AccountOnBehalfOf": cls._meta(
                    row, "account_on_behalf_of", row.atas_nama
                ),
                "BankName": cls._meta(row, "bank_name", row.nama_bank),
                "Country": cls._meta(row, "country"),
                "Year": cls._meta(row, "year", row.tahun_perolehan),
                "Balance": cls._meta(row, "balance", row.nilai),
            }

        if category == "INVESTASI":
            return {
                "Code": row.kode_harta,
                "Country": cls._meta(row, "country"),
                "BankTIN": cls._meta(row, "institution_tin"),
                "BankName": cls._meta(
                    row, "institution_name", row.atas_nama or row.nama_bank
                ),
                "AccountNumber": cls._meta(
                    row, "account_number", row.nomor_akun_keterangan
                ),
                "CostOfAcquisition": cls._meta(
                    row, "cost_of_acquisition"
                ),
                "Year": cls._meta(row, "year", row.tahun_perolehan),
                "CurrentBalance": cls._meta(
                    row, "current_balance", row.nilai
                ),
                "Remarks": cls._meta(row, "remarks"),
            }

        if category == "BERGERAK":
            return {
                "Code": row.kode_harta,
                "AssetModel": cls._meta(row, "asset_model", row.nama_harta),
                "PoliceRegistrationNumber": cls._meta(
                    row,
                    "police_registration_number",
                    row.nomor_akun_keterangan,
                ),
                "OwnershipType": cls._meta(row, "ownership_type"),
                "OwnershipTIN": cls._meta(row, "ownership_tin"),
                "OwnershipName": cls._meta(
                    row, "ownership_name", row.atas_nama
                ),
                "Year": cls._meta(row, "year", row.tahun_perolehan),
                "CostOfAcquisition": cls._meta(
                    row, "cost_of_acquisition"
                ),
                "FairMarketValue": cls._meta(
                    row, "fair_market_value", row.nilai
                ),
            }

        if category == "HTB":
            return {
                "Code": row.kode_harta,
                "LocationOfAsset": cls._meta(
                    row,
                    "location_of_asset",
                    row.nomor_akun_keterangan,
                ),
                "PropertySizeLand": cls._meta(row, "property_size_land"),
                "PropertySizeBuilding": cls._meta(
                    row, "property_size_building"
                ),
                "SourceOfOwnership": cls._meta(
                    row, "source_of_ownership"
                ),
                "CertificateNumber": cls._meta(
                    row, "certificate_number"
                ),
                "Year": cls._meta(row, "year", row.tahun_perolehan),
                "CostOfAcquisition": cls._meta(
                    row, "cost_of_acquisition"
                ),
                "FairMarketValue": cls._meta(
                    row, "fair_market_value", row.nilai
                ),
            }

        raise ValueError(
            f"Kategori {category} belum memiliki referensi XML Coretax resmi."
        )

    @classmethod
    def _build_tree(
        cls,
        category: str,
        rows: List[ReverseCoretaxRow],
    ) -> ET.ElementTree:
        schema = get_official_schema(category)
        if not schema.has_xml_reference:
            raise ValueError(
                f"Kategori {category} tidak memiliki referensi XML resmi."
            )

        root = ET.Element(schema.xml_root)

        for row in rows:
            item = ET.SubElement(root, schema.xml_list)
            values = cls._field_values(row)

            for field_name in schema.xml_fields:
                node = ET.SubElement(item, field_name)
                node.text = cls._text(values.get(field_name, ""))

        try:
            ET.indent(root, space="  ")
        except AttributeError:
            pass

        return ET.ElementTree(root)

    @staticmethod
    def _filename(category: str) -> str:
        schema = get_official_schema(category)
        return f"{schema.xml_root}.xml"

    def export_package(
        self,
        package: ReverseCoretaxPackage,
        output_dir: str | Path,
    ) -> OfficialXmlExportResult:
        target_dir = Path(output_dir)
        result = OfficialXmlExportResult(output_dir=target_dir)

        if not package.can_export:
            result.issues.append(
                OfficialXmlExportIssue(
                    "RCX4D_001",
                    "ERROR",
                    "Paket reverse Coretax belum valid untuk export XML resmi.",
                )
            )
            return result

        active_categories = tuple(
            category
            for category in CATEGORY_ORDER
            if package.rows_by_category.get(category)
        )

        for category in active_categories:
            schema = get_official_schema(category)
            if not schema.has_xml_reference:
                result.unsupported_categories.append(category)
                result.issues.append(
                    OfficialXmlExportIssue(
                        "RCX4D_101",
                        "WARNING",
                        (
                            f"XML {category} tidak dibuat karena referensi XML "
                            "resmi belum tersedia pada Stage 8D.4A."
                        ),
                        category,
                    )
                )

        target_dir.mkdir(parents=True, exist_ok=True)

        for category in active_categories:
            schema = get_official_schema(category)
            if not schema.has_xml_reference:
                continue
            rows = package.rows_by_category.get(category, [])
            tree = self._build_tree(category, rows)
            target = target_dir / self._filename(category)
            tree.write(
                target,
                encoding="utf-8",
                xml_declaration=True,
                short_empty_elements=True,
            )
            result.files[category] = target
            result.row_counts[category] = len(rows)

        if result.ok:
            result.issues.append(
                OfficialXmlExportIssue(
                    "RCX4D_INFO",
                    "INFO",
                    (
                        f"{len(result.files)} file XML dibuat hanya untuk kategori "
                        "berisi data yang memiliki referensi XML terkunci."
                    ),
                )
            )

        return result

    def export_active_final(
        self,
        npwp: str,
        tahun_pajak: int,
        output_dir: str | Path,
        *,
        db_path: Optional[str | Path] = None,
    ) -> OfficialXmlExportResult:
        package = ReverseCoretaxMappingService(
            db_path=db_path
        ).build_active_final(npwp, tahun_pajak)

        result = self.export_package(package, output_dir)

        for issue in package.issues:
            if issue.severity in {"ERROR", "WARNING"}:
                result.issues.append(
                    OfficialXmlExportIssue(
                        issue.code,
                        issue.severity,
                        issue.message,
                    )
                )

        return result
