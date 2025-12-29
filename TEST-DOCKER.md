# Docker Build Test Instructions

The crawler has been configured to test on **utdallas.edu**. 

## Quick Test

Run the test script:

```bash
./test-docker.sh
```

Or manually:

### 1. Build the Docker Image

```bash
docker build -t college-crawler .
```

This will:
- Install all system dependencies for Playwright
- Install Python packages
- Install Playwright Chromium browser
- Copy the crawler code

**Expected build time:** 5-10 minutes (first time)

### 2. Run the Container

```bash
docker run --rm -v $(pwd)/data:/app/data college-crawler
```

**On Windows PowerShell:**
```powershell
docker run --rm -v ${PWD}/data:/app/data college-crawler
```

### 3. Verify Output

After running, check the `data/` directory for:
- `utdallas_edu.md` - Clean markdown output
- `utdallas_edu.json` - Structured JSON with metadata and links

## Expected Output

You should see:
```
Starting College Data AI Webcrawler...
Crawling 1 websites...

[INIT].... → Crawl4AI 0.7.8 
Crawling: https://www.utdallas.edu
[FETCH]... ↓ https://www.utdallas.edu
| ✓ | ⏱: 0.88s 
[SCRAPE].. ◆ https://www.utdallas.edu
| ✓ | ⏱: 0.02s 
[COMPLETE] ● https://www.utdallas.edu
| ✓ | ⏱: 0.90s 
  ✓ Saved markdown to data/utdallas_edu.md
  ✓ Saved JSON to data/utdallas_edu.json

✓ Crawling complete! Check the 'data' directory for results.
```

## Troubleshooting

### Docker not found
Make sure Docker Desktop is installed and running:
- macOS: Install from [docker.com](https://www.docker.com/products/docker-desktop)
- Linux: Install Docker Engine
- Windows: Install Docker Desktop

### Build fails
- Check internet connection (needs to download packages)
- Ensure Docker has enough disk space (~2GB)
- Try: `docker system prune` to free up space

### Permission errors
On Linux, you may need to add your user to the docker group:
```bash
sudo usermod -aG docker $USER
```

### Playwright errors in container
The Dockerfile includes all necessary system dependencies. If issues persist, check the Dockerfile system packages list.

## Test Results

✅ Local test completed successfully
- Crawled: https://www.utdallas.edu
- Generated: utdallas_edu.md and utdallas_edu.json
- Ready for Docker build test

