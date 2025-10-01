FROM python:3.11-slim

# Ishchi papkani yaratamiz
WORKDIR /app

# Paketlarni o‘rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodlarni ko‘chiramiz
COPY . .

# Collectstatic bu yerda emas, docker-compose command ichida ishlatiladi

# Gunicorn ishga tushadi
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
