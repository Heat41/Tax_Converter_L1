from dataclasses import asdict

from config.constants import JenisKepemilikan, KategoriL1
from core.mapping.worksheet_harta_mapper import WorksheetHartaMapper
from core.models.asset import HartaL1Item


def _map_one(item):
    return WorksheetHartaMapper().map_items([item])[0]


def test_cash_official_metadata_is_preserved_in_worksheet_row():
    row = _map_one(
        HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.KAS,
            kode_harta="0102",
            tahun_perolehan=2025,
            nomor_akun="116801005138508",
            atas_nama="DR EVY BACHTIAR SPOG",
            nama_bank_institusi="BRI",
            lokasi_negara="Indonesia",
            saldo_current=391742658,
            saldo_original=391742658,
        )
    )

    meta = row.coretax_metadata
    assert meta["account_number"] == "116801005138508"
    assert meta["account_on_behalf_of"] == "DR EVY BACHTIAR SPOG"
    assert meta["bank_name"] == "BRI"
    assert meta["country"] == "Indonesia"
    assert meta["balance"] == 391742658


def test_movable_asset_metadata_preserves_official_detail():
    row = _map_one(
        HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.BERGERAK,
            kode_harta="0403",
            tahun_perolehan=2025,
            merek_model="TOYOTA RAIZE",
            nomor_polisi_registrasi="KB 1476 PI",
            jenis_kepemilikan=JenisKepemilikan.TAXPAYER,
            npwp_pemilik="6101015612710001",
            nama_pemilik="EVY BACHTIAR",
            biaya_perolehan_current=343750000,
            nilai_saat_ini_current=325000000,
        )
    )

    meta = row.coretax_metadata
    assert meta["asset_model"] == "TOYOTA RAIZE"
    assert meta["police_registration_number"] == "KB 1476 PI"
    assert meta["ownership_type"] == "TAXPAYER"
    assert meta["ownership_tin"] == "6101015612710001"
    assert meta["cost_of_acquisition"] == 343750000
    assert meta["fair_market_value"] == 325000000


def test_non_movable_asset_metadata_preserves_dimensions_and_certificate():
    row = _map_one(
        HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.HTB,
            kode_harta="0501",
            tahun_perolehan=2021,
            lokasi_alamat="JAGUR KAB SAMBAS",
            luas_tanah="607 M2",
            luas_bangunan="-",
            sumber_kepemilikan="Own Income",
            nomor_sertifikat="14030604100666",
            biaya_perolehan_current=35000000,
            nilai_saat_ini_current=38000000,
        )
    )

    meta = row.coretax_metadata
    assert meta["location_of_asset"] == "JAGUR KAB SAMBAS"
    assert meta["property_size_land"] == "607 M2"
    assert meta["property_size_building"] == "-"
    assert meta["source_of_ownership"] == "Own Income"
    assert meta["certificate_number"] == "14030604100666"
    assert meta["fair_market_value"] == 38000000


def test_metadata_survives_dataclass_snapshot_serialization():
    row = _map_one(
        HartaL1Item(
            wp_id=1,
            kategori_l1=KategoriL1.INVESTASI,
            kode_harta="0305",
            tahun_perolehan=2025,
            nomor_identitas_institusi="6101015612710001",
            nama_institusi="EVY BACHTIAR",
            nomor_akun_bukti="1971197117",
            lokasi_negara="Indonesia",
            biaya_perolehan_current=1000000000,
            nilai_saat_ini_current=1000000000,
        )
    )

    payload = asdict(row)
    assert payload["coretax_metadata"]["institution_tin"] == "6101015612710001"
    assert payload["coretax_metadata"]["institution_name"] == "EVY BACHTIAR"
    assert payload["coretax_metadata"]["account_number"] == "1971197117"
    assert payload["coretax_metadata"]["current_balance"] == 1000000000
