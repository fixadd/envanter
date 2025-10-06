## Çalıştırma (Yerel)s

```bash
python -m venv .venv && source .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env # düzenleyin
uvicorn app:app --reload --port 5000
```
