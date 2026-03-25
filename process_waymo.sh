#!/bin/bash

set -e  # Exit on error

# --- Configuration ---
GSUTIL_CMD="gsutil"
GCS_BUCKET="gs://waymo_open_dataset_end_to_end_camera_v_1_0_0"
REDIS_URL="redis://redis-server:6379"
GCS_IMAGE_BUCKET="e2e-processed-images"
RESULTS_DIR="./waymo_dataset/results"
CONTAINER_RESULTS_DIR="/waymo_dataset/results"

# --- Create directories ---
mkdir -p "$RESULTS_DIR"

# --- Build once ---
echo "Building Docker image..."
docker build -t waymodataset-waymo-e2e-loader .
echo "✓ Build complete"

# --- Main Loop ---
echo "Fetching list of files from GCS..."
file_list=$("$GSUTIL_CMD" ls "$GCS_BUCKET"/*.tfrecord* | head -n 5 | tr -d '\r')

echo "DEBUG: Found files:"
echo "$file_list"

for gcs_file_path in $file_list; do
    filename=$(basename "$gcs_file_path")

    echo "----------------------------------------"
    echo "Streaming Processing: $filename"
    echo "----------------------------------------"

    echo "Running analysis (C++ Core)..."
    docker-compose run --rm \
        waymo-e2e-loader "$gcs_file_path" "$REDIS_URL" "$GCS_IMAGE_BUCKET"

    echo "Done with $filename."
done

echo "----------------------------------------"
echo "✓ All files processed."
echo "✓ Results saved to: $RESULTS_DIR"
echo "----------------------------------------"