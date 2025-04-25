# YouTube Transcript RAG

A Chrome extension and local server that enables semantic search over YouTube video transcripts using RAG (Retrieval-Augmented Generation) and the PADM (Perception-Agent-Decision-Memory) architecture.

## Features

- Chrome extension for easy video indexing
- Semantic search over video transcripts
- Time-stamped results linking directly to video segments
- Local FAISS index for fast similarity search
- Gemini AI for natural language understanding and response generation

## Architecture

The project follows the PADM architecture:

- **Perception**: Analyzes user queries to understand intent and extract entities
- **Agent**: Orchestrates the interaction between components
- **Decision**: Generates natural language responses based on retrieved content
- **Memory**: Manages transcript storage and retrieval using FAISS

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file with:
```
GEMINI_API_KEY=your_key_here
```

3. Install the Chrome extension:
- Open Chrome and go to `chrome://extensions/`
- Enable "Developer mode"
- Click "Load unpacked" and select the `chrome_extension` directory

4. Start the local server:
```bash
python server/app.py
```

## Usage

1. Navigate to any YouTube video
2. Click the extension icon
3. Click "Index Current Video" to add it to your local index
4. Use the search box to ask questions about indexed videos
5. Results will include direct links to relevant video segments

## Components

- `server/`: Flask server for handling indexing and queries
- `agent/`: PADM architecture implementation
- `utils/`: Utility functions for transcript processing and indexing
- `chrome_extension/`: Browser extension for user interface
- `data/`: Storage for transcripts and FAISS index

## Requirements

- Python 3.8+
- Chrome browser
- Local Ollama server running with nomic-embed-text model
- Google Gemini API key

## Development

To modify the extension:
1. Make changes to files in `chrome_extension/`
2. Reload the extension in Chrome

To modify the server:
1. Update relevant Python files
2. Restart the Flask server

## License

MIT 