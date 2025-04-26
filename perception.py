import os
import json
from dotenv import load_dotenv
from google import genai
from models import PerceptionResult
import logging
import time
import re
from typing import List, Dict, Any, Optional

load_dotenv()

# Configure logging with debug level
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("yt_rag.perception")

class Perception:
    def __init__(self):
        """Initialize perception component with Gemini client."""
        logger.debug("Initializing Perception component")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment, using mock perception")
        self.client = genai.Client(api_key=api_key) if api_key else None
        logger.debug(f"Gemini client initialized: {self.client is not None}")

        self.intent_patterns = {
            "find_quote": [
                r"quote|said|mentioned|talked about|spoke about|discuss",
                r"exact|precise|verbatim|literal|word for word",
                r"what did .* say about",
                r"how did .* describe",
            ],
            "explain_topic": [
                r"explain|describe|elaborate on|tell me about|what is|how does",
                r"concept|topic|idea|subject|phenomenon",
                r"how .* works",
                r"why is .* important",
            ],
            "summarize_content": [
                r"summarize|summary|overview|brief|main points",
                r"key takeaways|highlights|main ideas",
                r"tldr|tl;dr",
                r"recap|nutshell",
            ],
            "find_definition": [
                r"define|definition|meaning of|what does .* mean",
                r"what is the definition of",
                r"explain the term",
            ],
            "locate_information": [
                r"where|when|find|locate|search for",
                r"timestamp|time|point in the video",
                r"section|part",
            ]
        }
        logger.debug(f"Initialized with {len(self.intent_patterns)} intent patterns")

    def extract_intent(self, query: str) -> PerceptionResult:
        """Extract intent and entities from a user query."""
        logger.info(f"Extracting intent from query: {query}")
        
        if not self.client:
            logger.debug("No Gemini client available, using mock perception")
            mock_result = PerceptionResult(
                query=query,
                intent="general_question",
                entities=[],
                context_needed=True
            )
            logger.debug(f"Mock perception result: {mock_result}")
            return mock_result
        
        logger.debug("Preparing prompt for Gemini")
        prompt = f"""
Analyze this query about a YouTube video transcript:
"{query}"

Return a JSON with:
- intent: Main goal of the query (e.g., find_quote, explain_topic, locate_discussion, summarize_content)
- entities: Key terms or concepts to look for
- context_needed: Whether additional context might help (true/false)

Format: {{"intent": "...", "entities": ["..."], "context_needed": true/false}}
"""
        logger.debug("Prompt prepared, sending to Gemini API")
        
        try:
            logger.debug("Calling Gemini API")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            raw_response = response.text.strip()
            logger.debug(f"Raw Gemini response received: {raw_response}")
            
            # Parse and validate the response safely
            logger.debug("Parsing API response")
            try:
                # Try to parse as JSON first
                logger.debug("Attempting to parse response as JSON")
                result = json.loads(raw_response)
                logger.debug(f"Successfully parsed JSON: {result}")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}")
                # If not valid JSON, try to extract JSON from the text
                logger.debug("Attempting to extract JSON from text using regex")
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    logger.debug(f"JSON pattern found: {json_match.group(0)}")
                    try:
                        result = json.loads(json_match.group(0))
                        logger.debug(f"Successfully parsed extracted JSON: {result}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse extracted JSON: {e}")
                        # Fallback to default values
                        logger.debug("Using default values due to parsing failure")
                        result = {
                            "intent": "general_question",
                            "entities": [],
                            "context_needed": True
                        }
                else:
                    logger.warning("No JSON pattern found in response")
                    # No JSON found, use default values
                    logger.debug("Using default values due to no JSON pattern")
                    result = {
                        "intent": "general_question",
                        "entities": [],
                        "context_needed": True
                    }
            
            # Ensure entities is a list
            logger.debug("Validating entities field")
            if "entities" in result and not isinstance(result["entities"], list):
                logger.debug(f"Converting entities to list: {result['entities']}")
                if isinstance(result["entities"], str):
                    result["entities"] = [result["entities"]]
                    logger.debug(f"Converted string to list: {result['entities']}")
                else:
                    logger.warning(f"Unexpected entities type: {type(result['entities'])}, using empty list")
                    result["entities"] = []
            
            logger.info(f"Detected intent: {result.get('intent', 'unknown')}")
            
            # Create and return PerceptionResult
            logger.debug("Creating PerceptionResult")
            perception_result = PerceptionResult(query=query, **result)
            logger.debug(f"Returning perception result: {perception_result}")
            return perception_result
            
        except Exception as e:
            logger.error(f"Error in perception: {str(e)}")
            logger.error("Traceback:", exc_info=True)
            # Fallback to default intent
            logger.debug("Using default PerceptionResult due to error")
            default_result = PerceptionResult(
                query=query,
                intent="unknown",
                entities=[],
                context_needed=True
            )
            logger.debug(f"Default perception result: {default_result}")
            return default_result 

    def process_query(self, query: str) -> PerceptionResult:
        """
        Process the user query to extract intent and entities.
        
        Args:
            query: The user's query string
            
        Returns:
            PerceptionResult with the detected intent and entities
        """
        if not query or not isinstance(query, str):
            logger.warning(f"Invalid query received: {query}")
            return PerceptionResult(
                query="",
                intent="general_query",
                entities=[]
            )
            
        start_time = time.time()
        logger.info(f"Processing query: {query}")
        logger.debug(f"Query length: {len(query)} characters")
        
        # Detect intent
        intent_start = time.time()
        intent = self._detect_intent(query)
        intent_end = time.time()
        intent_duration = intent_end - intent_start
        logger.debug(f"Intent detection completed in {intent_duration:.3f} seconds")
        logger.debug(f"Detected intent: {intent}")
        
        # Extract entities
        entity_start = time.time()
        entities = self._extract_entities(query)
        entity_end = time.time()
        entity_duration = entity_end - entity_start
        logger.debug(f"Entity extraction completed in {entity_duration:.3f} seconds")
        logger.debug(f"Extracted entities: {entities}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        logger.debug(f"Query processing completed in {total_duration:.3f} seconds")
        
        # Create and return the perception result
        result = PerceptionResult(
            query=query.strip(),
            intent=intent,
            entities=entities
        )
        logger.info(f"Perception result: intent={intent}, entities_count={len(entities)}")
        return result
        
    def _detect_intent(self, query: str) -> str:
        """
        Detect the intent of the user's query.
        
        Args:
            query: The user's query string
            
        Returns:
            The detected intent as a string
        """
        logger.debug("Detecting intent from query")
        query = query.lower()
        
        # Score each intent based on matching patterns
        intent_scores: Dict[str, int] = {}
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    score += 1
                    logger.debug(f"Pattern match: '{pattern}' for intent '{intent}'")
            intent_scores[intent] = score
            logger.debug(f"Intent '{intent}' score: {score}")
        
        # Find the intent with the highest score
        max_score = 0
        best_intent = "general_query"  # Default intent
        
        for intent, score in intent_scores.items():
            if score > max_score:
                max_score = score
                best_intent = intent
        
        logger.debug(f"Final intent detection: {best_intent} (score: {max_score})")
        return best_intent
        
    def _extract_entities(self, query: str) -> List[str]:
        """
        Extract entities from the user's query using simple heuristics.
        
        Args:
            query: The user's query string
            
        Returns:
            A list of extracted entities
        """
        logger.debug("Extracting entities from query")
        
        # Remove common question words and stop words
        stop_words = set([
            "what", "when", "where", "who", "why", "how", "is", "are", "was", "were",
            "do", "does", "did", "can", "could", "would", "should", "the", "a", "an",
            "in", "on", "at", "to", "for", "with", "about", "from", "by", "and", 
            "or", "this", "that", "these", "those", "it", "they", "them", "i", "we", "you"
        ])
        
        # Tokenize the query and extract potential entities (nouns and noun phrases)
        words = re.findall(r'\b\w+\b', query.lower())
        logger.debug(f"Tokenized query into {len(words)} words")
        
        # Filter out stop words and short words
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
        logger.debug(f"After filtering stop words: {len(filtered_words)} remaining")
        
        # Extract potential noun phrases (consecutive capitalized words)
        noun_phrases = re.findall(r'\b([A-Z][a-z]+ )+[A-Z][a-z]+\b', query)
        if noun_phrases:
            logger.debug(f"Found {len(noun_phrases)} capitalized noun phrases")
        
        # Extract quoted phrases as entities
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        quoted_phrases += re.findall(r"'([^']+)'", query)
        if quoted_phrases:
            logger.debug(f"Found {len(quoted_phrases)} quoted phrases")
        
        # Combine all potential entities
        entities = filtered_words + noun_phrases + quoted_phrases
        
        # Remove duplicates and sort by length (longer entities first)
        unique_entities = list(set(entities))
        unique_entities.sort(key=len, reverse=True)
        
        # Limit to top 5 longest entities
        top_entities = unique_entities[:5] if unique_entities else []
        logger.debug(f"Final entities extracted: {top_entities}")
        
        return top_entities 