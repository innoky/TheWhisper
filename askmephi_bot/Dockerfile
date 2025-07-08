FROM python:3.13.3-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Проверка перед сборкой статики

CMD ["python3", "main.py"]