import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, catalog_file: str = "catalog.json", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize vector store for semantic retrieval
        Args:
            catalog_file: Path to the catalog JSON file
            model_name: Name of the sentence transformer model
        """
        self.catalog_file = catalog_file
        self.model_name = model_name
        self.model = None
        self.index = None
        self.assessments = []
        self.embeddings = None
        
    def load_catalog(self) -> List[Dict]:
        """Load assessment catalog from JSON file"""
        try:
            with open(self.catalog_file, 'r', encoding='utf-8') as f:
                self.assessments = json.load(f)
            logger.info(f"Loaded {len(self.assessments)} assessments from catalog")
            return self.assessments
        except Exception as e:
            logger.error(f"Error loading catalog: {e}")
            return []
    
    def create_embeddings(self) -> np.ndarray:
        """Create embeddings for all assessments"""
        if not self.assessments:
            self.load_catalog()
        
        # Combine name and description for better semantic matching
        texts = []
        for assessment in self.assessments:
            text = f"{assessment['name']} {assessment['description']} {assessment['test_type']}"
            # Add additional context for better matching
            if assessment.get('remote_testing'):
                text += " remote online"
            if assessment.get('adaptive_irt'):
                text += " adaptive computerized"
            texts.append(text)
        
        logger.info("Creating embeddings...")
        self.model = SentenceTransformer(self.model_name)
        self.embeddings = self.model.encode(texts, show_progress_bar=True)
        
        logger.info(f"Created embeddings with shape: {self.embeddings.shape}")
        return self.embeddings
    
    def build_index(self):
        """Build FAISS index for fast similarity search"""
        if self.embeddings is None:
            self.create_embeddings()
        
        # Create FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings)
        
        logger.info(f"Built FAISS index with {self.index.ntotal} items")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """
        Search for assessments similar to the query
        Args:
            query: Search query string
            top_k: Number of results to return
        Returns:
            List of (assessment, score) tuples
        """
        if self.index is None:
            self.build_index()
        
        # Create query embedding
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, min(top_k, len(self.assessments)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.assessments):  # Valid index
                assessment = self.assessments[idx].copy()
                results.append((assessment, float(score)))
        
        return results
    
    def get_assessment_by_name(self, name: str) -> Dict:
        """Get assessment by exact name match"""
        for assessment in self.assessments:
            if assessment['name'].lower() == name.lower():
                return assessment
        return None
    
    def get_all_assessments(self) -> List[Dict]:
        """Get all assessments"""
        return self.assessments.copy()
    
    def save_index(self, index_file: str = "faiss_index.bin"):
        """Save FAISS index to file"""
        if self.index is not None:
            faiss.write_index(self.index, index_file)
            logger.info(f"Saved index to {index_file}")
    
    def load_index(self, index_file: str = "faiss_index.bin"):
        """Load FAISS index from file"""
        if os.path.exists(index_file):
            self.index = faiss.read_index(index_file)
            logger.info(f"Loaded index from {index_file}")
            return True
        return False

# Test the vector store
if __name__ == "__main__":
    # Initialize and test
    vs = VectorStore()
    
    # Load catalog and build index
    assessments = vs.load_catalog()
    if assessments:
        vs.build_index()
        
        # Test searches
        test_queries = [
            "Java developer programming skills",
            "personality assessment for leadership",
            "cognitive ability numerical reasoning",
            "customer service communication skills"
        ]
        
        print("\n=== Vector Store Test Results ===")
        for query in test_queries:
            print(f"\nQuery: {query}")
            results = vs.search(query, top_k=3)
            for assessment, score in results:
                print(f"  - {assessment['name']} (score: {score:.3f})")
                print(f"    {assessment['description'][:100]}...")
    else:
        print("No assessments found in catalog")
