from enum import Enum

class KategoriL1(str, Enum):
    KAS = "KAS"
    PIUTANG = "PIUTANG"
    INVESTASI = "INVESTASI"
    BERGERAK = "BERGERAK"
    HTB = "HTB"
    LAINNYA = "LAINNYA"

class StatusProses(str, Enum):
    BELUM_IMPOR = "BELUM_IMPOR"
    DRAFT = "DRAFT"
    FINAL = "FINAL"

class JenisKepemilikan(str, Enum):
    TAXPAYER = "TAXPAYER"
    OTHER = "OTHER"

class AuditAction(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RE_IMPORT_RESET = "RE_IMPORT_RESET"
    RE_IMPORT_PRESERVE = "RE_IMPORT_PRESERVE"

class AuditSource(str, Enum):
    CORETAX_IMPORT = "CORETAX_IMPORT"
    USER_EDIT = "USER_EDIT"
    SYSTEM_CALCULATION = "SYSTEM_CALCULATION"
