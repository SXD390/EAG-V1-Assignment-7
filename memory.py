from typing import List, Dict, Any, Optional
import logging
import time
import json
from models import PerceptionResult, MemoryItem, VideoSegment

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("yt_rag.memory")

class Memory:
    """Store and retrieve information from the current video context and past interactions."""
    
    def __init__(self, transcript_manager):
        """Initialize memory with transcript manager."""
        logger.debug("Initializing Memory component")
        self.transcript_manager = transcript_manager
        self.current_video_id = None
        self.current_segments = []
        self.conversation_history = []
        logger.debug("Memory component initialized")
        
    def retrieve(self, perception: PerceptionResult) -> List[MemoryItem]:
        """
        Retrieve memory items relevant to the perception result.
        This is a wrapper around get_memory_items for compatibility with the agent.py interface.
        
        Args:
            perception: PerceptionResult containing query and intent
            
        Returns:
            List of MemoryItem objects
        """
        logger.info(f"Retrieving memory items for perception: {perception.intent}")
        return self.get_memory_items(perception.query)
        
    def set_video_context(self, video_id: str) -> bool:
        """
        Set the current video context and load its segments.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Success state (bool)
        """
        logger.info(f"Setting video context: {video_id}")
        start_time = time.time()
        
        if not video_id:
            logger.warning("Attempted to set empty video ID")
            return False
            
        if video_id == self.current_video_id:
            logger.debug(f"Video {video_id} is already the current context")
            return True
            
        try:
            logger.debug(f"Loading segments for video: {video_id}")
            segments = self.transcript_manager.load_segments(video_id)
            
            if not segments:
                logger.warning(f"No segments found for video: {video_id}")
                return False
                
            self.current_video_id = video_id
            self.current_segments = segments
            segments_count = len(segments) if segments else 0
            logger.debug(f"Loaded {segments_count} segments for video {video_id}")
            
            end_time = time.time()
            logger.debug(f"Video context set in {end_time - start_time:.3f} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error setting video context: {str(e)}", exc_info=True)
            return False
            
    def search_relevant_segments(self, query: str, top_k: int = 5) -> List[VideoSegment]:
        """
        Search for video segments relevant to the user query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant VideoSegment objects
        """
        if not query:
            logger.warning("Empty query provided for search")
            return []
            
        if not self.current_video_id:
            logger.warning("No video context set for search")
            return []
            
        logger.info(f"Searching for segments matching query: '{query}'")
        start_time = time.time()
        
        try:
            logger.debug(f"Performing search with top_k={top_k}")
            results = self.transcript_manager.search(query, top_k=top_k)
            
            if not results:
                logger.warning(f"No results found for query: '{query}'")
                return []
                
            result_count = len(results)
            logger.debug(f"Search returned {result_count} results")
            
            # Convert raw results to VideoSegment objects
            video_segments = []
            for i, result in enumerate(results):
                try:
                    segment = VideoSegment(
                        text=result.get('text', ''),
                        start_time=result.get('start_time', 0),
                        end_time=result.get('end_time', 0),
                        video_id=result.get('video_id', ''),
                        video_title=result.get('video_title', 'Unknown Video'),
                        url=result.get('url', ''),
                        score=1.0 - (i / len(results)) if len(results) > 1 else 1.0  # Simple score based on position
                    )
                    video_segments.append(segment)
                except Exception as e:
                    logger.error(f"Error creating VideoSegment from result: {e}")
            
            # Log sample of results
            if result_count > 0:
                sample_size = min(3, result_count)
                sample = video_segments[:sample_size]
                for i, segment in enumerate(sample):
                    logger.debug(f"Result {i+1}: Score={segment.score:.4f}, Time={segment.start_time}s-{segment.end_time}s")
                    logger.debug(f"Text snippet: '{segment.text[:100]}...'")
            
            end_time = time.time()
            logger.debug(f"Search completed in {end_time - start_time:.3f} seconds")
            return video_segments
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}", exc_info=True)
            return []
            
    def add_interaction(self, query: str, response: str) -> None:
        """
        Add user interaction to conversation history.
        
        Args:
            query: User query
            response: System response
        """
        logger.debug(f"Adding interaction to history: Query='{query[:50]}...'")
        
        if not query or not response:
            logger.warning("Attempted to add empty interaction to history")
            return
            
        interaction = {
            "query": query,
            "response": response,
            "timestamp": time.time()
        }
        
        self.conversation_history.append(interaction)
        history_length = len(self.conversation_history)
        logger.debug(f"Conversation history updated, now contains {history_length} interactions")
        
    def get_recent_interactions(self, count: int = 3) -> List[Dict[str, Any]]:
        """
        Get the most recent interactions.
        
        Args:
            count: Number of interactions to retrieve
            
        Returns:
            List of recent interactions
        """
        logger.debug(f"Retrieving {count} recent interactions")
        history_length = len(self.conversation_history)
        
        if history_length == 0:
            logger.debug("Conversation history is empty")
            return []
            
        # Get the last 'count' interactions
        recent = self.conversation_history[-count:] if count < history_length else self.conversation_history
        logger.debug(f"Retrieved {len(recent)} recent interactions")
        
        return recent
        
    def get_memory_items(self, query: str, max_segments: int = 5) -> List[MemoryItem]:
        """
        Get memory items relevant to the current query.
        
        Args:
            query: User query
            max_segments: Maximum number of segments to include
            
        Returns:
            List of MemoryItem objects
        """
        logger.info(f"Getting memory items for query: '{query}'")
        start_time = time.time()
        
        memory_items = []
        
        # Get relevant video segments
        logger.debug("Searching for relevant video segments")
        segments_start = time.time()
        relevant_segments = self.search_relevant_segments(query, top_k=max_segments)
        segments_end = time.time()
        
        logger.debug(f"Found {len(relevant_segments)} relevant segments in {segments_end - segments_start:.3f} seconds")
        
        if relevant_segments:
            # Create memory item for video context
            video_memory = MemoryItem(
                type="video_segments",
                content=relevant_segments
            )
            memory_items.append(video_memory)
            
            # Log some details about the segments
            total_duration = sum(s.end_time - s.start_time for s in relevant_segments)
            total_text_length = sum(len(s.text) for s in relevant_segments)
            logger.debug(f"Video segments cover {total_duration:.1f} seconds with {total_text_length} characters")
        
        # Get recent conversation history
        logger.debug("Retrieving recent conversation history")
        history_start = time.time()
        recent_interactions = self.get_recent_interactions(count=3)
        history_end = time.time()
        
        logger.debug(f"Retrieved {len(recent_interactions)} recent interactions in {history_end - history_start:.3f} seconds")
        
        if recent_interactions:
            # Create memory item for conversation history
            history_memory = MemoryItem(
                type="conversation_history",
                content=recent_interactions
            )
            memory_items.append(history_memory)
        
        end_time = time.time()
        logger.debug(f"Memory items retrieval completed in {end_time - start_time:.3f} seconds")
        logger.debug(f"Returning {len(memory_items)} memory items")
        
        return memory_items 