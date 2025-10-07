## Çalıştırma (Yerel)

```bash
python -m venv .venv && source .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env # düzenleyin, üretimde SESSION_HTTPS_ONLY=true yapın
uvicorn app:app --reload --port 5000
```

Varsayılan olarak ilk açılışta `admin` kullanıcı adı ve `admin123` parolasıyla bir yönetici hesabı oluşturulur. Üretimde `.env` dosyanıza `DEFAULT_ADMIN_PASSWORD` değerini güçlü bir parola olacak şekilde eklemeyi unutmayın. Mevcut bir veritabanındaki `admin` hesabı için farklı veya eski formatlı bir parola varsa uygulama başlarken:

- `.env` içinde `DEFAULT_ADMIN_PASSWORD` tanımladıysanız parolayı bu değere otomatik olarak günceller,
- Geliştirme modunda (ortam değişkeni tanımlı değilken) sadece tanınmayan/parolasız eski kayıtları `admin123` ile sıfırlar.

Bu sayede eski kurulumlardan aktarılan veritabanlarında dahi oturum açma sorunları giderilir; kalıcı bir parola belirlemek istiyorsanız `.env` içindeki `DEFAULT_ADMIN_PASSWORD` değerini güncelleyin.

## Güvenlik Notları

- `.env` dosyasındaki `SESSION_SECRET` değerini **üretimde mutlaka** rastgele, en az 32 karakterlik bir anahtar ile değiştirin. Değer ayarlanmamışsa geliştirme ve test sırasında geçici bir anahtar otomatik olarak üretilir.
- Tarayıcı oturum çerezlerinin sadece HTTPS üzerinden gönderilmesi için `SESSION_HTTPS_ONLY=true` ayarını etkinleştirin ve uygulamayı TLS terminasyonu yapan bir ters proxy arkasında yayınlayın.
