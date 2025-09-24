## Çalıştırma (Yerel)

```bash
python -m venv .venv && source .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env # düzenleyin, üretimde SESSION_HTTPS_ONLY=true yapın
uvicorn app:app --reload --port 5000
```

## Güvenlik Notları

* `.env` dosyasındaki `SESSION_SECRET` değerini **üretimde mutlaka** rastgele, en az 32 karakterlik bir anahtar ile değiştirin. Değer ayarlanmamışsa geliştirme ve test sırasında geçici bir anahtar otomatik olarak üretilir.
* Tarayıcı oturum çerezlerinin sadece HTTPS üzerinden gönderilmesi için `SESSION_HTTPS_ONLY=true` ayarını etkinleştirin ve uygulamayı TLS terminasyonu yapan bir ters proxy arkasında yayınlayın.
