ACTION_TR = {
  "assign": "Atama",
  "edit": "Düzenleme",
  "scrap": "Hurdaya Ayırma",
  "girdi": "Girdi",
  "cikti": "Çıktı",
}

def tr_action(key: str) -> str:
    return ACTION_TR.get(key, key)

def humanize_log(row) -> str:
    # row: {tarih, islem, islem_yapan, aciklama}
    try:
        dt = row.tarih.strftime("%d.%m.%Y %H:%M")
    except Exception:
        dt = str(row.tarih)
    return f"{dt} - {tr_action(getattr(row,'islem', ''))} - {getattr(row,'islem_yapan','')} - {getattr(row,'aciklama','')}"
