from flask import Flask, request, jsonify
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import Agent
from utils.transcript_manager import TranscriptManager

app = Flask(__name__)
BASE_DIR = Path(__file__).parent.parent
transcript_manager = TranscriptManager(
    transcripts_dir=BASE_DIR / "data" / "transcripts",
    index_dir=BASE_DIR / "data" / "faiss_index"
)
agent = Agent(transcript_manager)

@app.route('/index_video', methods=['POST'])
def index_video():
    """Endpoint to index a YouTube video transcript."""
    data = request.json
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        video_id = transcript_manager.index_video(data['url'])
        return jsonify({
            "status": "success",
            "message": f"Video {video_id} indexed successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/query', methods=['POST'])
def query_transcripts():
    """Endpoint to query indexed transcripts."""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        results = agent.process_query(data['query'])
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True) 