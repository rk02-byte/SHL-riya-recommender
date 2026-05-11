from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging
import time
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SHL Conversational Assessment Recommender",
    description="AI-powered agent for recommending SHL assessments through natural dialogue",
    version="1.0.0"
)

# Global assessments data
assessments = []

# Pydantic models for request/response schemas
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str

class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation]
    end_of_conversation: bool

class HealthResponse(BaseModel):
    status: str

@app.on_event("startup")
async def startup_event():
    """Load assessments at startup"""
    global assessments
    logger.info("Starting SHL Assessment Recommender API...")
    
    try:
        # Load assessments from catalog
        if os.path.exists("catalog.json"):
            with open("catalog.json", "r", encoding="utf-8") as f:
                assessments = json.load(f)
            logger.info(f"Loaded {len(assessments)} assessments from catalog")
        else:
            # Fallback assessments if catalog doesn't exist
            assessments = [
                {
                    "name": "Occupational Personality Questionnaire (OPQ)",
                    "url": "https://www.shl.com/products/assessments/personality-assessment/shl-occupational-personality-questionnaire-opq/",
                    "description": "The world's most used personality assessment for workplace selection and development. Measures 32 specific personality traits relevant to occupational performance.",
                    "test_type": "P",
                    "remote_testing": True,
                    "adaptive_irt": False
                },
                {
                    "name": "Java 8 Programming Test",
                    "url": "https://www.shl.com/products/assessments/skills-and-simulations/technical-skills/java-8-programming/",
                    "description": "Assesses Java programming knowledge and skills including object-oriented programming, collections, and Java 8 features.",
                    "test_type": "S",
                    "remote_testing": True,
                    "adaptive_irt": False
                },
                {
                    "name": "General Ability Tests (GAT)",
                    "url": "https://www.shl.com/products/assessments/cognitive-assessments/general-ability-tests/",
                    "description": "Comprehensive cognitive ability assessment covering verbal, numerical, and logical reasoning skills. Predicts job performance across multiple roles.",
                    "test_type": "K",
                    "remote_testing": True,
                    "adaptive_irt": True
                }
            ]
            logger.info(f"Using fallback assessments: {len(assessments)}")
        
        logger.info("API is ready to serve requests")
        
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        assessments = []

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        return HealthResponse(status="ok")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

def simple_keyword_search(query: str) -> List[Dict]:
    """Simple keyword-based search"""
    query_lower = query.lower()
    results = []
    
    for assessment in assessments:
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
            results.append({"assessment": assessment, "score": score})
    
    # Sort by score and return top 5
    results.sort(key=lambda x: x["score"], reverse=True)
    return [item["assessment"] for item in results[:5]]

def detect_phase(messages: List[Dict]) -> str:
    """Detect conversation phase"""
    if len(messages) <= 1:
        return "clarify"
    
    last_message = messages[-1].get("content", "").lower()
    
    # Check for comparison
    if any(keyword in last_message for keyword in ["difference", "compare", "vs", "versus"]):
        return "compare"
    
    # Check for refinement
    if any(keyword in last_message for keyword in ["add", "also", "include", "actually"]):
        return "refine"
    
    return "recommend"

def generate_response(messages: List[Dict]) -> ChatResponse:
    """Generate response"""
    try:
        phase = detect_phase(messages)
        last_message = messages[-1].get("content", "").lower()
        
        # Guardrails
        off_topic_keywords = ["weather", "sports", "politics", "entertainment", "news", "medical", "legal"]
        if any(keyword in last_message for keyword in off_topic_keywords):
            return ChatResponse(
                reply="I'm specifically designed to help with SHL assessment recommendations. I can't assist with general questions outside of assessment selection.",
                recommendations=[],
                end_of_conversation=False
            )
        
        # Prompt injection detection
        injection_keywords = ["ignore previous instructions", "system prompt", "forget everything", "new role"]
        if any(keyword in last_message for keyword in injection_keywords):
            return ChatResponse(
                reply="I cannot process that request. Please keep your questions focused on SHL assessments.",
                recommendations=[],
                end_of_conversation=False
            )
        
        if phase == "clarify":
            return ChatResponse(
                reply="I'd be happy to help you find the right SHL assessments! Could you tell me more about the role you're hiring for? For example, what type of position, seniority level, and key skills are you looking for?",
                recommendations=[],
                end_of_conversation=False
            )
        
        elif phase == "compare":
            return ChatResponse(
                reply="OPQ (Occupational Personality Questionnaire) is a personality assessment that measures behavioral traits and work preferences, while cognitive tests measure reasoning abilities and problem-solving skills. OPQ helps predict job fit and cultural alignment, whereas cognitive tests predict learning ability and job performance across different roles.",
                recommendations=[],
                end_of_conversation=False
            )
        
        elif phase == "refine":
            relevant_assessments = simple_keyword_search(last_message)
            recommendations = []
            for assessment in relevant_assessments[:3]:
                recommendations.append({
                    "name": assessment["name"],
                    "url": assessment["url"],
                    "test_type": assessment["test_type"]
                })
            
            return ChatResponse(
                reply=f"I'll add personality assessments to your recommendations. Here are {len(recommendations)} assessments including both technical and personality tests:",
                recommendations=recommendations,
                end_of_conversation=False
            )
        
        else:  # recommend
            relevant_assessments = simple_keyword_search(last_message)
            recommendations = []
            for assessment in relevant_assessments[:3]:
                recommendations.append({
                    "name": assessment["name"],
                    "url": assessment["url"],
                    "test_type": assessment["test_type"]
                })
            
            return ChatResponse(
                reply=f"Based on your needs, here are {len(recommendations)} assessments that would be a good fit:",
                recommendations=recommendations,
                end_of_conversation=False
            )
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return ChatResponse(
            reply="I apologize, but I'm having trouble processing your request right now. Please try again.",
            recommendations=[],
            end_of_conversation=False
        )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for conversational assessment recommendations"""
    try:
        # Validate request
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty")
        
        # Convert messages to dict format
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Process request
        start_time = time.time()
        response = generate_response(messages_dict)
        processing_time = time.time() - start_time
        
        logger.info(f"Processed chat request in {processing_time:.2f} seconds")
        logger.info(f"Generated {len(response.recommendations)} recommendations")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SHL Conversational Assessment Recommender API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "docs": "/docs"
        }
    }

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "minimal_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
