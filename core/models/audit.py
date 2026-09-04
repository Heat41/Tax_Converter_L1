from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from config.constants import AuditAction, AuditSource

@dataclass
class AuditTrailEntry:
    wp_id: int
    asset_id: int
    nama_kolom: str
    nilai_lama: Optional[str]
    nilai_baru: Optional[str]
    action: AuditAction = AuditAction.UPDATE
    source: AuditSource = AuditSource.USER_EDIT
    keterangan: Optional[str] = None
    id: Optional[int] = None
    waktu_koreksi: Optional[datetime] = None

    def __post_init__(self):
        if isinstance(self.action, str):
            self.action = AuditAction(self.action)
        if isinstance(self.source, str):
            self.source = AuditSource(self.source)
