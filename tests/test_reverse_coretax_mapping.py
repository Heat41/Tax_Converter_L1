from core.reverse_coretax_mapping import ReverseCoretaxMappingService


def test_category_from_coretax_code_routes_six_l1_groups():
    service = ReverseCoretaxMappingService()

    assert service._category_from_code("0104") == "KAS"
    assert service._category_from_code("0201") == "PIUTANG"
    assert service._category_from_code("0305") == "INVESTASI"
    assert service._category_from_code("0402") == "BERGERAK"
    assert service._category_from_code("0501") == "HTB"
    assert service._category_from_code("0601") == "LAINNYA"
    assert service._category_from_code("0701") == "LAINNYA"


def test_reverse_mapping_uses_unique_eform_candidate_only():
    service = ReverseCoretaxMappingService()
    issues = []

    # 011 hanya berasal dari 0101 pada mapping saat ini.
    assert service._resolve_coretax_code(
        {"kode_ct": "", "kode_eform": "011"},
        1,
        issues,
    ) == "0101"
    assert issues == []


def test_reverse_mapping_refuses_ambiguous_eform_without_original_ct():
    service = ReverseCoretaxMappingService()
    issues = []

    # 019 dipakai oleh 0712 dan 0799, sehingga tidak boleh ditebak.
    assert service._resolve_coretax_code(
        {"kode_ct": "", "kode_eform": "019"},
        1,
        issues,
    ) is None
    assert issues
    assert issues[0].code == "RCT_104"
    assert issues[0].severity == "ERROR"


def test_original_coretax_code_has_priority_over_reverse_guess():
    service = ReverseCoretaxMappingService()
    issues = []

    assert service._resolve_coretax_code(
        {"kode_ct": "0799", "kode_eform": "019"},
        1,
        issues,
    ) == "0799"
    assert issues == []
