# Use an official lightweight Python image
FROM python:3.11-slim

# Install system-level dependencies for PDFs and Tesseract OCR
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python requirement layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly install the necessary OCR companion packages
RUN pip install --no-cache-dir pytesseract Pillow

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
