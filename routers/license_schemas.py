from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class LicenseBase(BaseModel):
    lisans_adi: str
    anahtar: str
    sorumlu_personel: Optional[str] = None
    bagli_envanter_no: Optional[str] = None
    ifs_no: Optional[str] = None
    tarih: Optional[str] = None
    islem_yapan: Optional[str] = None
    mail_adresi: Optional[str] = None


class LicenseCreate(LicenseBase):
    pass


class LicenseUpdate(BaseModel):
    lisans_adi: Optional[str] = None
    anahtar: Optional[str] = None
    sorumlu_personel: Optional[str] = None
    bagli_envanter_no: Optional[str] = None
    ifs_no: Optional[str] = None
    tarih: Optional[str] = None
    islem_yapan: Optional[str] = None
    mail_adresi: Optional[str] = None


class LicenseLogOut(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None
    changed_by: str
    changed_at: datetime

    class Config:
        from_attributes = True


class LicenseListOut(BaseModel):
    id: int
    bagli_envanter_no: str | None
    lisans_adi: str
    anahtar: str
    sorumlu_personel: str | None

    class Config:
        from_attributes = True


class LicenseDetailOut(LicenseBase):
    id: int
    logs: List[LicenseLogOut] = []

    class Config:
        from_attributes = True
