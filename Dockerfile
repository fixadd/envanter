FROM python:3.11-slim
WORKDIR /app

# requirements varsa yükle
COPY requirements.txt .
RUN test -f requirements.txt && pip install --no-cache-dir -r requirements.txt || echo "no requirements.txt"

COPY . .
EXPOSE 5000
CMD ["python", "app.py"]