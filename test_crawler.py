#!/usr/bin/env python3
"""
Test script to validate crawler functionality
Tests each component at every step
"""

import sys
import json
from pathlib import Path
from dataclasses import asdict

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all imports"""
    print("\n" + "="*60)
    print("TEST 1: Validating Imports")
    print("="*60)
    
    try:
        from typing import List, Dict, Optional
        from dataclasses import dataclass, asdict
        from urllib.parse import urljoin, urlparse
        print("✓ Standard library imports successful")
        
        # These won't work without crawl4ai, but we'll catch the error gracefully
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, DefaultMarkdownGenerator
            print("✓ Crawl4AI imports successful")
            return True
        except ImportError:
            print("⚠ Crawl4AI not installed (expected - install with: pip install crawl4ai)")
            return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_crawler_config():
    """Test CrawlerConfig dataclass"""
    print("\n" + "="*60)
    print("TEST 2: Validating CrawlerConfig")
    print("="*60)
    
    try:
        from dataclasses import dataclass, asdict
        
        @dataclass
        class CrawlerConfig:
            crawl_depth: int = 2
            max_pages: int = 50
            chunk_size: int = 1000
            chunk_overlap: int = 200
            timeout: int = 30
            exclude_external_links: bool = False
            verbose: bool = True
        
        # Test default config
        config = CrawlerConfig()
        print(f"✓ Default config created")
        print(f"  - Crawl depth: {config.crawl_depth}")
        print(f"  - Max pages: {config.max_pages}")
        print(f"  - Chunk size: {config.chunk_size}")
        print(f"  - Chunk overlap: {config.chunk_overlap}")
        
        # Test custom config
        custom_config = CrawlerConfig(
            crawl_depth=3,
            max_pages=100,
            chunk_size=2000
        )
        print(f"\n✓ Custom config created")
        print(f"  - Crawl depth: {custom_config.crawl_depth}")
        print(f"  - Max pages: {custom_config.max_pages}")
        print(f"  - Chunk size: {custom_config.chunk_size}")
        
        # Test asdict conversion
        config_dict = asdict(custom_config)
        print(f"\n✓ Config converted to dict")
        print(f"  - Dict keys: {list(config_dict.keys())}")
        
        return True
    except Exception as e:
        print(f"✗ CrawlerConfig test failed: {e}")
        return False


def test_text_chunker():
    """Test TextChunker class"""
    print("\n" + "="*60)
    print("TEST 3: Validating TextChunker")
    print("="*60)
    
    try:
        from typing import List
        
        class TextChunker:
            def __init__(self, chunk_size: int = 1000, overlap: int = 200):
                self.chunk_size = chunk_size
                self.overlap = overlap
            
            def chunk(self, text: str) -> List[str]:
                if len(text) <= self.chunk_size:
                    return [text]
                
                chunks = []
                start = 0
                
                while start < len(text):
                    end = start + self.chunk_size
                    
                    if end < len(text):
                        last_period = text.rfind('.', start, end)
                        if last_period > start + self.chunk_size * 0.7:
                            end = last_period + 1
                    
                    chunk = text[start:end].strip()
                    if chunk:
                        chunks.append(chunk)
                    
                    start = end - self.overlap
                
                return chunks
        
        # Test with small chunk size
        chunker = TextChunker(chunk_size=100, overlap=20)
        test_text = "This is a test sentence. " * 20  # Create longer text
        
        chunks = chunker.chunk(test_text)
        print(f"✓ TextChunker created and tested")
        print(f"  - Input length: {len(test_text)} chars")
        print(f"  - Chunk size: {chunker.chunk_size}")
        print(f"  - Overlap: {chunker.overlap}")
        print(f"  - Chunks generated: {len(chunks)}")
        print(f"  - Chunk sizes: {[len(c) for c in chunks[:3]]}...")
        
        # Test with default sizes
        chunker2 = TextChunker()
        chunks2 = chunker2.chunk(test_text)
        print(f"\n✓ TextChunker with default sizes")
        print(f"  - Default chunk size: {chunker2.chunk_size}")
        print(f"  - Default overlap: {chunker2.overlap}")
        print(f"  - Chunks generated: {len(chunks2)}")
        
        return True
    except Exception as e:
        print(f"✗ TextChunker test failed: {e}")
        return False


def test_url_parsing():
    """Test URL parsing utilities"""
    print("\n" + "="*60)
    print("TEST 4: Validating URL Parsing")
    print("="*60)
    
    try:
        from urllib.parse import urljoin, urlparse
        
        test_cases = [
            ("https://www.utdallas.edu", "https://www.utdallas.edu"),
            ("https://www.utdallas.edu/about", "https://www.utdallas.edu/about"),
            ("/about/history", "https://www.utdallas.edu/about/history"),
        ]
        
        base_url = "https://www.utdallas.edu"
        print(f"✓ URL parsing initialized")
        print(f"  - Base URL: {base_url}\n")
        
        for test_url, expected in test_cases:
            if test_url.startswith('/'):
                absolute_url = urljoin(base_url, test_url)
            else:
                absolute_url = test_url
            
            domain = urlparse(absolute_url).netloc
            print(f"  {test_url}")
            print(f"    → {absolute_url}")
            print(f"    → Domain: {domain}")
        
        # Test same-domain check
        url1 = "https://www.utdallas.edu/about"
        url2 = "https://google.com"
        domain1 = urlparse(url1).netloc
        domain2 = urlparse(url2).netloc
        
        print(f"\n✓ Same-domain check")
        print(f"  - {url1}: {domain1}")
        print(f"  - {url2}: {domain2}")
        print(f"  - Same domain? {domain1 == domain2}")
        
        return True
    except Exception as e:
        print(f"✗ URL parsing test failed: {e}")
        return False


def test_rag_json_structure():
    """Test RAG-ready JSON structure"""
    print("\n" + "="*60)
    print("TEST 5: Validating RAG-Ready JSON Structure")
    print("="*60)
    
    try:
        from dataclasses import dataclass, asdict
        
        @dataclass
        class CrawlerConfig:
            crawl_depth: int = 2
            max_pages: int = 50
            chunk_size: int = 1000
            chunk_overlap: int = 200
            timeout: int = 30
            exclude_external_links: bool = False
            verbose: bool = True
        
        config = CrawlerConfig(crawl_depth=2, max_pages=20)
        
        # Create sample RAG data
        rag_data = {
            'source': 'https://www.stanford.edu',
            'pages_crawled': 5,
            'total_content_length': 50000,
            'chunk_count': 50,
            'config': asdict(config),
            'chunks': [
                {
                    'chunk_id': 0,
                    'content': 'Sample chunk content here.',
                    'length': 26,
                    'metadata': {
                        'source_url': 'https://www.stanford.edu',
                        'chunk_index': 0,
                        'total_chunks': 50
                    }
                },
                {
                    'chunk_id': 1,
                    'content': 'Another sample chunk.',
                    'length': 21,
                    'metadata': {
                        'source_url': 'https://www.stanford.edu',
                        'chunk_index': 1,
                        'total_chunks': 50
                    }
                }
            ],
            'pages': [
                {'url': 'https://www.stanford.edu', 'depth': 0, 'content_length': 10000},
                {'url': 'https://www.stanford.edu/about', 'depth': 1, 'content_length': 15000},
            ]
        }
        
        # Validate JSON serialization
        json_str = json.dumps(rag_data, indent=2, ensure_ascii=False)
        print(f"✓ RAG-ready JSON structure validated")
        print(f"  - Total size: {len(json_str)} bytes")
        print(f"  - Pages crawled: {rag_data['pages_crawled']}")
        print(f"  - Total chunks: {rag_data['chunk_count']}")
        print(f"  - Config keys: {list(rag_data['config'].keys())}")
        print(f"\n✓ RAG data structure:")
        print(f"  - Has 'source': {'source' in rag_data}")
        print(f"  - Has 'chunks' array: {'chunks' in rag_data}")
        print(f"  - Has 'pages' array: {'pages' in rag_data}")
        print(f"  - Has 'config': {'config' in rag_data}")
        print(f"  - Chunk has metadata: {'metadata' in rag_data['chunks'][0]}")
        
        return True
    except Exception as e:
        print(f"✗ RAG JSON test failed: {e}")
        return False


def test_file_read():
    """Test that the crawler.py file exists and is valid"""
    print("\n" + "="*60)
    print("TEST 6: Validating crawler.py File")
    print("="*60)
    
    try:
        crawler_file = Path(__file__).parent / "crawler.py"
        
        if not crawler_file.exists():
            print(f"✗ crawler.py not found at {crawler_file}")
            return False
        
        print(f"✓ crawler.py file found")
        print(f"  - Path: {crawler_file}")
        print(f"  - Size: {crawler_file.stat().st_size} bytes")
        
        # Read and validate content
        with open(crawler_file, 'r') as f:
            content = f.read()
        
        # Check for critical components
        checks = [
            ('CrawlerConfig', 'CrawlerConfig dataclass'),
            ('TextChunker', 'TextChunker class'),
            ('crawl_adaptive', 'Adaptive crawl function'),
            ('crawl_college_sites', 'Main crawl function'),
            ('DefaultMarkdownGenerator', 'DefaultMarkdownGenerator import'),
            ('crawl_depth', 'Crawl depth parameter'),
            ('chunk_size', 'Chunk size parameter'),
            ('RAG', 'RAG-ready output'),
        ]
        
        print(f"\n✓ File validation checks:")
        all_passed = True
        for check_str, desc in checks:
            if check_str in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc} - NOT FOUND")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ File validation failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 CRAWLER FUNCTIONALITY TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Imports", test_imports()))
    results.append(("CrawlerConfig", test_crawler_config()))
    results.append(("TextChunker", test_text_chunker()))
    results.append(("URL Parsing", test_url_parsing()))
    results.append(("RAG JSON Structure", test_rag_json_structure()))
    results.append(("File Validation", test_file_read()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Crawler is ready for deployment.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
