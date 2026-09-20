# Build the React/Vite frontend in an isolated Node stage.
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# Run the Flask application and its pre-built frontend bundle.
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000

WORKDIR /app

# Tesseract is required by the OCR service; the remaining shared libraries are
# required by OpenCV and RapidOCR's ONNX runtime.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY serve_production.py ./
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# The application writes uploads and generated reports. SQLite remains a local fallback.
RUN mkdir -p backend/database backend/uploads backend/reports \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python", "serve_production.py"]
