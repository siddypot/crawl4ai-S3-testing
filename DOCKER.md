# Docker Setup Guide

This guide explains how to build and run the College Data AI Webcrawler using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier management)

## Quick Start

### Build the Image

```bash
docker build -t college-crawler .
```

### Run the Container

```bash
# Basic run
docker run --rm -v $(pwd)/data:/app/data college-crawler

# On Windows PowerShell
docker run --rm -v ${PWD}/data:/app/data college-crawler
```

### Using Docker Compose

```bash
# Build and run
docker-compose up

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

## Customization

### Run with Custom URLs

You can modify `crawler.py` before building, or create a custom entrypoint:

```bash
# Build with custom script
docker build -t college-crawler .

# Or override command at runtime
docker run --rm -v $(pwd)/data:/app/data college-crawler python -c "
from crawler import crawl_college_sites
import asyncio
asyncio.run(crawl_college_sites(['https://example.com']))
"
```

### Environment Variables

You can pass environment variables:

```bash
docker run --rm \
  -v $(pwd)/data:/app/data \
  -e PYTHONUNBUFFERED=1 \
  college-crawler
```

## Output Files

The crawled data will be saved in the `./data` directory on your host machine, which is mounted as a volume in the container.

## Troubleshooting

### Playwright Issues

If you encounter Playwright-related errors, ensure the Docker image includes all system dependencies. The Dockerfile already includes all necessary libraries.

### Permission Issues

If you encounter permission issues with the data directory:

```bash
# Fix permissions
sudo chown -R $USER:$USER data/
```

### Build Cache

To rebuild without cache:

```bash
docker build --no-cache -t college-crawler .
```

## Image Size

The Docker image includes:
- Python 3.11
- All Python dependencies
- Playwright and Chromium browser
- System libraries for browser support

Expected image size: ~1.5-2GB

