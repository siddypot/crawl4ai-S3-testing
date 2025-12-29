#!/bin/bash
# Test script for Docker build and run with utdallas.edu

set -e

echo "Building Docker image..."
docker build -t college-crawler .

echo ""
echo "Running crawler on utdallas.edu..."
docker run --rm -v $(pwd)/data:/app/data college-crawler

echo ""
echo "✓ Test complete! Check the data/ directory for utdallas_edu.md and utdallas_edu.json"

