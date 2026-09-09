from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Sequence


class SectionState(str, Enum):
    EMPTY = "EMPTY"
    AVAILABLE = "AVAILABLE"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class SectionValidationIssue:
    code: str
    severity: str
    message: str
    field: str = ""


@dataclass(frozen=True)
class SectionRule:
    name: str
    required_when_present: tuple[str, ...] = ()
    optional_fields: tuple[str, ...] = ()
    allow_empty: bool = True


@dataclass
class SectionValidationResult:
    section: str
    state: SectionState
    issues: List[SectionValidationIssue] = field(default_factory=list)

    @property
    def can_export(self) -> bool:
        return self.state in {SectionState.EMPTY, SectionState.AVAILABLE, SectionState.INCOMPLETE}


# Nama field mengikuti AcroForm PDF 1770 resmi, bukan koordinat visual.
INDUK_FIELDS: Dict[str, str] = {
    "npwp": "NPWP",
    "nama_wp": "Nama Wajib Pajak",
    "tahun_pajak": "Tahun Pajak",
    "penghasilan_usaha": "PNUsaha",
    "penghasilan_pekerjaan": "PNInduk",
    "penghasilan_lainnya": "JumlahBagianD",
    "zakat": "ZakatSumbanganWajib",
    "neto_setelah_zakat": "PNsetelahZakat",
    "neto_setelah_kompensasi": "PNsetelahKompen",
    "ptkp": "PTKP",
    "pkp": "PKP",
    "pph_terutang": "PPhTerutang",
    "jumlah_pph_terutang": "JumlahPPhTerutang",
    "kredit_pajak": "IIJBAinduk",
    "pph25": "JumlahPPh25",
    "kurang_lebih_bayar": "PPhLebihKurangDibayar",
}

LAMPIRAN_I_FIELDS: Dict[str, str] = {
    "jumlah_omzet": "jumlahomzet",
    "jumlah_bagian_b": "JumlahBagianB",
    "jumlah_bagian_c": "JumlahBagianC",
    "jumlah_bagian_d": "JumlahBagianD",
}

LAMPIRAN_II_FIELDS: Dict[str, str] = {
    "jumlah_pph_dipotong": "IIJBA",
}

LAMPIRAN_III_FIELDS: Dict[str, str] = {
    "jumlah_pph_final": "IIIJumlahPPhFinalA17",
    "jumlah_bukan_objek": "IIIJumlahPBBukanObjekB7",
}

LAMPIRAN_IV_FIELDS: Dict[str, str] = {
    "jumlah_harta": "IVJumlahHargaPerolehanHarta",
    "jumlah_utang": "IVJUmlahSisaUtang",
}


SECTION_RULES: Dict[str, SectionRule] = {
    "induk": SectionRule(
        "induk",
        required_when_present=("npwp", "nama_wp", "tahun_pajak"),
        optional_fields=tuple(key for key in INDUK_FIELDS if key not in {"npwp", "nama_wp", "tahun_pajak"}),
        allow_empty=False,
    ),
    "lampiran_i": SectionRule(
        "lampiran_i",
        required_when_present=(),
        optional_fields=(
            "penghasilan_usaha",
            "bupot_pekerjaan",
            "penghasilan_lainnya",
        ),
        allow_empty=True,
    ),
    "lampiran_ii": SectionRule(
        "lampiran_ii",
        required_when_present=(
            "npwp_pemotong",
            "no_bupot",
            "tanggal_bupot",
            "jenis_pph",
            "pph_dipotong",
        ),
        optional_fields=("nama_pemotong",),
        allow_empty=True,
    ),
    "lampiran_iii": SectionRule(
        "lampiran_iii",
        required_when_present=(),
        optional_fields=("penghasilan_final", "penghasilan_bukan_objek"),
        allow_empty=True,
    ),
    "lampiran_iv_harta": SectionRule(
        "lampiran_iv_harta",
        required_when_present=(
            "kode_harta",
            "nama_harta",
            "tahun_perolehan",
            "harga_perolehan",
        ),
        optional_fields=("keterangan",),
        allow_empty=True,
    ),
    "lampiran_iv_utang": SectionRule(
        "lampiran_iv_utang",
        required_when_present=(
            "kode_utang",
            "nama_pemberi_pinjaman",
            "tahun_pinjaman",
            "jumlah_utang",
        ),
        optional_fields=("alamat_pemberi_pinjaman",),
        allow_empty=True,
    ),
    "lampiran_iv_keluarga": SectionRule(
        "lampiran_iv_keluarga",
        required_when_present=("nama", "nik", "hubungan_keluarga"),
        optional_fields=("pekerjaan",),
        allow_empty=True,
    ),
}


class LegacyPdfCompletenessValidator:
    """Menentukan EMPTY/AVAILABLE/INCOMPLETE/INVALID secara adaptif per WP."""

    EMPTY_VALUES = (None, "", [], (), {})

    def validate_record_section(
        self,
        section: str,
        records: Sequence[Mapping[str, object]],
    ) -> SectionValidationResult:
        rule = SECTION_RULES[section]
        meaningful = [record for record in records if self._record_has_any_value(record)]
        if not meaningful:
            if rule.allow_empty:
                return SectionValidationResult(section, SectionState.EMPTY)
            return SectionValidationResult(
                section,
                SectionState.INVALID,
                [SectionValidationIssue("PDF_SEC_001", "ERROR", f"Bagian {section} wajib tersedia.")],
            )

        issues: List[SectionValidationIssue] = []
        invalid = False
        incomplete = False
        for row_number, record in enumerate(meaningful, start=1):
            for field_name in rule.required_when_present:
                if self._is_empty(record.get(field_name)):
                    incomplete = True
                    issues.append(
                        SectionValidationIssue(
                            "PDF_SEC_101",
                            "WARNING",
                            f"{section} baris {row_number}: field {field_name} belum lengkap.",
                            field_name,
                        )
                    )

            for key, value in record.items():
                if key.startswith("invalid_") and bool(value):
                    invalid = True
                    field_name = key.removeprefix("invalid_")
                    issues.append(
                        SectionValidationIssue(
                            "PDF_SEC_201",
                            "ERROR",
                            f"{section} baris {row_number}: field {field_name} tidak valid.",
                            field_name,
                        )
                    )

        if invalid:
            state = SectionState.INVALID
        elif incomplete:
            state = SectionState.INCOMPLETE
        else:
            state = SectionState.AVAILABLE
        return SectionValidationResult(section, state, issues)

    def validate_single_section(
        self,
        section: str,
        values: Mapping[str, object],
    ) -> SectionValidationResult:
        return self.validate_record_section(section, [values])

    @classmethod
    def _record_has_any_value(cls, record: Mapping[str, object]) -> bool:
        return any(not cls._is_empty(value) for key, value in record.items() if not key.startswith("invalid_"))

    @classmethod
    def _is_empty(cls, value: object) -> bool:
        return value is None or value == "" or value == [] or value == () or value == {}


def expected_acroform_fields() -> set[str]:
    """Field minimum yang harus ada pada template resmi untuk tahap 8C awal."""
    result = set(INDUK_FIELDS.values())
    result.update(LAMPIRAN_I_FIELDS.values())
    result.update(LAMPIRAN_II_FIELDS.values())
    result.update(LAMPIRAN_III_FIELDS.values())
    result.update(LAMPIRAN_IV_FIELDS.values())
    result.update({
        "NamaPemberiKerja1",
        "NPWPPemberiKerja1",
        "IIANama1",
        "IIANPWP1",
        "IIANoBuktiPotong1",
        "IIATglBuktiPotong1",
        "IIAJenisPajak1",
        "IIAPPhDipotong1",
        "KodeHarta1",
        "NamaHarta1",
        "TahunPerolehan1",
        "IVHargaPerolehanHarta1",
        "IVKeterangan1",
    })
    return result
