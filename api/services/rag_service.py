import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from api.config import settings
import logging
import os
import hashlib

logger = logging.getLogger(__name__)

class RAGService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.persist_directory = os.path.join(settings.EVIDENCE_DIR, "rag_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB at {self.persist_directory}")
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Use a lightweight model for embeddings
            logger.info("Loading embedding model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            self._initialized = False

    def _get_collection_name(self, case_id: str) -> str:
        # ChromaDB collection names must be alphanumeric, underscores, hyphens
        # Ensure case_id is safe
        safe_id = case_id.replace("-", "_").replace(":", "_")
        # Ensure it starts with a letter if needed, but case_id usually does
        return f"case_{safe_id}"

    def add_document(self, case_id: str, text: str, metadata: dict = None):
        if not self._initialized:
            return False
            
        try:
            collection_name = self._get_collection_name(case_id)
            collection = self.client.get_or_create_collection(name=collection_name)
            
            # Generate embedding
            embedding = self.embedding_model.encode(text).tolist()
            
            # Generate ID
            doc_id = f"{case_id}_{hashlib.md5(text.encode()).hexdigest()}"
            
            # Add to collection
            collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            logger.error(f"Error adding document to RAG: {e}")
            return False

    def query(self, case_id: str, query_text: str, n_results: int = 5):
        if not self._initialized:
            return []
            
        try:
            collection_name = self._get_collection_name(case_id)
            try:
                collection = self.client.get_collection(name=collection_name)
            except ValueError:
                logger.warning(f"Collection {collection_name} not found")
                return []

            query_embedding = self.embedding_model.encode(query_text).tolist()
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            return results
        except Exception as e:
            logger.error(f"Error querying RAG: {e}")
            return []

    def get_context(self, case_id: str, query_text: str) -> str:
        results = self.query(case_id, query_text)
        if not results or not results['documents']:
            return ""
        
        # Flatten documents list (results['documents'] is a list of lists)
        documents = results['documents'][0]
        return "\n\n".join(documents)

rag_service = RAGService()
