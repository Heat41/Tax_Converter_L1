import sys

from PySide6.QtWidgets import QApplication

from core.reverse_coretax_mapping import ReverseCoretaxPackage, ReverseCoretaxRow
from ui.coretax_package_preview import CoretaxPackagePreviewDialog


app = QApplication.instance() or QApplication(sys.argv)


def _package():
    package = ReverseCoretaxPackage(
        npwp="6101015612710001",
        nama_wp="EVY BACHTIAR",
        tahun_pajak=2025,
        revision=5,
    )
    package.rows_by_category["KAS"].append(
        ReverseCoretaxRow(
            nomor=1,
            kategori="KAS",
            kode_harta="0102",
            nama_harta="Tabungan",
            tahun_perolehan=2025,
            nilai=1000000,
            nomor_akun_keterangan="ACC-01",
            atas_nama="EVY BACHTIAR",
            nama_bank="BRI",
        )
    )
    package.rows_by_category["HTB"].append(
        ReverseCoretaxRow(
            nomor=1,
            kategori="HTB",
            kode_harta="0501",
            nama_harta="Tanah",
            tahun_perolehan=2020,
            nilai=500000000,
            nomor_akun_keterangan="Pontianak",
            atas_nama="EVY BACHTIAR",
            nama_bank="",
        )
    )
    return package


def test_coretax_preview_only_shows_active_categories():
    dialog = CoretaxPackagePreviewDialog(_package())
    try:
        assert dialog.tabs.count() == 2
        assert dialog.tabs.tabText(0).startswith("KAS")
        assert dialog.tabs.tabText(1).startswith("HTB")
        assert "2 kategori aktif" == dialog.category_label.text()
        assert "2 baris" == dialog.row_count_label.text()
        assert "SIAP EXPORT" == dialog.status_label.text()
    finally:
        dialog.close()
        dialog.deleteLater()


def test_coretax_preview_does_not_add_empty_category_tabs():
    dialog = CoretaxPackagePreviewDialog(_package())
    try:
        tabs = [
            dialog.tabs.tabText(index)
            for index in range(dialog.tabs.count())
        ]
        assert all("PIUTANG" not in text for text in tabs)
        assert all("LAINNYA" not in text for text in tabs)
    finally:
        dialog.close()
        dialog.deleteLater()
