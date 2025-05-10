"""
Utilities for text generation using OpenAI models.
Designed as a drop-in replacement for Google Gemini.
"""
import os
import time
import logging
import random
from typing import Dict, List, Any, Optional

from openai import OpenAI
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI client
API_INITIALIZED = False
if settings.OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        API_INITIALIZED = True
        logger.info("OpenAI client initialized with provided API key")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        API_INITIALIZED = False
else:
    logger.warning("No OpenAI API key provided, API functionality will be limited")

# Create a class mimicking the structure of Google's GenerativeModel
class OpenAIModel:
    """
    A wrapper for OpenAI that mimics the interface of Google's GenerativeModel class.
    """
    def __init__(self, 
                model_name: str = "gpt-4o",
                safety_settings: Optional[Dict[str, str]] = None,
                generation_config: Optional[Dict[str, Any]] = None):
        """
        Initialize an OpenAI model with similar parameters to Google's GenerativeModel.
        
        Args:
            model_name: The OpenAI model to use (default: gpt-4o)
            safety_settings: Safety settings (ignored for OpenAI, but kept for API compatibility)
            generation_config: Generation settings like temperature, max_tokens, etc.
        """
        self.model_name = model_name
        self.safety_settings = safety_settings or {}
        
        # Default generation settings
        self.generation_config = {
            "temperature": 0.1,
            "max_tokens": 4096,
            "top_p": 0.95,
        }
        
        # Override defaults with any provided settings
        if generation_config:
            self.generation_config.update(generation_config)
            
        # Map Google's max_output_tokens to OpenAI's max_tokens
        if "max_output_tokens" in self.generation_config:
            self.generation_config["max_tokens"] = self.generation_config.pop("max_output_tokens")
            
        # Check that the OpenAI client is initialized
        if not API_INITIALIZED:
            raise ValueError("OpenAI API client is not initialized. Make sure OPENAI_API_KEY is set.")
            
    def generate_content(self, prompt_parts):
        """
        Generate content using OpenAI, mimicking the interface of Google's generate_content.
        
        Args:
            prompt_parts: A list of messages in Google's format, each with 'role' and 'parts'
            
        Returns:
            A response object with a 'text' attribute containing the generated content
        """
        # Convert Google's prompt format to OpenAI's
        messages = []
        
        # Process prompt parts
        for part in prompt_parts:
            if "role" in part and "parts" in part and len(part["parts"]) > 0:
                # Map Google roles to OpenAI roles
                role = part["role"]
                if role == "user":
                    openai_role = "user"
                elif role == "system":
                    openai_role = "system"
                else:
                    openai_role = "assistant"  # Default
                
                # Add message
                messages.append({
                    "role": openai_role,
                    "content": part["parts"][0]
                })
                
        # Handle case where prompt_parts is just a string
        if not messages and len(prompt_parts) > 0 and isinstance(prompt_parts[0], str):
            messages.append({
                "role": "user",
                "content": prompt_parts[0]
            })
            
        # Ensure we have at least one message
        if not messages:
            raise ValueError("No valid messages found in prompt")
            
        try:
            # Map generation config to OpenAI's parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": self.generation_config.get("max_tokens", 4096),
                "temperature": self.generation_config.get("temperature", 0.1),
                "top_p": self.generation_config.get("top_p", 0.95),
            }
            
            # Call the OpenAI API
            response = client.chat.completions.create(**params)
            
            # Create a response object mimicking Google's API
            class OpenAIResponse:
                def __init__(self, text):
                    self.text = text
                    self.prompt_feedback = None
                    
            # Extract text from OpenAI's response
            if response and response.choices and len(response.choices) > 0:
                content_text = response.choices[0].message.content
                return OpenAIResponse(content_text)
            else:
                return OpenAIResponse("")
                
        except Exception as e:
            logger.error(f"Error generating content with OpenAI: {str(e)}")
            
            # Create a fallback response
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
    Configure the OpenAI client with the provided API key.
    """
    global API_INITIALIZED, client
    
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            API_INITIALIZED = True
            logger.info("OpenAI client configured with provided API key")
        except Exception as e:
            logger.error(f"Failed to configure OpenAI client: {str(e)}")
            API_INITIALIZED = False
    else:
        logger.warning("No API key provided to configure OpenAI client")
        
# Export GenerativeModel class with a different name to match Google's API
GenerativeModel = OpenAIModel