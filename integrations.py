"""
Integration helpers for RAG pipelines and Vector DBs
As specified in the PDF requirements: LangChain and Vector DB integration
Includes embeddings support for Vector DBs and tokenization
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import os


def load_for_langchain(markdown_file: str, use_existing_chunks: bool = True):
    """
    Load crawled markdown file for LangChain RAG pipeline
    As per PDF requirements: LangChain integration example
    
    Args:
        markdown_file: Path to markdown file or JSON file with chunks
        use_existing_chunks: If True and JSON exists, use pre-chunked data
    
    Returns:
        List of LangChain Document objects
    """
    try:
        from langchain.schema import Document
        from langchain.document_loaders import TextLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        # Try to load from JSON if it exists (has tokenized chunks)
        if use_existing_chunks:
            json_file = markdown_file.replace('.md', '.json')
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert chunks to LangChain Documents
                documents = []
                for chunk in data.get('chunks', []):
                    content = chunk.get('content', '')
                    metadata = chunk.get('metadata', {})
                    metadata.update({
                        'source': data.get('source_url', markdown_file),
                        'token_count': chunk.get('token_count', 0),
                        'char_count': chunk.get('char_count', 0)
                    })
                    documents.append(Document(page_content=content, metadata=metadata))
                
                if documents:
                    return documents
        
        # Fallback to loading markdown directly
        loader = TextLoader(markdown_file, encoding="utf-8")
        docs = loader.load()
        
        # Split into chunks for RAG
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)
        
        return splits
    except ImportError as e:
        print(f"LangChain not installed. Install with: pip install langchain langchain-community")
        print(f"Error: {e}")
        return None
    except Exception as e:
        print(f"Error loading for LangChain: {e}")
        return None


def load_domain_for_langchain(domain_dir: str):
    """
    Load all pages from a domain directory for LangChain
    
    Args:
        domain_dir: Path to domain directory (e.g., 'data/harvard')
    
    Returns:
        List of LangChain Document objects from all pages
    """
    domain_path = Path(domain_dir)
    all_docs = []
    
    # Load from combined.json if available
    combined_json = domain_path / "combined.json"
    if combined_json.exists():
        docs = load_for_langchain(str(combined_json))
        if docs:
            return docs
    
    # Otherwise load all individual page JSONs
    for json_file in domain_path.glob("*.json"):
        if json_file.name != "combined.json":
            docs = load_for_langchain(str(json_file))
            if docs:
                all_docs.extend(docs)
    
    return all_docs


def load_for_vector_db(json_file: str, vector_db_type: str = "pinecone", generate_embeddings: bool = False, embedding_model: str = "text-embedding-ada-002"):
    """
    Load crawled JSON file for Vector DB ingestion with optional embeddings
    As per PDF requirements: Vector DB integration (Pinecone, Weaviate)
    
    Args:
        json_file: Path to JSON file with chunks
        vector_db_type: "pinecone", "weaviate", or "chroma"
        generate_embeddings: If True, generate embeddings using OpenAI or local model
        embedding_model: Model to use for embeddings (OpenAI model name or "local")
    
    Returns:
        Prepared data ready for vector DB ingestion with embeddings if requested
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Generate embeddings if requested
    if generate_embeddings:
        data = add_embeddings_to_data(data, embedding_model)
    
    if vector_db_type.lower() == "pinecone":
        return prepare_for_pinecone(data)
    elif vector_db_type.lower() == "weaviate":
        return prepare_for_weaviate(data)
    elif vector_db_type.lower() == "chroma":
        return prepare_for_chroma(data)
    else:
        raise ValueError(f"Unknown vector DB type: {vector_db_type}. Supported: pinecone, weaviate, chroma")


def add_embeddings_to_data(data: Dict, embedding_model: str = "text-embedding-ada-002") -> Dict:
    """
    Add embeddings to chunk data
    
    Args:
        data: JSON data with chunks
        embedding_model: Model name or "local" for local embeddings
    
    Returns:
        Data dict with embeddings added to chunks
    """
    try:
        if embedding_model == "local":
            # Use sentence-transformers for local embeddings
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            texts = [chunk['content'] for chunk in data.get('chunks', [])]
            embeddings = model.encode(texts, show_progress_bar=True)
            
            for i, chunk in enumerate(data.get('chunks', [])):
                chunk['embedding'] = embeddings[i].tolist()
        else:
            # Use OpenAI embeddings
            try:
                import openai
                client = openai.OpenAI()
                
                texts = [chunk['content'] for chunk in data.get('chunks', [])]
                # OpenAI API accepts up to 2048 items per batch
                batch_size = 100
                all_embeddings = []
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    response = client.embeddings.create(
                        model=embedding_model,
                        input=batch
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                
                for i, chunk in enumerate(data.get('chunks', [])):
                    chunk['embedding'] = all_embeddings[i]
            except ImportError:
                print("OpenAI not installed. Install with: pip install openai")
                print("Falling back to local embeddings...")
                return add_embeddings_to_data(data, "local")
    except ImportError as e:
        print(f"Embedding libraries not available: {e}")
        print("Install with: pip install sentence-transformers openai")
        return data
    
    return data


def prepare_for_pinecone(data: Dict) -> List[Dict]:
    """Prepare chunks for Pinecone ingestion with embeddings"""
    vectors = []
    source = data.get('source', data.get('source_url', 'unknown'))
    
    for chunk in data.get('chunks', []):
        chunk_id = chunk.get('chunk_id', len(vectors))
        vector_data = {
            'id': f"{source}_{chunk_id}",
            'values': chunk.get('embedding', []),  # Use embeddings if available
            'metadata': {
                **chunk.get('metadata', {}),
                'source': source,
                'content': chunk.get('content', ''),
                'token_count': chunk.get('token_count', 0),
                'char_count': chunk.get('char_count', chunk.get('length', 0))
            }
        }
        
        # If no embeddings, Pinecone will need to generate them or use text
        if not vector_data['values']:
            # For Pinecone, you might want to store text and let it generate embeddings
            # Or use a different approach
            vector_data['metadata']['text'] = chunk.get('content', '')
        
        vectors.append(vector_data)
    return vectors


def prepare_for_weaviate(data: Dict) -> List[Dict]:
    """Prepare chunks for Weaviate ingestion with embeddings"""
    objects = []
    source = data.get('source', data.get('source_url', 'unknown'))
    
    for chunk in data.get('chunks', []):
        obj = {
            'class': 'CollegeContent',
            'properties': {
                'content': chunk.get('content', ''),
                'source_url': source,
                'chunk_index': chunk.get('chunk_id', 0),
                'token_count': chunk.get('token_count', 0),
                'char_count': chunk.get('char_count', chunk.get('length', 0)),
                **chunk.get('metadata', {})
            }
        }
        
        # Add embedding if available
        if 'embedding' in chunk:
            obj['vector'] = chunk['embedding']
        
        objects.append(obj)
    return objects


def prepare_for_chroma(data: Dict) -> List[Dict]:
    """Prepare chunks for ChromaDB ingestion"""
    documents = []
    metadatas = []
    ids = []
    embeddings = []
    source = data.get('source', data.get('source_url', 'unknown'))
    
    for chunk in data.get('chunks', []):
        chunk_id = chunk.get('chunk_id', len(documents))
        documents.append(chunk.get('content', ''))
        ids.append(f"{source}_{chunk_id}")
        metadatas.append({
            **chunk.get('metadata', {}),
            'source': source,
            'token_count': chunk.get('token_count', 0),
            'char_count': chunk.get('char_count', chunk.get('length', 0))
        })
        
        if 'embedding' in chunk:
            embeddings.append(chunk['embedding'])
    
    result = {
        'documents': documents,
        'metadatas': metadatas,
        'ids': ids
    }
    
    if embeddings:
        result['embeddings'] = embeddings
    
    return result


def example_langchain_usage():
    """Example: LangChain for RAG pipelines (from PDF)"""
    print("""
    # LangChain Integration Example
    from integrations import load_for_langchain, load_domain_for_langchain
    
    # Load from individual page
    docs = load_for_langchain("data/harvard/admissions.json")
    
    # Or load entire domain
    docs = load_domain_for_langchain("data/harvard")
    
    # Use with LangChain RAG
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings
    
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)
    
    # Query
    retriever = vectorstore.as_retriever()
    results = retriever.get_relevant_documents("admission requirements")
    """)


def example_vector_db_usage():
    """Example: Vector DB for embeddings (from PDF)"""
    print("""
    # Vector DB Integration Example (Pinecone with embeddings)
    from integrations import load_for_vector_db
    
    # Load and prepare data with embeddings
    vectors = load_for_vector_db(
        "data/harvard/combined.json", 
        "pinecone",
        generate_embeddings=True,
        embedding_model="text-embedding-ada-002"  # or "local" for free local embeddings
    )
    
    # Upload to Pinecone
    # import pinecone
    # from pinecone import Pinecone
    # pc = Pinecone(api_key="your-key")
    # index = pc.Index("college-data")
    # index.upsert(vectors=vectors)
    
    # Or for Weaviate
    # objects = load_for_vector_db("data/harvard/combined.json", "weaviate", generate_embeddings=True)
    # import weaviate
    # client = weaviate.Client("http://localhost:8080")
    # client.batch.create_objects(objects)
    
    # Or for ChromaDB
    # data = load_for_vector_db("data/harvard/combined.json", "chroma", generate_embeddings=True)
    # import chromadb
    # client = chromadb.Client()
    # collection = client.create_collection("college-data")
    # collection.add(**data)
    """)


if __name__ == "__main__":
    print("Integration helpers for RAG pipelines and Vector DBs")
    print("\nLangChain Example:")
    example_langchain_usage()
    print("\nVector DB Example:")
    example_vector_db_usage()

