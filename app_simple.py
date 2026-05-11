import streamlit as st
import json
import logging
from typing import List, Dict, Tuple
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global assessments data
assessments = []

def load_assessments():
    """Load assessments from catalog"""
    global assessments
    try:
        # Built-in fallback assessments - no external dependencies needed
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
            },
            {
                "name": "Situational Judgment Test",
                "url": "https://www.shl.com/products/assessments/situational-judgment-tests/",
                "description": "Assesses candidate's judgment in work-related situations. Measures ability to choose appropriate actions in workplace scenarios.",
                "test_type": "B",
                "remote_testing": True,
                "adaptive_irt": False
            },
            {
                "name": "Numerical Reasoning Test",
                "url": "https://www.shl.com/products/assessments/cognitive-assessments/numerical-reasoning/",
                "description": "Evaluates ability to work with numerical data, interpret charts and graphs, and perform mathematical calculations.",
                "test_type": "K",
                "remote_testing": True,
                "adaptive_irt": True
            },
            {
                "name": "Verbal Reasoning Test",
                "url": "https://www.shl.com/products/assessments/cognitive-assessments/verbal-reasoning/",
                "description": "Measures ability to understand and evaluate written information, identify logical relationships, and draw conclusions from text.",
                "test_type": "K",
                "remote_testing": True,
                "adaptive_irt": True
            },
            {
                "name": "Python Programming Test",
                "url": "https://www.shl.com/products/assessments/skills-and-simulations/technical-skills/python-programming/",
                "description": "Assesses Python programming knowledge including data structures, algorithms, object-oriented programming, and standard libraries.",
                "test_type": "S",
                "remote_testing": True,
                "adaptive_irt": False
            },
            {
                "name": "Customer Service Skills Test",
                "url": "https://www.shl.com/products/assessments/skills-and-simulations/customer-service-skills/",
                "description": "Evaluates customer service competencies including communication, problem-solving, and service orientation.",
                "test_type": "S",
                "remote_testing": True,
                "adaptive_irt": False
            },
            {
                "name": "Mechanical Comprehension Test",
                "url": "https://www.shl.com/products/assessments/cognitive-assessments/mechanical-comprehension/",
                "description": "Assesses understanding of basic mechanical principles and ability to apply them to solve practical problems.",
                "test_type": "K",
                "remote_testing": True,
                "adaptive_irt": False
            },
            {
                "name": "Cognitive Ability Test (CAT)",
                "url": "https://www.shl.com/products/assessments/cognitive-assessments/cognitive-ability-test/",
                "description": "Adaptive cognitive assessment that measures reasoning abilities across multiple domains with item response theory.",
                "test_type": "K",
                "remote_testing": True,
                "adaptive_irt": True
            }
        ]
        logger.info(f"Loaded {len(assessments)} built-in assessments")
        
    except Exception as e:
        logger.error(f"Failed to load assessments: {e}")
        assessments = []

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
        keywords = ["java", "python", "programming", "personality", "cognitive", "technical", "numerical", "verbal", "situational", "customer", "mechanical"]
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

def generate_response(messages: List[Dict]) -> Dict:
    """Generate response"""
    try:
        phase = detect_phase(messages)
        last_message = messages[-1].get("content", "").lower()
        
        # Guardrails
        off_topic_keywords = ["weather", "sports", "politics", "entertainment", "news", "medical", "legal"]
        if any(keyword in last_message for keyword in off_topic_keywords):
            return {
                "reply": "I'm specifically designed to help with SHL assessment recommendations. I can't assist with general questions outside of assessment selection.",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        # Prompt injection detection
        injection_keywords = ["ignore previous instructions", "system prompt", "forget everything", "new role"]
        if any(keyword in last_message for keyword in injection_keywords):
            return {
                "reply": "I cannot process that request. Please keep your questions focused on SHL assessments.",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        if phase == "clarify":
            return {
                "reply": "I'd be happy to help you find the right SHL assessments! Could you tell me more about the role you're hiring for? For example, what type of position, seniority level, and key skills are you looking for?",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        elif phase == "compare":
            return {
                "reply": "OPQ (Occupational Personality Questionnaire) is a personality assessment that measures behavioral traits and work preferences, while cognitive tests measure reasoning abilities and problem-solving skills. OPQ helps predict job fit and cultural alignment, whereas cognitive tests predict learning ability and job performance across different roles.",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        elif phase == "refine":
            relevant_assessments = simple_keyword_search(last_message)
            recommendations = []
            for assessment in relevant_assessments[:3]:
                recommendations.append({
                    "name": assessment["name"],
                    "url": assessment["url"],
                    "test_type": assessment["test_type"]
                })
            
            return {
                "reply": f"I'll add personality assessments to your recommendations. Here are {len(recommendations)} assessments including both technical and personality tests:",
                "recommendations": recommendations,
                "end_of_conversation": False
            }
        
        else:  # recommend
            relevant_assessments = simple_keyword_search(last_message)
            recommendations = []
            for assessment in relevant_assessments[:3]:
                recommendations.append({
                    "name": assessment["name"],
                    "url": assessment["url"],
                    "test_type": assessment["test_type"]
                })
            
            return {
                "reply": f"Based on your needs, here are {len(recommendations)} assessments that would be a good fit:",
                "recommendations": recommendations,
                "end_of_conversation": False
            }
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return {
            "reply": "I apologize, but I'm having trouble processing your request right now. Please try again.",
            "recommendations": [],
            "end_of_conversation": False
        }

def main():
    st.set_page_config(
        page_title="SHL Assessment Recommender",
        page_icon="🎯",
        layout="centered",
        initial_sidebar_state="expanded"
    )
    
    # Load assessments
    if 'assessments_loaded' not in st.session_state:
        load_assessments()
        st.session_state.assessments_loaded = True
    
    # Header
    st.title("🎯 SHL Assessment Recommender")
    st.markdown("AI-powered agent for recommending SHL assessments through natural dialogue")
    
    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display recommendations if any
            if "recommendations" in message and message["recommendations"]:
                st.markdown("**Recommended Assessments:**")
                for rec in message["recommendations"]:
                    st.markdown(f"📋 [{rec['name']}]({rec['url']}) - Type: {rec['test_type']}")
    
    # Chat input
    if prompt := st.chat_input("Tell me about your hiring needs..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        response = generate_response(st.session_state.messages)
        
        # Add assistant response
        with st.chat_message("assistant"):
            st.markdown(response["reply"])
            
            # Display recommendations if any
            if response["recommendations"]:
                st.markdown("**Recommended Assessments:**")
                for rec in response["recommendations"]:
                    st.markdown(f"📋 [{rec['name']}]({rec['url']}) - Type: {rec['test_type']}")
        
        # Save assistant message
        assistant_message = {
            "role": "assistant", 
            "content": response["reply"],
            "recommendations": response["recommendations"]
        }
        st.session_state.messages.append(assistant_message)
    
    # Sidebar with information
    with st.sidebar:
        st.header("About")
        st.markdown("""
        **SHL Assessment Recommender** helps hiring managers find the right assessments through natural conversation.
        
        **Features:**
        - 🤖 Conversational AI interface
        - 🎯 Personalized recommendations
        - 🔍 Keyword-based search
        - 🛡️ Built-in guardrails
        
        **Assessment Types:**
        - **P** - Personality
        - **K** - Cognitive/Ability  
        - **S** - Skills/Technical
        - **B** - Behavioral
        """)
        
        st.header("Usage Tips")
        st.markdown("""
        1. Be specific about role
        2. Mention key skills required
        3. Include seniority level
        4. Ask for comparisons
        5. Request refinements
        """)
        
        st.header("Example Queries")
        st.markdown("""
        - "I need to hire a Java developer"
        - "Compare OPQ vs cognitive tests"
        - "Add personality assessments too"
        - "Mid-level Python developer"
        """)
        
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by SHL Assessment Catalog*")

if __name__ == "__main__":
    import os
    main()
