# YouTube Transcript RAG System

A Retrieval-Augmented Generation (RAG) system for YouTube videos using the PADM (Perception-Action-Decision-Memory) architecture.

## Project Structure

The project follows the PADM architecture for agentic systems:

- **Perception**: Extracts intent and entities from user queries
- **Memory**: Retrieves relevant transcript chunks using semantic search
- **Decision**: Generates responses based on perception and memory
- **Action**: Formats the final response with sources

## Components

- `agent.py`: Main agent with integrated Flask server
- `perception.py`: Query intent extraction
- `memory.py`: Transcript retrieval
- `decision.py`: Response generation
- `action.py`: Result formatting
- `models.py`: Data models
- `mcp_server.py`: MCP tools for transcript search and indexing
- `utils/transcript_manager.py`: Core transcript handling functionality
- `utils/status_tracker.py`: Indexing operation status tracking

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

3. Start the Ollama server for embeddings (requires [Ollama](https://ollama.ai/)):
   ```bash
   ollama run nomic-embed-text
   ```

## Usage

### Starting the Agent Server

```bash
python agent.py
```

The server runs on http://localhost:5000 by default.

### Using the Chrome Extension

1. Navigate to the `chrome_extension` directory.
2. Load the extension in Chrome's developer mode.
3. Go to a YouTube video and use the extension to:
   - Index the current video transcript
   - Query indexed transcripts

## API Endpoints

- `POST /index_video`: Index a YouTube video transcript
  ```json
  {
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }
  ```

- `GET /indexing_status/<operation_id>`: Get indexing status

- `POST /query`: Query indexed transcripts
  ```json
  {
    "query": "What does the video talk about?"
  }
  ```

## MCP Tools (optional)

You can also run the MCP tools server for programmatic access:

```bash
python mcp_server.py
```

Available tools:
- `search_transcripts`: Search indexed transcripts
- `index_video`: Index a YouTube video
- `get_indexing_status`: Get operation status 