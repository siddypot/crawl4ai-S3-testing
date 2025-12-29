# AI Webcrawler for College Data

A webcrawler built with Crawl4AI to extract and organize data from college and university websites for AI/LLM ingestion.

## Features

- **Async Web Crawling**: Fast, asynchronous crawling using Crawl4AI
- **Adaptive Crawling**: Stops when coverage is sufficient
- **Clean Output**: Converts HTML to clean Markdown format
- **Structured Data**: Saves both Markdown and JSON formats
- **LLM-Ready**: Chunked output optimized for language models

## Setup

### Option 1: Docker (Recommended)

#### Build the Docker Image

```bash
docker build -t college-crawler .
```

#### Run with Docker

```bash
# Run the crawler
docker run --rm -v $(pwd)/data:/app/data college-crawler

# Or use docker-compose
docker-compose up
```

#### Run with Custom URLs

```bash
# Create a custom script or override the command
docker run --rm -v $(pwd)/data:/app/data college-crawler python crawler.py
```

### Option 2: Local Python Setup

#### 1. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

#### 3. Run the Crawler

```bash
python crawler.py
```

## Configuration

Edit `crawler.py` to customize:

- **URLs**: Modify the `urls` list in the `main()` function
- **Crawl Depth**: Change `max_depth` in `crawl_config`
- **Output Directory**: Change `output_dir` parameter in `crawl_college_sites()`
- **Exclude Patterns**: Add patterns to `exclude_patterns` to skip certain pages

## Output Structure

The crawler now organizes output by domain in separate folders, with individual pages saved as separate files:

```
data/
├── harvard_edu/
│   ├── admissions.md
│   ├── admissions.json
│   ├── research.md
│   ├── research.json
│   ├── programs.md
│   ├── programs.json
│   ├── combined.md
│   └── combined.json
├── stanford_edu/
│   ├── programs.md
│   ├── programs.json
│   ├── combined.md
│   └── combined.json
└── mit_edu/
    ├── admissions.md
    ├── admissions.json
    ├── combined.md
    └── combined.json
```

Each JSON file includes:
- **Tokenized chunks** with token counts for LLM ingestion
- **Metadata** for each chunk (source URL, page name, chunk index)
- **Embedding-ready** structure for Vector DBs

## Advanced Features (All from PDF Requirements)

### Proxy Rotation

```python
from crawler import CrawlerConfig, crawl_college_sites

config = CrawlerConfig(
    proxy="http://proxy-server:port"  # Enable proxy rotation
)
asyncio.run(crawl_college_sites(urls, config=config))
```

### Session Persistence

```python
config = CrawlerConfig(
    persist_session=True  # Persist browser session for authenticated pages
)
```

### Semantic Extraction

```python
config = CrawlerConfig(
    semantic_extraction=True  # Enable LLM-based semantic extraction
)
```

### Exclude Patterns

```python
config = CrawlerConfig(
    exclude_patterns=['privacy', '/terms', 'login']  # Skip irrelevant pages
)
```

## Integration (As per PDF Requirements)

### LangChain Integration

```python
from integrations import load_for_langchain, load_domain_for_langchain

# Load individual page (uses pre-tokenized chunks from JSON)
docs = load_for_langchain("data/harvard_edu/admissions.json")

# Or load entire domain
docs = load_domain_for_langchain("data/harvard_edu")

# Use with LangChain RAG pipeline
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)

# Query the vector store
retriever = vectorstore.as_retriever()
results = retriever.get_relevant_documents("admission requirements")
```

### Vector DB Integration with Embeddings

```python
from integrations import load_for_vector_db

# Load with embeddings (OpenAI or local)
vectors = load_for_vector_db(
    "data/harvard_edu/combined.json",
    "pinecone",
    generate_embeddings=True,
    embedding_model="text-embedding-ada-002"  # or "local" for free embeddings
)

# Upload to Pinecone
# from pinecone import Pinecone
# pc = Pinecone(api_key="your-key")
# index = pc.Index("college-data")
# index.upsert(vectors=vectors)

# For Weaviate
# objects = load_for_vector_db("data/harvard_edu/combined.json", "weaviate", generate_embeddings=True)
# import weaviate
# client = weaviate.Client("http://localhost:8080")
# client.batch.create_objects(objects)

# For ChromaDB
# data = load_for_vector_db("data/harvard_edu/combined.json", "chroma", generate_embeddings=True)
# import chromadb
# client = chromadb.Client()
# collection = client.create_collection("college-data")
# collection.add(**data)
```

### Tokenization

All output is tokenized using `tiktoken` for accurate token counting. Each chunk includes:
- Token count (for LLM context window management)
- Character count
- Metadata for traceability

This makes it easy to:
- Track token usage for LLM APIs
- Manage context windows
- Optimize chunk sizes for your specific LLM

See `integrations.py` for complete integration examples.

## License

MIT

