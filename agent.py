import asyncio
import logging
import threading
import os
import traceback
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any, Optional
import time
from datetime import datetime

# Import PADM components
from perception import Perception
from memory import Memory
from decision import Decision
from action import Action
from models import IndexingStatus, SearchResult
from utils.transcript_manager import TranscriptManager
from utils.status_tracker import StatusTracker

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose logging
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yt_rag_debug.log')  # Also log to file
    ]
)
logger = logging.getLogger("yt_rag.agent")

class Agent:
    def __init__(self):
        """Initialize the agent with all components."""
        logger.debug("Initializing Agent")
        # Set up data directories
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        logger.debug(f"Data directory: {self.data_dir}")
        
        # Initialize components
        logger.debug("Initializing TranscriptManager")
        self.transcript_manager = TranscriptManager(
            transcripts_dir=self.data_dir / "transcripts",
            index_dir=self.data_dir / "faiss_index"
        )
        logger.debug("Initializing StatusTracker")
        self.status_tracker = StatusTracker()
        
        # Initialize PADM components
        logger.debug("Initializing PADM components")
        self.perception = Perception()
        self.memory = Memory(self.transcript_manager)
        self.decision = Decision()
        self.action = Action()
        
        logger.info("Agent initialized with all components")

    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query through the PADM cycle.
        
        Args:
            query: The user's natural language query
            
        Returns:
            Dictionary with answer and sources
        """
        logger.info(f"Processing query: {query}")
        start_time = time.time()
        
        try:
            # Perception: Extract intent and entities
            logger.debug("Starting perception phase")
            perception_result = self.perception.extract_intent(query)
            logger.info(f"Intent extracted: {perception_result.intent}")
            logger.debug(f"Perception result: {perception_result}")
            
            # Memory: Retrieve relevant transcript chunks
            logger.debug("Starting memory phase")
            memory_items = self.memory.retrieve(perception_result)
            logger.info(f"Retrieved {len(memory_items)} memory items")
            logger.debug(f"First memory item (if any): {memory_items[0] if memory_items else 'None'}")
            
            # Decision: Generate response based on perception and memory
            logger.debug("Starting decision phase")
            response_text = self.decision.generate_response(perception_result, memory_items)
            logger.info("Response generated")
            logger.debug(f"Response text first 100 chars: {response_text[:100]}...")
            
            # Action: Format final response
            logger.debug("Starting action phase")
            result = self.action.format_response(response_text, memory_items)
            logger.info("Response formatted with sources")
            logger.debug(f"Number of sources in result: {len(result.sources)}")
            
            end_time = time.time()
            logger.debug(f"Query processing completed in {end_time - start_time:.2f} seconds")
            
            # Convert to dict with the proper method
            result_dict = result.model_dump()
            logger.debug(f"Final result keys: {list(result_dict.keys())}")
            return result_dict
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            logger.error(traceback.format_exc())
            end_time = time.time()
            logger.debug(f"Query processing failed after {end_time - start_time:.2f} seconds")
            return {
                "error": str(e),
                "status": "error"
            }
    
    def index_video_task(self, operation_id: str, url: str):
        """Background task for indexing a video.
        
        Args:
            operation_id: Unique ID for tracking the operation
            url: YouTube video URL
        """
        logger.debug(f"Starting index_video_task for operation_id={operation_id}, url={url}")
        try:
            # Update status to fetching metadata
            logger.debug("Updating status to FETCHING_METADATA")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.FETCHING_METADATA,
                "Fetching video metadata..."
            )
            
            # Extract video ID and get metadata
            logger.debug("Extracting video ID")
            video_id = self.transcript_manager.extract_video_id(url)
            logger.debug(f"Extracted video_id: {video_id}")
            if not video_id:
                logger.warning(f"Invalid YouTube URL: {url}")
                self.status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FAILED,
                    "Invalid YouTube URL",
                    "Could not extract video ID"
                )
                return
                
            logger.debug("Fetching video metadata")
            metadata = self.transcript_manager.get_video_metadata(url)
            logger.debug(f"Metadata retrieved: {metadata is not None}")
            if not metadata:
                logger.warning("Failed to fetch video metadata")
                self.status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FAILED,
                    "Failed to fetch video metadata",
                    "Could not retrieve video information"
                )
                return
                
            # Update status to fetching transcript
            logger.debug("Updating status to FETCHING_TRANSCRIPT")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.FETCHING_TRANSCRIPT,
                "Fetching video transcript..."
            )
            
            # Get transcript
            logger.debug("Fetching transcript")
            transcript = self.transcript_manager.get_transcript(video_id)
            logger.debug(f"Transcript retrieved: {transcript is not None}")
            if not transcript:
                logger.warning("Failed to fetch transcript")
                self.status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FAILED,
                    "Failed to fetch transcript",
                    "Could not retrieve video transcript"
                )
                return
                
            # Update status to indexing
            logger.debug("Updating status to INDEXING")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.INDEXING,
                "Processing and indexing transcript..."
            )
            
            # Index the video
            logger.debug("Starting transcript indexing")
            self.transcript_manager.index_video(url)
            
            # Update status to completed
            logger.debug("Updating status to COMPLETED")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.COMPLETED,
                "Video indexed successfully!"
            )
            logger.debug(f"Indexing operation {operation_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error in indexing task: {str(e)}")
            logger.error(traceback.format_exc())
            # Update status to failed if any error occurs
            logger.debug(f"Updating status to FAILED for operation {operation_id}")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.FAILED,
                "An error occurred while indexing",
                str(e)
            )


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize agent
logger.debug("Initializing agent instance")
agent = Agent()

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler for Flask app."""
    logger.error(f"Global error handler triggered: {str(error)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": str(error),
        "status": "error"
    }), 500

@app.route("/index_video", methods=["POST"])
def index_video():
    """Start an asynchronous video indexing operation."""
    logger.debug("index_video endpoint called")
    try:
        data = request.get_json()
        logger.debug(f"Request data: {data}")
        if not data or "url" not in data:
            logger.warning("No URL provided in request")
            return jsonify({"error": "No URL provided"}), 400
            
        url = data["url"]
        logger.debug(f"URL to index: {url}")
        
        # Create new operation
        logger.debug("Creating new operation")
        operation_id = agent.status_tracker.create_operation(url)
        logger.debug(f"Operation ID created: {operation_id}")
        
        # Start indexing in background thread
        logger.debug("Starting indexing thread")
        thread = threading.Thread(
            target=agent.index_video_task,
            args=(operation_id, url)
        )
        thread.daemon = True
        thread.start()
        logger.debug("Indexing thread started")
        
        response = {
            "operation_id": operation_id,
            "message": "Indexing started",
            "status": "pending"
        }
        logger.debug(f"Returning response: {response}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error starting indexing: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/indexing_status/<operation_id>", methods=["GET"])
def get_indexing_status(operation_id):
    """Get the status of an indexing operation."""
    logger.debug(f"get_indexing_status endpoint called for operation_id={operation_id}")
    try:
        logger.debug("Retrieving status from status_tracker")
        status = agent.status_tracker.get_status(operation_id)
        logger.debug(f"Status retrieved: {status}")
        return jsonify(status)
    except ValueError as e:
        logger.warning(f"Operation not found: {operation_id}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 404
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/query', methods=['POST'])
def query():
    """Endpoint to query indexed transcripts."""
    logger.debug("query endpoint called")
    try:
        request_data = request.get_json()
        logger.debug(f"Request data: {request_data}")
        
        if not request_data or 'query' not in request_data:
            logger.warning("No query provided in request")
            return jsonify({"error": "No query provided", "status": "error"}), 400
        
        user_query = request_data['query']
        logger.debug(f"Processing query: '{user_query}'")
        
        # Process query through agent
        logger.debug("Calling agent.process_query")
        results = agent.process_query(user_query)
        logger.debug(f"Query results: {results.keys() if isinstance(results, dict) else 'not a dict'}")
        
        # Verify results structure before returning
        if isinstance(results, dict):
            if "error" in results:
                logger.warning(f"Error in results: {results['error']}")
            else:
                logger.debug(f"Results contains keys: {results.keys()}")
                if "answer" not in results:
                    logger.warning("Missing 'answer' in results")
                if "sources" not in results:
                    logger.warning("Missing 'sources' in results")
                    
        # Return results with explicit content type
        logger.debug("Returning query results")
        response = jsonify(results)
        logger.debug(f"Response mimetype: {response.mimetype}")
        return response
    
    except Exception as e:
        logger.error(f"Error in query endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        detailed_error = {
            "error": str(e),
            "status": "error",
            "traceback": traceback.format_exc().split("\n")
        }
        logger.debug(f"Returning error response: {detailed_error}")
        return jsonify(detailed_error), 500

if __name__ == "__main__":
    logger.info("Starting YouTube RAG Agent")
    app.run(debug=True) 