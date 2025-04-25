from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

class PerceptionResult(BaseModel):
    query: str
    intent: str
    entities: List[str] = []
    context_needed: bool = True

class MemoryItem(BaseModel):
    text: str
    video_title: str
    url: str
    start_time: float
    end_time: float
    video_id: str

class Agent:
    def __init__(self, transcript_manager):
        """Initialize the agent with components."""
        self.transcript_manager = transcript_manager
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def perceive(self, query: str) -> PerceptionResult:
        """Extract intent and entities from user query."""
        prompt = f"""
Analyze this query about a YouTube video transcript:
"{query}"

Return a JSON with:
- intent: Main goal of the query (e.g., find_quote, explain_topic, locate_discussion)
- entities: Key terms or concepts to look for
- context_needed: Whether additional context might help (true/false)

Format: {{"intent": "...", "entities": ["..."], "context_needed": true/false}}
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            result = eval(response.text.strip())
            return PerceptionResult(query=query, **result)
        except Exception as e:
            return PerceptionResult(
                query=query,
                intent="unknown",
                entities=[],
                context_needed=True
            )

    def retrieve_memory(self, perception: PerceptionResult) -> List[MemoryItem]:
        """Search for relevant transcript chunks."""
        results = self.transcript_manager.search(perception.query)
        return [MemoryItem(**result) for result in results]

    def make_decision(self, perception: PerceptionResult, memories: List[MemoryItem]) -> str:
        """Generate a response based on perception and memories."""
        if not memories:
            return "I couldn't find any relevant information in the indexed videos."

        memory_context = "\n".join([
            f"- In video '{m.video_title}' at {int(m.start_time)}s: {m.text}"
            for m in memories
        ])

        prompt = f"""
Based on the query: "{perception.query}"
With intent: {perception.intent}
And key terms: {', '.join(perception.entities)}

I found these relevant segments:
{memory_context}

Generate a natural, helpful response that:
1. Directly answers the query
2. Cites specific timestamps and video titles
3. Quotes relevant parts of the transcript
4. Provides context when needed

Response should be in markdown format.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            return "I encountered an error while generating the response."

    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query through the PADM cycle."""
        # Perception
        perception = self.perceive(query)
        
        # Memory
        memories = self.retrieve_memory(perception)
        
        # Decision
        response = self.make_decision(perception, memories)
        
        # Return structured response
        return {
            "answer": response,
            "sources": [
                {
                    "video_title": m.video_title,
                    "url": m.url,
                    "timestamp": int(m.start_time)
                }
                for m in memories
            ]
        } 