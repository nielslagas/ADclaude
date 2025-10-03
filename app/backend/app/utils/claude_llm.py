"""
Utilities for text generation using Anthropic's Claude models.
Designed as a drop-in replacement for Google Gemini.
"""
import os
import time
import logging
import random
from typing import Dict, List, Any, Optional

from anthropic import Anthropic
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Anthropic client
API_INITIALIZED = False
if settings.ANTHROPIC_API_KEY:
    try:
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        API_INITIALIZED = True
        logger.info("Anthropic Claude client initialized with provided API key")
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic client: {str(e)}")
        API_INITIALIZED = False
else:
    logger.warning("No Anthropic API key provided, Claude functionality will be limited")

# Create a class mimicking the structure of Google's GenerativeModel
class ClaudeModel:
    """
    A wrapper for Claude that mimics the interface of Google's GenerativeModel class.
    """
    def __init__(self, 
                model_name: str = "claude-3-5-haiku-20241022",
                safety_settings: Optional[Dict[str, str]] = None,
                generation_config: Optional[Dict[str, Any]] = None):
        """
        Initialize a Claude model with similar parameters to Google's GenerativeModel.
        
        Args:
            model_name: The Claude model to use (default: claude-3-5-haiku-20241022)
            safety_settings: Safety settings (ignored for Claude, but kept for API compatibility)
            generation_config: Generation settings like temperature, max_tokens, etc.
        """
        self.model_name = model_name
        self.safety_settings = safety_settings or {}
        
        # Default generation settings
        self.generation_config = {
            "temperature": 0.1,
            "max_tokens": 4096,
            "top_p": 0.95,
            "top_k": 40,
        }
        
        # Override defaults with any provided settings
        if generation_config:
            self.generation_config.update(generation_config)
            
        # Map Google's max_output_tokens to Claude's max_tokens
        if "max_output_tokens" in self.generation_config:
            self.generation_config["max_tokens"] = self.generation_config.pop("max_output_tokens")
            
        # Check that the Anthropic client is initialized
        if not API_INITIALIZED:
            raise ValueError("Anthropic API client is not initialized. Make sure ANTHROPIC_API_KEY is set.")
            
    def generate_content(self, prompt_parts):
        """
        Generate content using Claude, mimicking the interface of Google's generate_content.
        
        Args:
            prompt_parts: A list of messages in Google's format, each with 'role' and 'parts'
            
        Returns:
            A response object with a 'text' attribute containing the generated content
        """
        # Extract system message if present
        system_message = ""
        user_message = ""
        
        # Process prompt parts to convert to Claude's format
        for part in prompt_parts:
            if part["role"] == "system" and "parts" in part and len(part["parts"]) > 0:
                system_message = part["parts"][0]
            elif part["role"] == "user" and "parts" in part and len(part["parts"]) > 0:
                user_message = part["parts"][0]
                
        # Make sure we have a user message at minimum
        if not user_message:
            if len(prompt_parts) > 0 and isinstance(prompt_parts[0], str):
                # Handle direct string input
                user_message = prompt_parts[0]
            elif len(prompt_parts) > 0 and "parts" in prompt_parts[0]:
                # Handle other formats
                user_message = prompt_parts[0]["parts"][0]
            else:
                raise ValueError("No valid user message found in prompt")
                
        try:
            # Map generation config to Claude's parameters
            params = {
                "model": self.model_name,
                "max_tokens": self.generation_config.get("max_tokens", 4096),
                "temperature": self.generation_config.get("temperature", 0.1),
                "top_p": self.generation_config.get("top_p", 0.95),
                "messages": [{"role": "user", "content": user_message}]
            }
            
            # Add system message if provided
            if system_message:
                params["system"] = system_message
                
            # Call the Claude API
            response = client.messages.create(**params)
            
            # Create a response object mimicking Google's API
            class ClaudeResponse:
                def __init__(self, text):
                    self.text = text
                    self.prompt_feedback = None
                    
            # Extract text from Claude's response
            if response and hasattr(response, "content") and len(response.content) > 0:
                content_text = "".join([block.text for block in response.content if hasattr(block, "text")])
                return ClaudeResponse(content_text)
            else:
                return ClaudeResponse("")
                
        except Exception as e:
            logger.error(f"Error generating content with Claude: {str(e)}")
            
            # Check if this is an overloaded error (529) or other API error
            error_message = str(e)
            is_overloaded = "529" in error_message or "overloaded" in error_message.lower()
            
            if is_overloaded:
                logger.warning("Claude API is currently overloaded, raising exception for retry")
                # Raise the exception so it can be caught and handled appropriately
                raise e
            
            # Create a fallback response for other errors
            class FallbackResponse:
                def __init__(self, error_message):
                    self.text = f"Op basis van de beschikbare documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst."
                    self.prompt_feedback = None
                    class BlockReason:
                        def __init__(self):
                            self.block_reason = None
                    self.prompt_feedback = BlockReason()
                    
            return FallbackResponse(str(e))
            
# Function to configure the module (similar to genai.configure)
def configure(api_key=None):
    """
    Configure the Claude client with the provided API key.
    """
    global API_INITIALIZED, client
    
    if api_key:
        try:
            client = Anthropic(api_key=api_key)
            API_INITIALIZED = True
            logger.info("Anthropic Claude client configured with provided API key")
        except Exception as e:
            logger.error(f"Failed to configure Anthropic client: {str(e)}")
            API_INITIALIZED = False
    else:
        logger.warning("No API key provided to configure Claude client")
        
# Export GenerativeModel class with a different name to match Google's API
GenerativeModel = ClaudeModel