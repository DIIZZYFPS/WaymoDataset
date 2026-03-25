# --- STAGE 1: Build ---
FROM ubuntu:22.04 AS builder

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build tools, Bazelisk, OpenCV, and Redis deps
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    python3 \
    libopencv-dev \
    cmake \
    git \
    libhiredis-dev \
    && rm -rf /var/lib/apt/lists/*

# Build and install redis-plus-plus from source (v1.3.10)
RUN git clone https://github.com/sewenew/redis-plus-plus.git /tmp/redis-plus-plus && \
    cd /tmp/redis-plus-plus && \
    git checkout 1.3.10 && \
    mkdir build && cd build && \
    cmake .. && \
    make -j$(nproc) && \
    make install

# Install Bazelisk
RUN curl -L https://github.com/bazelbuild/bazelisk/releases/download/v1.17.0/bazelisk-linux-amd64 -o /usr/local/bin/bazel \
    && chmod +x /usr/local/bin/bazel

ENV USE_BAZEL_VERSION=6.1.1

WORKDIR /app

# Proto files are now bundled locally in src/waymo_open_dataset/protos/
# (self-contained, no deep dependency chain from upstream repo)

# Copy build config and source
COPY WORKSPACE .
COPY .bazelrc .
RUN echo "Force rebuild OpenCV fix"
COPY src/ src/

# Build binary
RUN bazel build -c opt //src:waymo_processor

# --- STAGE 2: Runtime ---
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
ENV LD_LIBRARY_PATH=/usr/local/lib

# Fix #4: Remove 'd' suffix from OpenCV package names (Ubuntu ships release builds)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libopencv-core4.5 \
    libopencv-imgcodecs4.5 \
    libopencv-stitching4.5 \
    libopencv-imgproc4.5 \
    libhiredis0.14 \
    && rm -rf /var/lib/apt/lists/*

# Copy redis++ shared lib from builder
COPY --from=builder /usr/local/lib/libredis++* /usr/local/lib/
COPY --from=builder /usr/local/include/sw /usr/local/include/sw

# Copy binary from builder
COPY --from=builder /app/bazel-bin/src/waymo_processor .

ENTRYPOINT ["./waymo_processor"]