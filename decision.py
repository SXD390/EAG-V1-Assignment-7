import os
from dotenv import load_dotenv
from google import genai
import logging
from typing import List, Optional
from models import PerceptionResult, MemoryItem, DecisionResult, VideoSegment
import time
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("yt_rag.decision")

load_dotenv()

class Decision:
    def __init__(self):
        """Initialize the decision component."""
        logger.debug("Initializing Decision component")
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("GEMINI_API_KEY not found in environment variables")
                logger.info("Decision component will provide informational responses only")
                self.client = None
            else:
                logger.debug("GEMINI_API_KEY found in environment variables")
                self.client = genai.Client(api_key=api_key)
                logger.info("Gemini API initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Gemini API: {e}")
            logger.error("Traceback:", exc_info=True)
            self.client = None
    
    def generate_response(self, perception: PerceptionResult, memory_items: List[MemoryItem]) -> str:
        """
        Generate a response based on perception and memory.
        This is a wrapper around generate_plan for compatibility with the agent.py interface.
        
        Args:
            perception: The perception result containing query and intent
            memory_items: List of memory items from the memory component
            
        Returns:
            Generated response as a string
        """
        logger.info(f"Generating response for query: {perception.query}")
        decision_result = self.generate_plan(perception, memory_items)
        return decision_result.response
        
    def generate_plan(self, perception: PerceptionResult, memory_items: List[MemoryItem]) -> DecisionResult:
        """Generate a plan based on perception and memory.
        
        Args:
            perception: The perception result containing query and intent
            memory_items: List of memory items from the memory component
            
        Returns:
            A decision result containing the plan
        """
        logger.info(f"Generating plan for query: {perception.query}")
        start_time = time.time()
        logger.debug(f"Intent: {perception.intent}")
        logger.debug(f"Entities: {perception.entities}")
        logger.debug(f"Memory items count: {len(memory_items)}")

        # Check if we have memory items to work with
        if not memory_items:
            logger.warning("No memory items found for query. Cannot generate a meaningful response.")
            return DecisionResult(
                response="I couldn't find any relevant information about this topic in the video content. "
                         "Please try a different query or ensure a video has been loaded.",
                should_search_more=False
            )

        # Construct the system prompt
        logger.debug("Constructing system prompt")
        prompt_start = time.time()
        
        # Extract and format video segments
        video_segments = []
        conversation_history = []
        
        for item in memory_items:
            if hasattr(item, 'type'):
                # Handle different types of memory items
                if item.type == "video_segments":
                    segments = item.content
                    logger.debug(f"Found {len(segments)} video segments")
                    video_segments.extend(segments)
                elif item.type == "conversation_history":
                    logger.debug("Found conversation history")
                    conversation_history = item.content
            else:
                # Handle direct memory items that might be VideoSegment objects
                video_segments.append(item)
        
        # Format video segments for the prompt
        memory_segments = []
        segment_count = min(len(video_segments), 10)  # Limit to top 10 for prompt length
        
        logger.debug(f"Processing {segment_count} video segments for prompt")
        for i, segment in enumerate(video_segments[:segment_count]):
            try:
                # Format timestamp for readability
                minutes, seconds = divmod(int(segment.start_time), 60)
                timestamp = f"{minutes}:{seconds:02d}"
                
                # Format segment info
                segment_info = f"Segment {i+1} from '{segment.video_title}' (timestamp: {timestamp})"
                memory_segments.append(f"{segment_info}\n{segment.text}")
                logger.debug(f"Added segment {i+1} from video: {segment.video_title[:30]}...")
            except Exception as e:
                logger.warning(f"Error formatting video segment {i}: {e}")
        
        # Format conversation history if available
        conversation_context = ""
        if conversation_history:
            logger.debug(f"Including {len(conversation_history)} conversation history items")
            conv_items = []
            for i, conv in enumerate(conversation_history):
                conv_items.append(f"User: {conv['query']}\nAssistant: {conv['response']}")
            
            conversation_context = "## Previous Conversation\n" + "\n\n".join(conv_items)
        
        # Combine all segments
        memory_text = "\n\n".join(memory_segments)
        logger.debug(f"Memory segments combined, total length: {len(memory_text)} chars")
        
        # Build the full prompt
        system_prompt = f"""🤖 ROLE AND GOAL
You are a YouTube video transcript assistant with expert reasoning abilities. Your task is to respond to queries about YouTube video content using only information from the provided transcript segments.

📝 QUERY CONTEXT
- User Query: "{perception.query}"
- Detected Intent: {perception.intent}
- Key Entities: {', '.join(perception.entities) if perception.entities else 'None detected'}

📋 TRANSCRIPT SEGMENTS
{memory_text}

{conversation_context}

📊 RESPONSE GUIDELINES
1. Analyze the transcript segments thoroughly before responding
2. Structure your response clearly using Markdown:
   - Use headings (##) for main sections
   - Use bullet points for lists
   - Use **bold** for emphasis
3. ALWAYS quote directly from the transcript when referencing specific content using > blockquotes
4. Include relevant timestamps when available
5. For specific claims, mention which video and timestamp the information comes from

⚠️ CRITICAL RULES
- NEVER fabricate or assume information not present in the transcript segments
- If the transcript segments don't contain sufficient information to answer the query, clearly state this
- Precision is more important than comprehensiveness - be accurate with what you know
- Citations should use the format: > "quoted text" (Video Title, timestamp)
"""
        
        prompt_end = time.time()
        prompt_duration = prompt_end - prompt_start
        logger.debug(f"Prompt construction completed in {prompt_duration:.3f} seconds")
        logger.debug(f"Prompt length: {len(system_prompt)} characters")
        
        # Generate a response using Gemini API
        logger.debug("Calling Gemini API to generate response")
        api_call_start = time.time()
        
        try:
            if not self.client:
                logger.warning("No Gemini client available, returning default response")
                api_response = "I don't have enough information to answer that question based on the video content."
            else:
                logger.debug("Initializing Gemini model")
                # Make the API call with error handling
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=system_prompt
                )
                logger.debug("Received response from Gemini API")
                
                # Check if response has text attribute and is not empty
                if hasattr(response, 'text') and response.text.strip():
                    logger.info("Successfully generated response")
                    api_response = response.text
                else:
                    logger.warning("Empty response received from Gemini API")
                    api_response = "I couldn't generate a proper response. Please try again or rephrase your query."
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            logger.error("Traceback:", exc_info=True)
            api_response = (f"I encountered an issue while processing your query. "
                          f"Please try again or rephrase your question.")
        
        api_call_end = time.time()
        api_call_duration = api_call_end - api_call_start
        logger.debug(f"API call completed in {api_call_duration:.3f} seconds")
        
        end_time = time.time()
        total_duration = end_time - start_time
        logger.debug(f"Plan generation completed in {total_duration:.3f} seconds")
        logger.info("Decision generated successfully")
        
        # Return the decision result
        return DecisionResult(
            response=api_response,
            should_search_more=False  # Currently not implementing multi-step search
        ) 