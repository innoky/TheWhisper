FROM python:3.13.3-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Проверка перед сборкой статики
RUN mkdir -p /app/staticfiles && \
    chmod -R 755 /app/staticfiles && \
    python3 manage.py collectstatic --noinput

CMD ["gunicorn", "thewhisper.wsgi:application", "--bind", "0.0.0.0:8000"]