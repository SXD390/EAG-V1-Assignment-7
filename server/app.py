from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from pathlib import Path
import sys
import os
import traceback
import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.transcript_manager import TranscriptManager
from utils.status_tracker import StatusTracker, IndexingStatus
from agent.agent import Agent

app = Flask(__name__)
CORS(app)

# Initialize managers
transcript_manager = TranscriptManager(
    transcripts_dir=Path("data/transcripts"),
    index_dir=Path("data/faiss_index")
)
status_tracker = StatusTracker()
agent = Agent(transcript_manager=transcript_manager)

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler to ensure consistent error responses."""
    print("Error occurred:", error)
    print(traceback.format_exc())
    return jsonify({
        "error": str(error),
        "status": "error"
    }), 500

def index_video_task(operation_id: str, url: str):
    """Background task for indexing a video."""
    try:
        # Update status to fetching metadata
        status_tracker.update_status(
            operation_id,
            IndexingStatus.FETCHING_METADATA,
            "Fetching video metadata..."
        )
        
        # Extract video ID and get metadata
        video_id = transcript_manager.extract_video_id(url)
        if not video_id:
            status_tracker.update_status(
                operation_id,
                IndexingStatus.FAILED,
                "Invalid YouTube URL",
                "Could not extract video ID"
            )
            return
            
        metadata = transcript_manager.get_video_metadata(url)
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
        transcript_manager.index_video(url)
        
        # Update status to completed
        status_tracker.update_status(
            operation_id,
            IndexingStatus.COMPLETED,
            "Video indexed successfully!"
        )
        
    except Exception as e:
        print("Error in indexing task:", str(e))
        print(traceback.format_exc())
        # Update status to failed if any error occurs
        status_tracker.update_status(
            operation_id,
            IndexingStatus.FAILED,
            "An error occurred while indexing",
            str(e)
        )

@app.route("/index_video", methods=["POST"])
def index_video():
    """Start an asynchronous video indexing operation."""
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "No URL provided"}), 400
            
        url = data["url"]
        
        # Create new operation
        operation_id = status_tracker.create_operation(url)
        
        # Start indexing in background thread
        thread = threading.Thread(
            target=index_video_task,
            args=(operation_id, url)
        )
        thread.daemon = True  # Make thread daemon so it doesn't block app shutdown
        thread.start()
        
        return jsonify({
            "operation_id": operation_id,
            "message": "Indexing started",
            "status": "pending"
        })
    except Exception as e:
        print("Error starting indexing:", str(e))
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/indexing_status/<operation_id>", methods=["GET"])
def get_indexing_status(operation_id):
    """Get the status of an indexing operation."""
    try:
        status = status_tracker.get_status(operation_id)
        return jsonify(status)
    except ValueError as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 404
    except Exception as e:
        print("Error getting status:", str(e))
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/query', methods=['POST'])
def query():
    """Endpoint to query indexed transcripts."""
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        results = agent.process_query(data['query'])
        return jsonify(results)
    except Exception as e:
        print(f"Error in query: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

if __name__ == "__main__":
    app.run(debug=True) 