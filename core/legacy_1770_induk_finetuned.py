from __future__ import annotations

from core.legacy_1770_induk import Legacy1770IndukService as BaseLegacy1770IndukService


class Legacy1770IndukService(BaseLegacy1770IndukService):
    """Compatibility alias untuk renderer Induk 1770 utama.

    Fine tuning sekarang dikunci langsung di ``core.legacy_1770_induk`` agar tidak
    ada dua sumber koordinat yang saling menimpa. Class ini dipertahankan supaya
    import lama tetap bekerja tanpa menggandakan overlay atau checkbox.
    """

    pass
