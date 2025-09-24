from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class InventoryBase(BaseModel):
    no: str
    fabrika: Optional[str] = None
    departman: Optional[str] = None
    donanim_tipi: Optional[str] = None
    bilgisayar_adi: Optional[str] = None
    marka: Optional[str] = None
    model: Optional[str] = None
    seri_no: Optional[str] = None
    sorumlu_personel: Optional[str] = None
    bagli_makina_no: Optional[str] = None
    ifs_no: Optional[str] = None
    tarih: Optional[str] = None
    islem_yapan: Optional[str] = None
    notlar: Optional[str] = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    fabrika: Optional[str] = None
    departman: Optional[str] = None
    donanim_tipi: Optional[str] = None
    bilgisayar_adi: Optional[str] = None
    marka: Optional[str] = None
    model: Optional[str] = None
    seri_no: Optional[str] = None
    sorumlu_personel: Optional[str] = None
    bagli_makina_no: Optional[str] = None
    ifs_no: Optional[str] = None
    tarih: Optional[str] = None
    islem_yapan: Optional[str] = None
    notlar: Optional[str] = None


class InventoryLogOut(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None
    changed_by: str
    changed_at: datetime

    class Config:
        from_attributes = True


class InventoryListOut(BaseModel):
    id: int
    no: str
    fabrika: str | None
    departman: str | None
    donanim_tipi: str | None
    bilgisayar_adi: str | None
    sorumlu_personel: str | None

    class Config:
        from_attributes = True


class InventoryDetailOut(InventoryBase):
    id: int
    logs: List[InventoryLogOut] = []

    class Config:
        from_attributes = True
