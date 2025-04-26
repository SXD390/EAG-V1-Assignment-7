from typing import List, Dict, Any
import logging
import time
from models import MemoryItem, SearchResult, ActionResult, DecisionResult, VideoSegment

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
logger = logging.getLogger("yt_rag.action")

class Action:
    """Generate response based on decision and memory items."""
    
    def __init__(self):
        """Initialize the action component."""
        logger.debug("Initializing Action component")
        # No initialization parameters needed currently
        logger.debug("Action component initialized")
    
    def generate_response(self, decision: DecisionResult, memory_items: List[MemoryItem]) -> ActionResult:
        """
        Generate a response based on the decision and memory items.
        
        Args:
            decision: The decision result from the Decision component
            memory_items: List of memory items from the Memory component
            
        Returns:
            ActionResult object containing the response
        """
        logger.info("Generating response")
        start_time = time.time()
        
        if not decision:
            logger.error("No decision provided for response generation")
            return ActionResult(
                response="I couldn't process that request. Please try again.",
                video_segments=[]
            )
            
        if not memory_items:
            logger.warning("No memory items available for response generation")
            return ActionResult(
                response="I couldn't find any relevant information in the video. Please try a different question or check if the video has been indexed.",
                video_segments=[]
            )
            
        logger.debug(f"Decision intent: {decision.intent}")
        logger.debug(f"Decision plan: {decision.plan}")
        logger.debug(f"Memory items count: {len(memory_items)}")
        
        relevant_segments = []
        
        # Extract video segments from memory items
        for item in memory_items:
            logger.debug(f"Processing memory item of type: {item.type}")
            
            if item.type == "video_segments":
                segments = item.content
                logger.debug(f"Found {len(segments)} video segments")
                
                # Sort segments by relevance (score)
                segments.sort(key=lambda x: x.score if hasattr(x, 'score') else 0, reverse=True)
                
                for i, segment in enumerate(segments[:3]):  # Log top 3 segments
                    if hasattr(segment, 'score'):
                        logger.debug(f"Segment {i+1}: score={segment.score:.4f}, time={segment.start_time}s-{segment.end_time}s")
                    else:
                        logger.debug(f"Segment {i+1}: time={segment.start_time}s-{segment.end_time}s (no score)")
                
                relevant_segments.extend(segments)
        
        # Determine response based on intent
        logger.debug(f"Constructing response for intent: {decision.intent}")
        response = self._create_response(decision, relevant_segments)
        
        # Package results
        result = ActionResult(
            response=response,
            video_segments=relevant_segments[:5]  # Limit to top 5 segments
        )
        
        end_time = time.time()
        logger.debug(f"Response generation completed in {end_time - start_time:.3f} seconds")
        logger.debug(f"Response length: {len(response)} characters")
        logger.debug(f"Included {len(result.video_segments)} video segments in result")
        
        return result
    
    def _create_response(self, decision: DecisionResult, segments: List) -> str:
        """
        Create a response based on the decision and segments.
        
        Args:
            decision: Decision result
            segments: List of video segments
            
        Returns:
            Formatted response string
        """
        logger.debug(f"Creating response for intent: {decision.intent}")
        start_time = time.time()
        
        if not segments:
            logger.warning("No segments available for response creation")
            return "I couldn't find any relevant information in this video. Please try a different question."
        
        intent = decision.intent
        response_text = ""
        
        try:
            if intent == "find_quote" or intent == "locate_information":
                logger.debug("Handling find_quote/locate_information intent")
                
                # For quote finding, we use the most relevant segment
                best_segment = segments[0]
                response_text = f"Here's what I found in the video: \"{best_segment.text}\""
                
                # Add timestamp information
                minutes, seconds = divmod(int(best_segment.start_time), 60)
                timestamp = f"{minutes}:{seconds:02d}"
                response_text += f" (at {timestamp})"
                
                logger.debug(f"Created quote response with timestamp {timestamp}")
                
            elif intent == "explain_topic" or intent == "find_definition":
                logger.debug("Handling explain_topic/find_definition intent")
                
                # For explanations, we combine information from multiple segments
                explanation = ""
                for i, segment in enumerate(segments[:3]):  # Use top 3 segments
                    explanation += segment.text + " "
                    logger.debug(f"Added segment {i+1} to explanation (length: {len(segment.text)} chars)")
                
                response_text = f"Based on the video, {explanation.strip()}"
                logger.debug(f"Created explanation response of {len(response_text)} characters")
                
            elif intent == "summarize_content":
                logger.debug("Handling summarize_content intent")
                
                # For summaries, use several segments but more concisely
                summary_parts = []
                for i, segment in enumerate(segments[:4]):  # Use top 4 segments
                    summary_parts.append(segment.text)
                    logger.debug(f"Added segment {i+1} to summary (length: {len(segment.text)} chars)")
                
                combined_text = " ".join(summary_parts)
                response_text = f"To summarize what's discussed in the video: {combined_text}"
                logger.debug(f"Created summary response of {len(response_text)} characters")
                
            else:
                logger.debug(f"Handling generic/unknown intent: {intent}")
                
                # Generic response for other intents
                best_segment = segments[0]
                response_text = f"From the video: {best_segment.text}"
                logger.debug("Created generic response")
        
        except Exception as e:
            logger.error(f"Error creating response: {str(e)}", exc_info=True)
            response_text = "I found some information in the video but had trouble formatting it. Here's the relevant part: "
            
            # Fallback to using first segment
            if segments:
                response_text += segments[0].text
        
        end_time = time.time()
        logger.debug(f"Response creation completed in {end_time - start_time:.3f} seconds")
        
        return response_text

    def format_response(self, generated_text: str, memory_items: List[MemoryItem]) -> SearchResult:
        """Format the final response including generated text and sources.
        
        Args:
            generated_text: The text generated by the decision component
            memories: The memory items used to generate the response
            
        Returns:
            A SearchResult object with answer and sources
        """
        logger.info("Formatting response with sources")
        
        # Extract video segments from memory items
        all_segments = []
        for item in memory_items:
            if hasattr(item, 'type') and item.type == "video_segments":
                all_segments.extend(item.content)
        
        # Format sources with relevant information
        sources = []
        for segment in all_segments[:5]:  # Limit to top 5 segments
            try:
                sources.append({
                    "video_title": segment.video_title,
                    "url": segment.url,
                    "timestamp": int(segment.start_time),
                    "text": segment.text
                })
            except Exception as e:
                logger.warning(f"Error formatting segment as source: {e}")
            
        # Create search result
        result = SearchResult(
            answer=generated_text,
            sources=sources
        )
        
        logger.debug(f"Formatted response with {len(sources)} sources")
        return result 