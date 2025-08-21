from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class PrinterBase(BaseModel):
    envanter_no: str
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    yazici_markasi: Optional[str] = None
    yazici_modeli: Optional[str] = None
    kullanim_alani: Optional[str] = None
    ip_adresi: Optional[str] = None
    mac: Optional[str] = None
    hostname: Optional[str] = None
    ifs_no: Optional[str] = None
    tarih: Optional[str] = None
    islem_yapan: Optional[str] = None
    sorumlu_personel: Optional[str] = None


class PrinterCreate(PrinterBase):
    pass


class PrinterUpdate(BaseModel):
    envanter_no: Optional[str] = None
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    yazici_markasi: Optional[str] = None
    yazici_modeli: Optional[str] = None
    kullanim_alani: Optional[str] = None
    ip_adresi: Optional[str] = None
    mac: Optional[str] = None
    hostname: Optional[str] = None
    ifs_no: Optional[str] = None
    tarih: Optional[str] = None
    islem_yapan: Optional[str] = None
    sorumlu_personel: Optional[str] = None


class PrinterLogOut(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None
    changed_by: str
    changed_at: datetime

    class Config:
        from_attributes = True


class PrinterListOut(BaseModel):
    id: int
    envanter_no: str
    brand_id: int | None
    model_id: int | None
    yazici_markasi: str | None
    yazici_modeli: str | None
    kullanim_alani: str | None
    ip_adresi: str | None
    mac: str | None
    hostname: str | None

    class Config:
        from_attributes = True


class PrinterDetailOut(PrinterBase):
    id: int
    logs: List[PrinterLogOut] = []

    class Config:
        from_attributes = True
