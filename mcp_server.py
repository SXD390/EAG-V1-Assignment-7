from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import sys
import logging
from pathlib import Path
import json
import time
import uuid
from typing import Dict, List, Any

# Import models
from models import (
    SearchInput, SearchOutput, 
    IndexInput, IndexOutput,
    StatusInput, StatusOutput,
    IndexingStatus
)

# Local imports
from utils.transcript_manager import TranscriptManager
from utils.status_tracker import StatusTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
logger = logging.getLogger("yt_rag.mcp")

# Initialize components
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

transcript_manager = TranscriptManager(
    transcripts_dir=DATA_DIR / "transcripts",
    index_dir=DATA_DIR / "faiss_index",
    chunk_size=60
)

status_tracker = StatusTracker()

# Initialize MCP server
mcp = FastMCP("YouTube RAG Tools")

def mcp_log(message: str) -> None:
    """Log a message to stderr to avoid interfering with JSON communication"""
    sys.stderr.write(f"MCP: {message}\n")
    sys.stderr.flush()

@mcp.tool()
def search_transcripts(input: SearchInput) -> SearchOutput:
    """Search indexed YouTube transcripts for relevant content"""
    mcp_log(f"Searching transcripts for: {input.query}")
    
    try:
        results = transcript_manager.search(input.query, k=input.top_k)
        mcp_log(f"Found {len(results)} results")
        return SearchOutput(results=results)
    except Exception as e:
        mcp_log(f"Search error: {str(e)}")
        return SearchOutput(results=[])

# Function to index a video - Not exposed as MCP tool as it's only for frontend use
def index_video(input: IndexInput) -> IndexOutput:
    """Index a YouTube video transcript"""
    mcp_log(f"Starting indexing for URL: {input.url}")
    
    try:
        # Create new operation
        operation_id = status_tracker.create_operation(input.url)
        
        # Start indexing in background thread
        import threading
        
        def index_thread():
            try:
                # Updating status to fetching metadata
                status_tracker.update_status(
                    operation_id, 
                    IndexingStatus.FETCHING_METADATA,
                    "Fetching video metadata..."
                )
                
                # Extract video ID and get metadata
                video_id = transcript_manager.extract_video_id(input.url)
                if not video_id:
                    status_tracker.update_status(
                        operation_id,
                        IndexingStatus.FAILED,
                        "Invalid YouTube URL",
                        "Could not extract video ID"
                    )
                    return
                    
                metadata = transcript_manager.get_video_metadata(input.url)
                if not metadata:
                    status_tracker.update_status(
                        operation_id,
                        IndexingStatus.FAILED,
                        "Failed to fetch video metadata",
                        "Could not retrieve video information"
                    )
                    return
                    
                # Update status to fetching transcript
                status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FETCHING_TRANSCRIPT,
                    "Fetching video transcript..."
                )
                
                # Get transcript
                transcript = transcript_manager.get_transcript(video_id)
                if not transcript:
                    status_tracker.update_status(
                        operation_id,
                        IndexingStatus.FAILED,
                        "Failed to fetch transcript",
                        "Could not retrieve video transcript"
                    )
                    return
                    
                # Update status to indexing
                status_tracker.update_status(
                    operation_id,
                    IndexingStatus.INDEXING,
                    "Processing and indexing transcript..."
                )
                
                # Index the video
                transcript_manager.index_video(input.url)
                
                # Update status to completed
                status_tracker.update_status(
                    operation_id,
                    IndexingStatus.COMPLETED,
                    "Video indexed successfully!"
                )
                
            except Exception as e:
                mcp_log(f"Error in indexing task: {str(e)}")
                # Update status to failed if any error occurs
                status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FAILED,
                    "An error occurred while indexing",
                    str(e)
                )
        
        # Start thread
        thread = threading.Thread(target=index_thread)
        thread.daemon = True
        thread.start()
        
        return IndexOutput(
            operation_id=operation_id,
            status="pending",
            message="Indexing started"
        )
        
    except Exception as e:
        mcp_log(f"Failed to start indexing: {str(e)}")
        return IndexOutput(
            operation_id=str(uuid.uuid4()),
            status="error",
            message=f"Failed to start indexing: {str(e)}"
        )

# Function to get status - Not exposed as MCP tool as it's only for frontend use
def get_indexing_status(input: StatusInput) -> StatusOutput:
    """Get the current status of an indexing operation"""
    mcp_log(f"Getting status for operation: {input.operation_id}")
    
    try:
        status = status_tracker.get_status(input.operation_id)
        return StatusOutput(
            status=status["status"],
            message=status["message"],
            elapsed_seconds=status["elapsed_seconds"],
            error=status.get("error")
        )
    except Exception as e:
        mcp_log(f"Error getting status: {str(e)}")
        return StatusOutput(
            status="error",
            message=f"Error retrieving status: {str(e)}",
            elapsed_seconds=0,
            error=str(e)
        )

if __name__ == "__main__":
    mcp_log("Starting MCP server for YouTube RAG Tools")
    mcp.run() 