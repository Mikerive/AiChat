FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for audio processing and optional native builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    git \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip and helpers
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies (uses the repository requirements)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the TTS finetune app into the image
COPY backend/tts_finetune_app /app/backend/tts_finetune_app

# Create persistent directories for training artifacts and checkpoints
RUN mkdir -p /app/backend/tts_finetune_app/training_data /app/backend/tts_finetune_app/checkpoints

# Expose persistent volumes so host can mount training data and checkpoints
VOLUME ["/app/backend/tts_finetune_app/training_data", "/app/backend/tts_finetune_app/checkpoints"]

WORKDIR /app

# Default command - drop to a shell. To run ingestion use:
# docker run --rm -it -v $(pwd)/backend/tts_finetune_app/training_data:/app/backend/tts_finetune_app/training_data \
#    <image> python backend/tts_finetune_app/scripts/ingest.py /path/to/input.mp3
CMD ["bash"]