import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import logging
import os
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self, catalog_file: str = "catalog.json", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding manager
        Args:
            catalog_file: Path to the catalog JSON file
            model_name: Name of the sentence transformer model
        """
        self.catalog_file = catalog_file
        self.model_name = model_name
        self.model = None
        self.assessments = []
        
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
    
    def create_text_for_embedding(self, assessment: Dict) -> str:
        """Create comprehensive text for embedding from assessment data"""
        text_parts = []
        
        # Add name and description
        if assessment.get('name'):
            text_parts.append(assessment['name'])
        if assessment.get('description'):
            text_parts.append(assessment['description'])
        
        # Add test type with semantic meaning
        test_type = assessment.get('test_type', '')
        if test_type == 'P':
            text_parts.append("personality assessment behavioral traits")
        elif test_type == 'K':
            text_parts.append("cognitive ability reasoning knowledge test")
        elif test_type == 'B':
            text_parts.append("behavioral assessment situational judgment")
        elif test_type == 'S':
            text_parts.append("skills assessment technical programming")
        
        # Add features
        if assessment.get('remote_testing'):
            text_parts.append("remote online testing")
        if assessment.get('adaptive_irt'):
            text_parts.append("adaptive computerized testing")
        
        return ' '.join(text_parts)
    
    def generate_embeddings(self) -> np.ndarray:
        """Generate embeddings for all assessments"""
        if not self.assessments:
            self.load_catalog()
        
        # Create texts for embedding
        texts = [self.create_text_for_embedding(assessment) for assessment in self.assessments]
        
        logger.info(f"Loading sentence transformer model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        logger.info("Generating embeddings...")
        embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=8)
        
        logger.info(f"Generated embeddings with shape: {embeddings.shape}")
        return embeddings
    
    def save_faiss_index(self, embeddings: np.ndarray, index_file: str = "faiss_index.bin"):
        """Save embeddings as FAISS index to disk"""
        try:
            # Normalize embeddings for cosine similarity
            normalized_embeddings = embeddings.copy()
            faiss.normalize_L2(normalized_embeddings)
            
            # Create FAISS index
            dimension = normalized_embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            index.add(normalized_embeddings)
            
            # Save index to disk
            faiss.write_index(index, index_file)
            
            # Also save assessment metadata
            metadata_file = index_file.replace('.bin', '_metadata.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.assessments, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved FAISS index with {index.ntotal} items to {index_file}")
            logger.info(f"Saved metadata to {metadata_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
            return False
    
    def load_faiss_index(self, index_file: str = "faiss_index.bin") -> tuple:
        """Load FAISS index and metadata from disk"""
        try:
            # Load index
            index = faiss.read_index(index_file)
            
            # Load metadata
            metadata_file = index_file.replace('.bin', '_metadata.json')
            with open(metadata_file, 'r', encoding='utf-8') as f:
                assessments = json.load(f)
            
            logger.info(f"Loaded FAISS index with {index.ntotal} items from {index_file}")
            logger.info(f"Loaded {len(assessments)} assessments from metadata")
            
            return index, assessments
            
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            return None, None
    
    def test_search(self, index, query: str, top_k: int = 5):
        """Test semantic search with the loaded index"""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
        
        # Create query embedding
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = index.search(query_embedding, top_k)
        
        # Load assessments for results
        _, assessments = self.load_faiss_index()
        
        print(f"\nQuery: {query}")
        print("Top results:")
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(assessments):
                assessment = assessments[idx]
                print(f"  - {assessment['name']} (score: {score:.3f})")
                print(f"    {assessment['description'][:80]}...")

def main():
    """Main function to generate and save embeddings"""
    print("=== SHL Assessment Embeddings Generator ===")
    
    # Initialize embedding manager
    embed_manager = EmbeddingManager()
    
    # Load catalog
    assessments = embed_manager.load_catalog()
    if not assessments:
        print("No assessments found. Exiting.")
        return
    
    print(f"Processing {len(assessments)} assessments...")
    
    # Generate embeddings
    embeddings = embed_manager.generate_embeddings()
    
    # Save FAISS index
    success = embed_manager.save_faiss_index(embeddings)
    
    if success:
        print("\n✅ Embeddings generated and saved successfully!")
        
        # Test the saved index
        print("\n=== Testing Semantic Search ===")
        index, _ = embed_manager.load_faiss_index()
        
        test_queries = [
            "Java developer programming test",
            "personality assessment for hiring",
            "cognitive reasoning ability",
            "customer service skills"
        ]
        
        for query in test_queries:
            embed_manager.test_search(index, query, top_k=3)
            print()
    else:
        print("❌ Failed to save embeddings")

if __name__ == "__main__":
    main()
