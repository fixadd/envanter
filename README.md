## Çalıştırma (Yerel)

```bash
python -m venv .venv && source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env # düzenleyin, üretimde SESSION_HTTPS_ONLY=true yapın
uvicorn app:app --reload --port 5000
```

## Varsayılan yönetici hesabı ve parolayı sıfırlama

Uygulama her açılışta veritabanında bir yönetici hesabı olup olmadığını
kontrol eder. Hesap yoksa, ortam değişkenlerinden alınan kullanıcı adı ve
parola ile yeni bir kullanıcı oluşturulur. Parola önce `DEFAULT_ADMIN_PASSWORD`
değişkeninden okunur; bu değişken tanımlı değilse geliştirme için
`DEFAULT_ADMIN_DEV_PASSWORD` (varsayılan değeri `admin123`) kullanılır. 【F:app/main.py†L100-L135】【F:app/main.py†L240-L266】

Kurulumdan sonra parolanın değiştirilmiş olması ihtimaline karşı, mevcut
hesabın parolasını komut satırından kolayca sıfırlayabilirsiniz:

```bash
python -m scripts.reset_admin_password --username admin --password yeni_sifre
```

Komut, kullanıcı adını büyük/küçük harfe duyarsız olarak arar ve yeni parolayı
güvenli bir biçimde (bcrypt) tekrar yazar. Parolayı komut satırında vermek
istemiyorsanız `DEFAULT_ADMIN_PASSWORD` ortam değişkenini tanımlayıp komutu
parametresiz olarak da çalıştırabilirsiniz. 【F:scripts/reset_admin_password.py†L1-L118】

## Güvenlik Notları

- `.env` dosyasındaki `SESSION_SECRET` değerini **üretimde mutlaka** rastgele, en az 32 karakterlik bir anahtar ile değiştirin.
Değer ayarlanmamışsa geliştirme ve test sırasında geçici bir anahtar otomatik olarak üretilir.
- Tarayıcı oturum çerezlerinin sadece HTTPS üzerinden gönderilmesi için `SESSION_HTTPS_ONLY=true` ayarını etkinleştirin ve uygulamayı TLS terminasyonu yapan bir ters proxy arkasında yayınlayın.
