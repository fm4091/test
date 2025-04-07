FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for PDF processing
RUN apt-get update && apt-get install -y \
    build-essential \
    default-jre \
    poppler-utils \
    libpq-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn jinja2 python-multipart

# Install spaCy models
RUN python -m spacy download en_core_web_lg

# Create necessary directories
RUN mkdir -p data/input data/output static/uploads

# Copy source code
COPY . .

# Make scripts executable
RUN chmod +x setup.sh run_demo.sh

# Expose the port that FastAPI runs on
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data

# Run the FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 