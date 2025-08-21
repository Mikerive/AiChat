"""
OpenRouter Service for LLM Processing according to the flow diagram
"""

import logging
import os
from typing import Any, Dict, List, Optional

# Local imports
from aichat.core.event_system import EventSeverity, EventType, get_event_system

import aiohttp

# Add parent directory to path for imports

logger = logging.getLogger(__name__)


class OpenRouterService:
    """Service for handling LLM requests through OpenRouter"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.event_system = get_event_system()
        self.default_model = "anthropic/claude-3-haiku"
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://vtuber-miku-app.local",
                "X-Title": "VTuber Miku Chat App",
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def generate_response(
        self,
        message: str,
        character_name: str,
        character_personality: str,
        character_profile: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Generate character response using OpenRouter LLM"""
        try:
            if not self.api_key:
                logger.warning(
                    "OpenRouter API key not configured, using fallback response"
                )
                return await self._generate_fallback_response(
                    message, character_name, character_personality
                )

            # Build character context
            system_prompt = self._build_character_prompt(
                character_name, character_personality, character_profile
            )

            # Prepare request
            model_name = model or self.default_model
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Emit processing event
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Sending request to OpenRouter LLM ({model_name})",
                {
                    "character": character_name,
                    "model": model_name,
                    "message_length": len(message),
                },
            )

            # Make API request
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/chat/completions", json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    # Extract response
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]

                        # Extract emotion from response (simple pattern matching)
                        emotion = self._extract_emotion(content)

                        # Clean up the response
                        cleaned_response = self._clean_response(content)

                        # Emit success event
                        await self.event_system.emit(
                            EventType.CHAT_RESPONSE,
                            f"LLM response generated successfully",
                            {
                                "character": character_name,
                                "model": model_name,
                                "response_length": len(cleaned_response),
                                "emotion": emotion,
                                "tokens_used": result.get("usage", {}).get(
                                    "total_tokens", 0
                                ),
                            },
                        )

                        return {
                            "response": cleaned_response,
                            "emotion": emotion,
                            "model_used": model_name,
                            "tokens_used": result.get("usage", {}).get(
                                "total_tokens", 0
                            ),
                            "success": True,
                        }
                    else:
                        raise ValueError("No response content in API result")

                else:
                    error_text = await response.text()
                    logger.error(
                        f"OpenRouter API error {response.status}: {error_text}"
                    )

                    # Emit error event
                    await self.event_system.emit(
                        EventType.ERROR_OCCURRED,
                        f"OpenRouter API error: {response.status}",
                        {"status_code": response.status, "error": error_text},
                        EventSeverity.ERROR,
                    )

                    # Return fallback response
                    return await self._generate_fallback_response(
                        message, character_name, character_personality
                    )

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")

            # Emit error event
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"LLM processing error: {str(e)}",
                {"character": character_name, "error": str(e)},
                EventSeverity.ERROR,
            )

            # Return fallback response
            return await self._generate_fallback_response(
                message, character_name, character_personality
            )

    def _build_character_prompt(
        self, character_name: str, personality: str, profile: str
    ) -> str:
        """Build character-specific system prompt"""
        personality_traits = personality.split(",") if personality else []

        prompt = f"""You are {character_name}, a virtual character with the following traits:

Personality: {', '.join(trait.strip() for trait in personality_traits)}
Profile: {profile}

Please respond as {character_name} would, staying true to the character's personality and background.
Keep responses conversational and engaging, typically 1-3 sentences unless more detail is needed.
Show emotion and personality in your responses.

Remember:
- Stay in character at all times
- Be friendly and engaging
- Match the personality traits listed above
- Respond naturally as if you're having a real conversation"""

        if character_name.lower() == "hatsune_miku":
            prompt += "\n- You are the famous virtual singer Hatsune Miku, known for your cheerful and energetic personality"

        return prompt

    def _extract_emotion(self, response: str) -> str:
        """Extract emotion from response text using simple pattern matching"""
        response_lower = response.lower()

        # Emotion patterns
        if any(
            word in response_lower
            for word in ["happy", "excited", "joy", "great", "awesome", "wonderful"]
        ):
            return "happy"
        elif any(
            word in response_lower for word in ["sad", "sorry", "disappointed", "upset"]
        ):
            return "sad"
        elif any(
            word in response_lower for word in ["angry", "mad", "frustrated", "annoyed"]
        ):
            return "angry"
        elif any(
            word in response_lower
            for word in ["surprised", "wow", "amazing", "incredible"]
        ):
            return "surprised"
        elif any(
            word in response_lower
            for word in ["confused", "don't understand", "not sure", "unclear"]
        ):
            return "confused"
        elif any(
            word in response_lower for word in ["calm", "peaceful", "relaxed", "serene"]
        ):
            return "calm"
        else:
            return "neutral"

    def _clean_response(self, response: str) -> str:
        """Clean up response text"""
        # Remove common AI response patterns
        cleaned = response.strip()

        # Remove excessive line breaks
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")

        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in cleaned.split("\n")]
        cleaned = "\n".join(line for line in lines if line)

        return cleaned

    async def _generate_fallback_response(
        self, message: str, character_name: str, personality: str
    ) -> Dict[str, Any]:
        """Generate fallback response when OpenRouter is unavailable"""
        try:
            personality_traits = personality.split(",") if personality else ["friendly"]

            # Simple response patterns based on personality
            responses = {
                "cheerful": [
                    f"That's wonderful! I'm so glad to hear about that!",
                    f"Yay! That sounds amazing!",
                    f"Awesome! I love hearing good news!",
                ],
                "curious": [
                    f"That's interesting! Tell me more about that.",
                    f"I'd love to learn more! What do you think?",
                    f"Fascinating! Can you explain more?",
                ],
                "helpful": [
                    f"I'm here to help! How can I assist you?",
                    f"Let me help you with that. What would you like to know?",
                    f"I'd be happy to help you. What do you need?",
                ],
            }

            # Select response based on personality
            response_text = (
                "I'm not sure how to respond to that, but I'm happy to chat with you!"
            )
            for trait in personality_traits:
                trait = trait.strip().lower()
                if trait in responses:
                    import random

                    response_text = random.choice(responses[trait])
                    break

            # Add character-specific greeting
            if character_name.lower() == "hatsune_miku":
                response_text = f"Hello! I'm Hatsune Miku! {response_text}"

            return {
                "response": response_text,
                "emotion": "neutral",
                "model_used": "fallback_local",
                "tokens_used": 0,
                "success": False,
            }

        except Exception as e:
            logger.error(f"Error generating fallback response: {e}")
            return {
                "response": "I'm having trouble responding right now. Please try again later.",
                "emotion": "confused",
                "model_used": "error",
                "tokens_used": 0,
                "success": False,
            }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from OpenRouter"""
        try:
            if not self.api_key:
                return []

            session = await self._get_session()
            async with session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("data", [])
                else:
                    logger.error(f"Error fetching models: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        try:
            models = await self.get_available_models()
            for model in models:
                if model.get("id") == model_id:
                    return model
            return None

        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
