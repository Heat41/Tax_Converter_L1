from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.reconciliation import ReconciliationResult
from core.finalization import FinalizationInput
from core.legacy_1770_hybrid_xlsx import Legacy1770HybridXlsxService
from core.mapping.worksheet_harta_mapper import WorksheetHartaRow
from core.worksheet_pph_state import WorksheetBupotRow


def _analysis() -> ReconciliationResult:
    return ReconciliationResult(
        total_harta_sebelumnya=1_245_000_000.0,
        total_harta_berjalan=1_385_268_584.0,
        total_utang_sebelumnya=0.0,
        total_utang_berjalan=0.0,
        naik_turun_harta_utang=140_268_584.0,
        biaya_hidup_setahun=84_000_000.0,
        pajak_pajak=486_900.0,
        pengeluaran_lain_lain=0.0,
        kerugian_keuntungan_penjualan_aset=0.0,
        utang_baru_atas_kredit=0.0,
        harta_baru_dari_kredit=0.0,
        total_pengeluaran=224_755_484.0,
        penghasilan_bruto_umkm=1_289_695_000.0,
        penambahan_penghasilan_bruto_umkm=0.0,
        margin_usaha=0.0,
        jumlah_penghasilan_bruto_final=1_289_695_000.0,
        jumlah_penghasilan_bukan_objek=0.0,
        penghasilan_netto=224_755_484.0,
        selisih_pengeluaran_vs_penghasilan=0.0,
    )


def _sample_input() -> FinalizationInput:
    harta = [
        WorksheetHartaRow(
            nomor=1,
            kode_eform="012",
            kode_ct="0102",
            nama_harta="Tabungan",
            nomor_akun_keterangan="BANK-001",
            atas_nama="WP CONTOH",
            nama_bank="BANK CONTOH",
            tahun_perolehan=2024,
            nilai_tahun_sebelumnya=735_000_000.0,
            nilai_tahun_berjalan=867_325_000.0,
        ),
        WorksheetHartaRow(
            nomor=2,
            kode_eform="011",
            kode_ct="0101",
            nama_harta="Uang Tunai",
            nomor_akun_keterangan="-",
            atas_nama="WP CONTOH",
            nama_bank="-",
            tahun_perolehan=2024,
            nilai_tahun_sebelumnya=180_000_000.0,
            nilai_tahun_berjalan=200_000_000.0,
        ),
        WorksheetHartaRow(
            nomor=3,
            kode_eform="032",
            kode_ct="0302",
            nama_harta="Saham",
            nomor_akun_keterangan="AKTA-34",
            atas_nama="WP CONTOH",
            nama_bank="-",
            tahun_perolehan=2019,
            nilai_tahun_sebelumnya=330_000_000.0,
            nilai_tahun_berjalan=317_943_584.0,
        ),
    ]

    bupot = [
        WorksheetBupotRow(
            jenis="BP21",
            no_bupot="TEST-EFORM-001",
            masa="01",
            tahun="2025",
            sifat="TIDAK FINAL",
            status="NORMAL",
            npwp_penerima="6171015911930002",
            nama_penerima="WP CONTOH",
            fasilitas="",
            jenis_pph="Pasal 21",
            kop="21-100-07",
            bruto=120_000_000.0,
            dpp_persen=50.0,
            tarif=5.0,
            pengurang=110_262_344.0,
            pph_dipotong=486_883.0,
            bukti="Bukti Potong",
            no_bukti="DOC-001",
            tanggal_bukti="31/12/2025",
            npwp_pemotong="0072103856707000",
            nama_pemotong="PEMBERI KERJA CONTOH",
            tanggal_pemotongan="31/12/2025",
            mekanisme_sp2d="",
            no_sp2d="",
            npwp_pemberi_kerja="0072103856707000",
        )
    ]

    return FinalizationInput(
        npwp="6171015911930002",
        nama_wp="WP CONTOH VISUAL",
        tahun_pajak=2025,
        harta_current_rows=harta,
        harta_original_hash="visual-test-original",
        bupot_rows=bupot,
        pph_components={
            "penghasilan_neto_lainnya": 54_001_000.0,
            "pengurang_penghasilan_neto": 0.0,
            "ptkp": 54_000_000.0,
            "pph_terutang": 486_900.0,
            "kredit_pajak": 486_883.0,
            "pph25": 0.0,
        },
        umkm_state={
            "bruto_bulanan": [
                110_000_000.0,
                100_000_000.0,
                105_000_000.0,
                108_000_000.0,
                112_000_000.0,
                106_000_000.0,
                109_000_000.0,
                104_000_000.0,
                107_000_000.0,
                111_000_000.0,
                108_000_000.0,
                109_695_000.0,
            ],
            "pph_setor_bulanan": [0.0] * 12,
        },
        penghasilan_lainnya={
            "domestic_other_enabled": True,
            "domestic_other_dpp": 54_001_000.0,
            "prive_dpp": 0.0,
            "hibah_warisan_dpp": 0.0,
            "final_other_rows": [],
        },
        zakat=0.0,
        status_ptkp="TK/0",
        pph_calc_result={
            "total_netto_bupot": 9_737_656.0,
            "penghasilan_neto_lainnya": 54_001_000.0,
            "pengurang_penghasilan_neto": 0.0,
            "penghasilan_neto_sebelum_pengurang": 63_738_000.0,
            "penghasilan_neto_gabungan": 63_738_000.0,
            "ptkp": 54_000_000.0,
            "pkp": 9_738_000.0,
            "pph_terutang": 486_900.0,
            "kredit_pajak": 486_883.0,
            "pph25": 0.0,
            "kurang_lebih_bayar": 17.0,
            "kurang_lebih_bayar_pembulatan": 0.0,
        },
        analisis_result=_analysis(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate workbook visual test HYBRID 1770."
    )
    parser.add_argument(
        "--output",
        default="output/1770_hybrid_visual_test.xlsx",
        help="Path output workbook .xlsx",
    )
    args = parser.parse_args()

    output = Path(args.output)
    result = Legacy1770HybridXlsxService().export(
        _sample_input(),
        output,
        revision=1,
        snapshot_hash="VISUAL-TEST-SNAPSHOT",
    )

    if not result.ok:
        for issue in result.issues:
            print(f"[{issue.severity}] {issue.code}: {issue.message}")
        return 1

    print("=" * 62)
    print("HYBRID XLSX VISUAL TEST BERHASIL")
    print("=" * 62)
    print(f"File      : {result.output_path.resolve()}")
    print("Cek keenam sheet visual:")
    print("  1. 01 eForm Induk H1          -> format baru")
    print("  2. 02 eForm Induk H2          -> format baru")
    print("  3. 03 Legacy Lamp I H2        -> format lama")
    print("  4. 04 Legacy Lamp II          -> format lama")
    print("  5. 05 Legacy Lamp III         -> format lama")
    print("  6. 06 Legacy Lamp IV          -> format lama")
    print()
    print("Pastikan seluruh halaman menggunakan kertas Legal dan proporsi tidak melebar.")
    print("Khusus Lampiran IV, cek data Harta, JUMLAH BAGIAN A, serta struktur Bagian B dan C.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
