# Gunakan base image Python 3.10 slim yang ringan dan stabil
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Set working directory
WORKDIR /app

# Install system dependencies yang dibutuhkan untuk kompilasi psycopg2 & packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code backend
COPY backend/ .

# Buat direktori uploads jika belum ada
RUN mkdir -p uploads

# Hugging Face Spaces secara default mengekspos port 7860
EXPOSE 7860

# Jalankan FastAPI uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
