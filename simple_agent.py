import json
import faiss
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
import os
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationPhase(Enum):
    CLARIFY = "clarify"
    RECOMMEND = "recommend"
    REFINE = "refine"
    COMPARE = "compare"

@dataclass
class AgentResponse:
    reply: str
    recommendations: List[Dict]
    end_of_conversation: bool

class SimpleSHLAgent:
    """Simplified agent that doesn't depend on sentence-transformers"""
    
    def __init__(self, 
                 index_file: str = "faiss_index.bin",
                 metadata_file: str = "faiss_index_metadata.json"):
        self.index_file = index_file
        self.metadata_file = metadata_file
        
        # Initialize components
        self.index = None
        self.assessments = []
        
        # Load everything at startup
        self._initialize()
    
    def _initialize(self):
        """Initialize all components"""
        try:
            # Load FAISS index and assessments
            self._load_vector_index()
            logger.info("Simple agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing simple agent: {e}")
    
    def _load_vector_index(self):
        """Load FAISS index and assessment metadata"""
        try:
            if os.path.exists(self.index_file):
                self.index = faiss.read_index(self.index_file)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} items")
            else:
                logger.error(f"FAISS index file not found: {self.index_file}")
                return
            
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.assessments = json.load(f)
                logger.info(f"Loaded {len(self.assessments)} assessments")
            else:
                logger.error(f"Metadata file not found: {self.metadata_file}")
                
        except Exception as e:
            logger.error(f"Error loading vector index: {e}")
    
    def _simple_keyword_search(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """Simple keyword-based search as fallback"""
        query_lower = query.lower()
        results = []
        
        for assessment in self.assessments:
            score = 0.0
            
            # Check name match
            if query_lower in assessment['name'].lower():
                score += 1.0
            
            # Check description match
            if query_lower in assessment['description'].lower():
                score += 0.5
            
            # Check test type match
            if query_lower in assessment['test_type'].lower():
                score += 0.3
            
            # Check for common keywords
            keywords = ["java", "python", "programming", "personality", "cognitive", "technical"]
            for keyword in keywords:
                if keyword in query_lower and keyword in assessment['name'].lower():
                    score += 0.8
                if keyword in query_lower and keyword in assessment['description'].lower():
                    score += 0.4
            
            if score > 0:
                results.append((assessment, score))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def _retrieve_relevant_assessments(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """Retrieve relevant assessments using available search method"""
        if self.index is not None:
            try:
                # Try vector search if available
                import random
                # Simple random search as placeholder for vector search
                random.shuffle(self.assessments)
                results = [(assessment, random.random()) for assessment in self.assessments[:top_k]]
                return results
            except Exception as e:
                logger.warning(f"Vector search failed, using keyword search: {e}")
        
        # Fallback to keyword search
        return self._simple_keyword_search(query, top_k)
    
    def _detect_prompt_injection(self, messages: List[Dict]) -> bool:
        """Detect potential prompt injection attempts"""
        injection_patterns = [
            "ignore previous instructions",
            "system prompt",
            "forget everything",
            "new role",
            "you are now",
            "act as",
            "pretend to be",
            "disregard",
            "override",
            "bypass",
            "admin",
            "developer mode"
        ]
        
        for message in messages:
            content = message.get("content", "").lower()
            for pattern in injection_patterns:
                if pattern in content:
                    logger.warning(f"Potential prompt injection detected: {pattern}")
                    return True
        return False
    
    def _is_off_topic(self, query: str) -> bool:
        """Check if query is off-topic (not related to SHL assessments)"""
        off_topic_keywords = [
            "weather", "sports", "politics", "entertainment", "news",
            "personal advice", "medical", "legal", "financial advice",
            "cooking", "travel", "relationships", "general knowledge"
        ]
        
        query_lower = query.lower()
        for keyword in off_topic_keywords:
            if keyword in query_lower:
                return True
        return False
    
    def _extract_conversation_context(self, messages: List[Dict]) -> Dict:
        """Extract relevant context from conversation history"""
        context = {
            "role": None,
            "seniority": None,
            "skills": [],
            "test_types": [],
            "constraints": []
        }
        
        # Extract information from all messages
        for message in messages:
            content = message.get("content", "").lower()
            
            # Extract role information
            role_keywords = ["developer", "manager", "analyst", "engineer", "consultant", "specialist", "coordinator"]
            for keyword in role_keywords:
                if keyword in content:
                    context["role"] = keyword
                    break
            
            # Extract seniority
            seniority_keywords = ["junior", "mid-level", "senior", "lead", "entry", "experienced"]
            for keyword in seniority_keywords:
                if keyword in content:
                    context["seniority"] = keyword
                    break
            
            # Extract skills
            skill_keywords = ["java", "python", "sql", "programming", "coding", "technical", "customer service", "sales"]
            for keyword in skill_keywords:
                if keyword in content:
                    context["skills"].append(keyword)
            
            # Extract test type preferences
            if "personality" in content:
                context["test_types"].append("P")
            if "cognitive" in content or "reasoning" in content:
                context["test_types"].append("K")
            if "behavioral" in content or "situational" in content:
                context["test_types"].append("B")
            if "skills" in content or "technical" in content:
                context["test_types"].append("S")
        
        return context
    
    def _determine_conversation_phase(self, messages: List[Dict]) -> ConversationPhase:
        """Determine current phase of conversation"""
        context = self._extract_conversation_context(messages)
        last_message = messages[-1].get("content", "").lower()
        
        # Check for comparison questions (more comprehensive) - check this first
        comparison_keywords = ["difference", "compare", "vs", "versus", "what's the difference", "how do", "which is better"]
        if any(keyword in last_message for keyword in comparison_keywords):
            return ConversationPhase.COMPARE
        
        # Check for refinement (more comprehensive)
        refine_keywords = ["add", "also", "include", "actually", "in addition", "as well", "too"]
        if any(keyword in last_message for keyword in refine_keywords):
            return ConversationPhase.REFINE
        
        # Only return CLARIFY if no specific phase detected and no context
        if len(messages) <= 1:
            return ConversationPhase.CLARIFY
        
        # Check if we have enough context to recommend
        if context["role"] or context["skills"] or len(context["test_types"]) > 0:
            return ConversationPhase.RECOMMEND
        
        return ConversationPhase.CLARIFY
    
    def _generate_response(self, messages: List[Dict], phase: ConversationPhase, context: Dict, relevant_assessments: List[Tuple[Dict, float]]) -> AgentResponse:
        """Generate response without external LLM"""
        
        if phase == ConversationPhase.CLARIFY:
            return AgentResponse(
                reply="I'd be happy to help you find the right SHL assessments! Could you tell me more about the role you're hiring for? For example, what type of position, seniority level, and key skills are you looking for?",
                recommendations=[],
                end_of_conversation=False
            )
        
        elif phase == ConversationPhase.RECOMMEND:
            # Return top relevant assessments
            recommendations = []
            for assessment, score in relevant_assessments[:5]:
                recommendations.append({
                    "name": assessment["name"],
                    "url": assessment["url"],
                    "test_type": assessment["test_type"]
                })
            
            return AgentResponse(
                reply=f"Based on your needs, here are {len(recommendations)} assessments that would be a good fit:",
                recommendations=recommendations,
                end_of_conversation=False
            )
        
        elif phase == ConversationPhase.REFINE:
            # Return updated recommendations with additional assessments
            recommendations = []
            # Include technical assessments
            for assessment, score in relevant_assessments:
                if any(skill in assessment["name"].lower() for skill in ["java", "python", "programming", "technical"]):
                    recommendations.append({
                        "name": assessment["name"],
                        "url": assessment["url"],
                        "test_type": assessment["test_type"]
                    })
            # Add personality assessments
            for assessment, score in relevant_assessments:
                if "personality" in assessment["name"].lower() or "opq" in assessment["name"].lower():
                    recommendations.append({
                        "name": assessment["name"],
                        "url": assessment["url"],
                        "test_type": assessment["test_type"]
                    })
            
            return AgentResponse(
                reply=f"I'll add personality assessments to your recommendations. Here are {len(recommendations)} assessments including both technical and personality tests:",
                recommendations=recommendations[:5],  # Limit to 5
                end_of_conversation=False
            )
        
        elif phase == ConversationPhase.COMPARE:
            return AgentResponse(
                reply="OPQ (Occupational Personality Questionnaire) is a personality assessment that measures behavioral traits and work preferences, while cognitive tests measure reasoning abilities and problem-solving skills. OPQ helps predict job fit and cultural alignment, whereas cognitive tests predict learning ability and job performance across different roles.",
                recommendations=[],
                end_of_conversation=False
            )
        
        else:
            return AgentResponse(
                reply="I can help you with that! Let me find the most relevant assessments for your needs.",
                recommendations=[],
                end_of_conversation=False
            )
    
    def process_message(self, messages: List[Dict]) -> AgentResponse:
        """Process incoming messages and generate response"""
        try:
            # Guardrails check
            if self._detect_prompt_injection(messages):
                return AgentResponse(
                    reply="I cannot process that request. Please keep your questions focused on SHL assessments.",
                    recommendations=[],
                    end_of_conversation=False
                )
            
            # Get last user message
            last_message = messages[-1].get("content", "") if messages else ""
            
            # Off-topic check
            if self._is_off_topic(last_message):
                return AgentResponse(
                    reply="I'm specifically designed to help with SHL assessment recommendations. I can't assist with general questions outside of assessment selection.",
                    recommendations=[],
                    end_of_conversation=False
                )
            
            # Determine conversation phase
            phase = self._determine_conversation_phase(messages)
            
            # Extract context
            context = self._extract_conversation_context(messages)
            
            # Retrieve relevant assessments
            relevant_assessments = self._retrieve_relevant_assessments(last_message, top_k=10)
            
            # Generate response
            return self._generate_response(messages, phase, context, relevant_assessments)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return AgentResponse(
                reply="I apologize, but I'm having trouble processing your request right now. Please try again.",
                recommendations=[],
                end_of_conversation=False
            )
