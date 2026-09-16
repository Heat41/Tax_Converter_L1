from pathlib import Path
import tempfile

import pandas as pd

from config.database import init_database
from core.rekap_bupot_importer import RekapBupotImporter
from core.worksheet_pph_state import WorksheetPPhStateStore


def test_rekap_bupot_golden_headers_and_full_fields_roundtrip():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "rekap.xlsx"
        db_path = Path(temp) / "test.db"
        init_database(db_path)

        headers = [
            "NO", "JENIS BUPOT", "NO BUKPOT", "MASA", "TAHUN", "SIFAT", "STATUS",
            "NPWP PENERIMA", "NAMA PENERIMA", "FASILITAS", "JENIS PPH", "KOP",
            "BRUTO", "DPP PERSEN", "TARIF", "PENGURANG BRUTO", "PPH", "BUKTI",
            "NO BUKTI", "TANGGAL BUKTI", "NPWP PEMOTONG", "NAMA PEMOTONG",
            "TANGGAL PEMOTONGAN", "MEKANISME SP2D", "NO SP2D",
        ]
        values = [
            1, "BP21", "2502BG9RZ", "01", "2025", "TIDAK FINAL", "NORMAL",
            "6171042211890007", "VIKTOR OKTAVIUS", "", "Pasal 21", "21-100-07",
            500000, 50, 5, 250000, 12500, "Surat Tagihan",
            "597/CV.BMS/SSKP/VI/2025", "04/06/2025", "0072103856707000",
            "BERLIN MITRA SEJATI", "04/06/2025", "", "",
        ]
        pd.DataFrame([headers, values]).to_excel(path, index=False, header=False)

        store = WorksheetPPhStateStore(db_path)
        importer = RekapBupotImporter(pph_store=store)
        result = importer.parse(path)

        assert result.is_valid
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.jenis == "BP21"
        assert row.no_bupot == "2502BG9RZ"
        assert row.bruto == 500000
        assert row.pengurang == 250000
        assert row.pph_dipotong == 12500
        assert row.npwp_penerima == "6171042211890007"
        assert row.npwp_pemotong == "0072103856707000"
        assert row.kop == "21-100-07"

        importer.persist_replace(
            npwp="6171042211890007",
            tahun_pajak=2025,
            rows=result.rows,
        )
        saved = store.load("6171042211890007", 2025)
        assert saved is not None
        restored = saved.bupot_rows[0]
        assert restored.nama_pemotong == "BERLIN MITRA SEJATI"
        assert restored.no_bukti == "597/CV.BMS/SSKP/VI/2025"
        assert restored.dpp_persen == 50
