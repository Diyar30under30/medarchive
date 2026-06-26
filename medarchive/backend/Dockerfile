# MedArchive backend — Python 3.11 with Tesseract (rus+kaz+eng) and the
# embedding model baked in, so the image runs fully offline at judging time.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models \
    TRANSFORMERS_OFFLINE=0

# System deps: Tesseract + RU/KK/EN language data, build basics for some wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-rus \
        tesseract-ocr-kaz \
        tesseract-ocr-eng \
        libgl1 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download the multilingual embedding model into the image (offline-first).
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" \
    || echo 'WARN: model pre-download failed; will download on first run'

COPY . .

EXPOSE 8000
# entrypoint runs migrations + reference load + server (see scripts/entrypoint.sh)
CMD ["bash", "scripts/entrypoint.sh"]
