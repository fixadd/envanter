FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .           # app.py bu repo kökünde olmalı
CMD ["python", "app.py"]

