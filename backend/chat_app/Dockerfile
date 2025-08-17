# Base image
FROM python:3.11-slim

ARG INSTALL_TORCH="false"
ARG TORCH_VERSION="2.2.2"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build-time dependencies for ffmpeg + rnnoise + general tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    wget \
    curl \
    pkg-config \
    autoconf \
    automake \
    libtool \
    cmake \
    yasm \
    nasm \
    libsndfile1 \
    libsndfile1-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install libsndfile runtime (already installed above)
# Build and install rnnoise (required for ffmpeg arnndn filter)
WORKDIR /tmp
RUN git clone https://git.xiph.org/rnnoise.git rnnoise && \
    cd rnnoise && \
    ./autogen.sh && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    ldconfig

# Build ffmpeg from source with librnnoise enabled so arnndn filter is available
WORKDIR /tmp
RUN git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg && \
    cd ffmpeg && \
    ./configure \
      --prefix=/usr/local \
      --pkg-config-flags="--static" \
      --extra-cflags="-I/usr/local/include" \
      --extra-ldflags="-L/usr/local/lib" \
      --extra-libs="-lpthread -lm" \
      --enable-gpl \
      --enable-nonfree \
      --enable-librnnoise \
      --disable-doc \
      --disable-debug && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd /tmp && rm -rf ffmpeg

# Create app directory
WORKDIR /app

# Copy python dependency manifest and install python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
# Optional: install CPU PyTorch if requested at build time
RUN if [ "$INSTALL_TORCH" = "true" ]; then \
      pip install --no-cache-dir torch==${TORCH_VERSION}+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html ; \
    fi
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the repository
COPY . /app

# Create non-root user
RUN useradd -m appuser || true
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8765

# Default command — run uvicorn using the factory create_app
CMD ["uvicorn", "backend.chat_app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]