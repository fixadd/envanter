## Çalıştırma (Yerel)

```bash
python -m venv .venv && source .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env # düzenleyin, üretimde SESSION_HTTPS_ONLY=true yapın
uvicorn app:app --reload --port 5000
```
