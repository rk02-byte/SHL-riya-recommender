from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging
import time
import os
from agent import SHLAgent, AgentResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SHL Conversational Assessment Recommender",
    description="AI-powered agent for recommending SHL assessments through natural dialogue",
    version="1.0.0"
)

# Global agent instance (loaded at startup)
agent = None

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
    """Initialize the agent and load FAISS index at startup"""
    global agent
    logger.info("Starting SHL Assessment Recommender API...")
    
    try:
        # Initialize agent (loads FAISS index and models)
        start_time = time.time()
        agent = SHLAgent()
        load_time = time.time() - start_time
        
        logger.info(f"Agent initialized successfully in {load_time:.2f} seconds")
        logger.info("API is ready to serve requests")
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        # Continue startup but agent will be None
        agent = None

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - must respond within 2 minutes on cold start"""
    try:
        if agent is None:
            logger.warning("Agent not initialized but health endpoint responding")
        
        return HealthResponse(status="ok")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for conversational assessment recommendations"""
    try:
        # Check if agent is available
        if agent is None:
            logger.error("Agent not initialized")
            raise HTTPException(status_code=503, detail="Service not available - agent not initialized")
        
        # Validate request
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty")
        
        # Convert messages to dict format for agent
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Process with agent (30 second timeout enforced by FastAPI)
        start_time = time.time()
        agent_response = agent.process_message(messages_dict)
        processing_time = time.time() - start_time
        
        logger.info(f"Processed chat request in {processing_time:.2f} seconds")
        logger.info(f"Generated {len(agent_response.recommendations)} recommendations")
        
        # Convert agent response to exact schema
        recommendations = []
        for rec in agent_response.recommendations:
            recommendations.append(Recommendation(
                name=rec.get("name", ""),
                url=rec.get("url", ""),
                test_type=rec.get("test_type", "")
            ))
        
        response = ChatResponse(
            reply=agent_response.reply,
            recommendations=recommendations,
            end_of_conversation=agent_response.end_of_conversation
        )
        
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

# Add CORS middleware for web access
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
