FROM python:3.11-slim

WORKDIR /app

# build-essential + gcc needed for prophet's dependencies; libpq-dev for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
EXPOSE 8501

# Default command runs the API; docker-compose overrides this for the dashboard service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
