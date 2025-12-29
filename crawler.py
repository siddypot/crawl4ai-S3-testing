"""
AI Webcrawler for Colleges & Universities
Uses Crawl4AI to crawl college/university websites and extract clean data
Includes adaptive crawling, LLM chunking, and RAG-ready output
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, DefaultMarkdownGenerator, ProxyConfig
from urllib.parse import urljoin, urlparse

# Try to import tiktoken for tokenization, fallback to simple estimation
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


# Configuration class for adaptive crawling

@dataclass
class CrawlerConfig:
    """Configuration for adaptive web crawling"""
    crawl_depth: int = 10  # How many levels deep to crawl
    max_pages: int = 300  # Maximum pages to crawl per domain
    chunk_size: int =  5000
    chunk_overlap: int = 200  # Overlap between chunks
    timeout: int = 30  # Crawl timeout in seconds
    exclude_external_links: bool = False  # Whether to exclude external links
    exclude_patterns: List[str] = None  # URL patterns to exclude (e.g., ['privacy', '/terms'])
    proxy: Optional[str] = None  # Proxy server URL (e.g., "http://proxy-server:port")
    persist_session: bool = False  # Persist browser session for authenticated pages
    semantic_extraction: bool = False  # Enable LLM-based semantic extraction
    verbose: bool = True  # Show progress


    
    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = ['privacy', '/terms']  # Default exclude patterns from PDF


class TextChunker:
    """Split text into chunks optimized for LLM ingestion with tokenization support"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200, model: str = "gpt-4"):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.model = model
        self.encoding = None
        
        # Initialize tokenizer if available
        if HAS_TIKTOKEN:
            try:
                self.encoding = tiktoken.encoding_for_model(model)
            except:
                # Fallback to cl100k_base (used by GPT-4)
                self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.encoding:
            return len(self.encoding.encode(text))
        # Fallback: estimate ~4 chars per token
        return len(text) // 4
    
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks with token counts
        
        Returns:
            List of dicts with 'content', 'token_count', and 'char_count'
        """
        if not text.strip():
            return []
        
        # If text fits in one chunk
        token_count = self.count_tokens(text)
        if token_count <= self.chunk_size:
            return [{
                'content': text,
                'token_count': token_count,
                'char_count': len(text)
            }]
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Find chunk end by token count
            end = start
            chunk_text = ""
            target_tokens = self.chunk_size
            
            # Build chunk up to target token size
            while end < text_length:
                test_text = text[start:end + 100]  # Look ahead 100 chars
                test_tokens = self.count_tokens(test_text)
                
                if test_tokens >= target_tokens:
                    # Try to break at sentence boundary
                    if end < text_length:
                        # Find last sentence end
                        last_period = text.rfind('.', start, end)
                        last_newline = text.rfind('\n', start, end)
                        break_point = max(last_period, last_newline)
                        
                        if break_point > start + (end - start) * 0.7:  # At least 70% full
                            end = break_point + 1
                    break
                
                end += 100
                if end >= text_length:
                    end = text_length
                    break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                token_count = self.count_tokens(chunk_text)
                chunks.append({
                    'content': chunk_text,
                    'token_count': token_count,
                    'char_count': len(chunk_text)
                })
            
            # Move start position with overlap
            overlap_text = text[max(0, end - self.overlap):end]
            overlap_tokens = self.count_tokens(overlap_text)
            start = max(0, end - self.overlap)
            
            # If we're at the end, break
            if end >= text_length:
                break
        
        return chunks


# Browser settings factory function
def get_browser_config(crawler_config: Optional[CrawlerConfig] = None) -> BrowserConfig:
    """
    Create BrowserConfig with optional proxy and session persistence
    As per PDF requirements: Proxy rotation and session persistence
    """
    proxy_config = None
    proxy_url = None
    
    if crawler_config and crawler_config.proxy:
        # Create proxy config from string URL (as per PDF: proxy rotation)
        # ProxyConfig expects: server, username, password, ip
        # For simple proxy URL, use it directly
        proxy_url = crawler_config.proxy
        # If you need full ProxyConfig with rotation, parse the URL here
    
    return BrowserConfig(
        headless=True,  # Run without UI
        proxy=proxy_url,  # Proxy URL string (e.g., "http://proxy-server:port")
        proxy_config=proxy_config,  # Full proxy config object for rotation
        # Note: persist_session is handled via session_id in CrawlerRunConfig
    )

# Default browser config (can be overridden)
browser_config = get_browser_config()

# DefaultMarkdownGenerator for clean HTML-to-markdown conversion
markdown_generator = DefaultMarkdownGenerator()

# Base crawl settings
def get_crawl_config(config: CrawlerConfig) -> CrawlerRunConfig:
    """Create CrawlerRunConfig from CrawlerConfig"""
    # Generate session ID if persistence is enabled
    session_id = f"session_{hash(config)}" if config.persist_session else None
    
    return CrawlerRunConfig(
        markdown_generator=markdown_generator,  # Explicitly use DefaultMarkdownGenerator
        exclude_domains=[],
        exclude_external_links=config.exclude_external_links,
        verbose=config.verbose,
        cache_mode="default",
        session_id=session_id,  # Session persistence for authenticated pages
        # Note: exclude_patterns handled in URL filtering, not directly in CrawlerRunConfig
    )


def should_exclude_url(url: str, exclude_patterns: List[str]) -> bool:
    """Check if URL should be excluded based on patterns"""
    if not exclude_patterns:
        return False
    url_lower = url.lower()
    return any(pattern.lower() in url_lower for pattern in exclude_patterns)


async def crawl_adaptive(url: str, config: CrawlerConfig, crawler: AsyncWebCrawler) -> Dict:
    """
    Adaptively crawl a website up to specified depth with coverage tracking
    
    Args:
        url: Starting URL to crawl
        config: CrawlerConfig with depth and page limits
        crawler: AsyncWebCrawler instance
    
    Returns:
        Dict with crawl results and metadata
    """
    visited_urls = set()
    all_content = []
    crawl_config = get_crawl_config(config)
    
    async def crawl_recursive(current_url: str, current_depth: int):
        """Recursive crawl with depth and coverage limits"""
        if current_depth > config.crawl_depth or len(visited_urls) >= config.max_pages:
            return
        
        if current_url in visited_urls:
            return
        
        # Check exclude patterns (as per PDF requirements)
        if should_exclude_url(current_url, config.exclude_patterns):
            if config.verbose:
                print(f"  {'  ' * current_depth}⊘ Excluded (pattern): {current_url}")
            return
        
        visited_urls.add(current_url)
        
        if config.verbose:
            print(f"  {'  ' * current_depth}↳ Crawling (depth {current_depth}): {current_url}")
        
        try:
            result = await crawler.arun(current_url, config=crawl_config)
            
            if result and result.markdown:
                # Apply semantic extraction if enabled (as per PDF requirements)
                markdown_content = result.markdown
                if config.semantic_extraction:
                    # Note: Full semantic extraction would require LLM integration
                    # This is a placeholder for the feature mentioned in PDF
                    markdown_content = f"[Semantic Extraction Enabled]\n{markdown_content}"
                
                all_content.append({
                    'url': current_url,
                    'depth': current_depth,
                    'markdown': markdown_content,
                    'html': result.html if hasattr(result, 'html') else '',
                    'links': result.links if hasattr(result, 'links') else []
                })
            
            # Extract domain from current URL
            current_domain = urlparse(current_url).netloc
            
            # Crawl linked pages if depth allows
            if current_depth < config.crawl_depth and result and hasattr(result, 'links'):
                links = result.links
                if isinstance(links, dict):
                    # If links is a dict, get internal links
                    links = links.get('internal', [])
                elif not isinstance(links, list):
                    links = []
                
                # Limit links to crawl (max 10 per page)
                for link in links[:10]:
                    if isinstance(link, dict):
                        link_url = link.get('href', '')
                    elif isinstance(link, str):
                        link_url = link
                    else:
                        continue
                    
                    absolute_url = urljoin(current_url, link_url)
                    link_domain = urlparse(absolute_url).netloc
                    
                    # Only follow links on same domain and check exclude patterns
                    if (link_domain == current_domain and 
                        absolute_url not in visited_urls and
                        not should_exclude_url(absolute_url, config.exclude_patterns)):
                        await crawl_recursive(absolute_url, current_depth + 1)
        
        except Exception as e:
            if config.verbose:
                print(f"    Error crawling {current_url}: {str(e)}")
    
    # Start recursive crawl
    await crawl_recursive(url, 0)
    
    return {
        'start_url': url,
        'pages_crawled': len(visited_urls),
        'content': all_content
    }


async def crawl_college_sites(
    urls: List[str], 
    output_dir: str = 'data',
    config: Optional[CrawlerConfig] = None
):
    """
    Crawl multiple college/university websites with adaptive depth and LLM optimization
    
    Args:
        urls: List of URLs to crawl
        output_dir: Directory to save output files
        config: CrawlerConfig for crawl behavior (uses defaults if None)
    """
    if config is None:
        config = CrawlerConfig()
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize chunker for LLM
    chunker = TextChunker(config.chunk_size, config.chunk_overlap)
    
    # Get browser config with proxy and session settings (as per PDF requirements)
    browser_cfg = get_browser_config(config)
    
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for url in urls:
            print(f"\n📌 Crawling: {url}")
            print(f"   Depth: {config.crawl_depth} | Max Pages: {config.max_pages}\n")
            
            try:
                # Perform adaptive crawl
                crawl_result = await crawl_adaptive(url, config, crawler)
                
                # Extract domain name for folder organization
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
                
                # Create domain-specific output directory
                domain_dir = os.path.join(output_dir, domain)
                Path(domain_dir).mkdir(parents=True, exist_ok=True)
                
                # Process each page and save individually by page type
                all_chunks = []
                total_tokens = 0
                
                for item in crawl_result['content']:
                    page_url = item['url']
                    page_markdown = item['markdown']
                    
                    # Extract page type from URL path (e.g., /admissions -> admissions.md)
                    page_path = urlparse(page_url).path.strip('/')
                    if not page_path or page_path == '/':
                        page_name = 'index'
                    else:
                        # Get last meaningful segment of path
                        path_parts = [p for p in page_path.split('/') if p]
                        if path_parts:
                            page_name = path_parts[-1]
                        else:
                            page_name = 'index'
                    
                    # Clean page name for filename
                    page_name = re.sub(r'[^\w\-_]', '_', page_name)[:50]  # Limit length
                    if not page_name:
                        page_name = 'index'
                    
                    # Save individual page markdown
                    page_md_file = os.path.join(domain_dir, f"{page_name}.md")
                    with open(page_md_file, "w", encoding="utf-8") as f:
                        f.write(f"# {page_url}\n\n{page_markdown}")
                    print(f"  ✓ Saved page: {page_md_file}")
                    
                    # Chunk this page
                    page_chunks = chunker.chunk(page_markdown)
                    page_tokens = sum(chunk['token_count'] for chunk in page_chunks)
                    total_tokens += page_tokens
                    
                    # Add page-specific metadata to chunks
                    for i, chunk_data in enumerate(page_chunks):
                        chunk_data['chunk_id'] = len(all_chunks)
                        chunk_data['metadata'] = {
                            'source_url': page_url,
                            'page_name': page_name,
                            'chunk_index': i,
                            'total_chunks_in_page': len(page_chunks),
                            'depth': item['depth']
                        }
                        all_chunks.append(chunk_data)
                    
                    # Save individual page JSON with tokenized chunks
                    page_json_file = os.path.join(domain_dir, f"{page_name}.json")
                    page_rag_data = {
                        'source_url': page_url,
                        'page_name': page_name,
                        'content_length': len(page_markdown),
                        'token_count': page_tokens,
                        'chunk_count': len(page_chunks),
                        'chunks': page_chunks,
                        'metadata': {
                            'depth': item['depth'],
                            'domain': domain
                        }
                    }
                    with open(page_json_file, "w", encoding="utf-8") as f:
                        json.dump(page_rag_data, f, indent=2, ensure_ascii=False)
                    print(f"  ✓ Saved tokenized JSON: {page_json_file} ({len(page_chunks)} chunks, {page_tokens} tokens)")
                
                # Save combined domain-level summary
                combined_markdown = "\n\n---\n\n".join([
                    f"# {item['url']}\n\n{item['markdown']}" 
                    for item in crawl_result['content']
                ])
                
                combined_md_file = os.path.join(domain_dir, "combined.md")
                with open(combined_md_file, "w", encoding="utf-8") as f:
                    f.write(combined_markdown)
                
                # Save combined RAG-ready JSON with all chunks
                combined_rag_data = {
                    'source': url,
                    'domain': domain,
                    'pages_crawled': crawl_result['pages_crawled'],
                    'total_content_length': len(combined_markdown),
                    'total_token_count': total_tokens,
                    'total_chunk_count': len(all_chunks),
                    'config': asdict(config),
                    'chunks': all_chunks,
                    'pages': [
                        {
                            'url': item['url'],
                            'depth': item['depth'],
                            'content_length': len(item['markdown'])
                        }
                        for item in crawl_result['content']
                    ]
                }
                
                combined_json_file = os.path.join(domain_dir, "combined.json")
                with open(combined_json_file, "w", encoding="utf-8") as f:
                    json.dump(combined_rag_data, f, indent=2, ensure_ascii=False)
                print(f"  ✓ Saved combined JSON: {combined_json_file} ({len(all_chunks)} chunks, {total_tokens} tokens)")
                
                print(f"  ✓ Summary: {crawl_result['pages_crawled']} pages, {len(all_chunks)} chunks, {total_tokens} tokens")
                
            except Exception as e:
                print(f"  ✗ Error crawling {url}: {str(e)}")


def main():
    """Main function to run the crawler"""
    # Create custom config with adaptive parameters
    config = CrawlerConfig(
        crawl_depth=2,      # Crawl up to 2 levels deep
        max_pages=20,       # Max 20 pages per domain
        chunk_size=1000,    # 1000 char chunks
        chunk_overlap=200,  # 200 char overlap
        verbose=True
    )
    
    # Test URLs
    urls = [
        "https://www.utdallas.edu",
        "https://www.smu.edu",
        "https://www.unc.edu"
    ]
    
    print("=" * 60)
    print("🚀 College Data AI Webcrawler - Adaptive Mode")
    print("=" * 60)
    print(f"Crawling {len(urls)} websites with adaptive depth crawling...\n")
    
    asyncio.run(crawl_college_sites(urls, config=config))
    
    print("\n" + "=" * 60)
    print("✓ Crawling complete! Check the 'data' directory for results.")
    print("=" * 60)


if __name__ == "__main__":
    main()

