"""
Unified LLM Service - Orchestrates multiple AI providers and services
"""

import logging
from typing import Any, Dict, List, Optional, AsyncIterator, Union
from enum import Enum

from aichat.core.event_system import EventSeverity, EventType, get_event_system
from .openrouter_service import OpenRouterService
from .pydantic_ai_service import PydanticAIService

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers"""

    PYDANTIC_AI = "pydantic_ai"
    OPENROUTER = "openrouter"
    AUTO = "auto"


class UnifiedLLMService:
    """
    Unified service that manages multiple LLM providers with intelligent routing

    Features:
    - Automatic provider selection based on availability and request type
    - Fallback chain for reliability
    - Function tools and memory (via PydanticAI)
    - Multiple AI model support (OpenAI, Anthropic, OpenRouter)
    - Streaming responses
    - Enhanced error handling
    """

    def __init__(
        self,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        openrouter_key: Optional[str] = None,
    ):

        self.event_system = get_event_system()

        # Initialize services
        self.pydantic_ai = PydanticAIService(
            openai_key=openai_key,
            anthropic_key=anthropic_key,
            openrouter_key=openrouter_key,
        )
        self.openrouter = OpenRouterService(api_key=openrouter_key)

        # Provider priority (first available wins)
        self.provider_priority = [LLMProvider.PYDANTIC_AI, LLMProvider.OPENROUTER]

    async def generate_response(
        self,
        message: str,
        character_name: str,
        character_personality: str,
        character_profile: str,
        provider: LLMProvider = LLMProvider.AUTO,
        model: Optional[str] = None,
        use_tools: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate character response using the best available provider

        Args:
            message: User input message
            character_name: Character name for roleplay
            character_personality: Character personality traits
            character_profile: Character background/profile
            provider: Specific provider to use (AUTO for intelligent selection)
            model: Specific model to use
            use_tools: Whether to enable function tools (emotions, memory, etc.)
            **kwargs: Additional parameters
        """

        try:
            # Emit start event
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Generating response for {character_name}",
                {
                    "character": character_name,
                    "provider": provider.value,
                    "use_tools": use_tools,
                    "message_length": len(message),
                },
            )

            # Select provider
            selected_provider = await self._select_provider(provider, use_tools, model)

            # Generate response with selected provider
            if selected_provider == LLMProvider.PYDANTIC_AI:
                result = await self.pydantic_ai.generate_response(
                    message,
                    character_name,
                    character_personality,
                    character_profile,
                    model,
                    **kwargs,
                )
                result["provider_used"] = "pydantic_ai"

            elif selected_provider == LLMProvider.OPENROUTER:
                if use_tools:
                    # Use enhanced OpenRouter with PydanticAI fallback
                    result = await self.openrouter.generate_enhanced_response(
                        message,
                        character_name,
                        character_personality,
                        character_profile,
                        use_pydantic_ai=True,
                        model=model,
                        **kwargs,
                    )
                else:
                    # Use traditional OpenRouter
                    result = await self.openrouter.generate_response(
                        message,
                        character_name,
                        character_personality,
                        character_profile,
                        model,
                        **kwargs,
                    )
                result["provider_used"] = "openrouter"

            else:
                # Should not reach here, but fallback
                result = await self._generate_fallback_response(
                    message, character_name, character_personality
                )
                result["provider_used"] = "fallback"

            # Emit success event
            await self.event_system.emit(
                EventType.CHAT_RESPONSE,
                f"Response generated successfully",
                {
                    "character": character_name,
                    "provider": result.get("provider_used"),
                    "model": result.get("model_used"),
                    "success": result.get("success", True),
                    "response_length": len(result.get("response", "")),
                    "emotion": result.get("emotion"),
                },
            )

            return result

        except Exception as e:
            logger.error(f"Error in unified LLM generation: {e}")

            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Unified LLM error: {str(e)}",
                {
                    "character": character_name,
                    "provider": provider.value,
                    "error": str(e),
                },
                EventSeverity.ERROR,
            )

            # Final fallback
            return await self._generate_fallback_response(
                message, character_name, character_personality
            )

    async def generate_streaming_response(
        self,
        message: str,
        character_name: str,
        character_personality: str,
        character_profile: str,
        provider: LLMProvider = LLMProvider.AUTO,
        model: Optional[str] = None,
        use_tools: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate streaming response"""

        try:
            selected_provider = await self._select_provider(provider, use_tools, model)

            # Emit start event
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Starting streaming response for {character_name}",
                {
                    "character": character_name,
                    "provider": selected_provider.value,
                    "streaming": True,
                },
            )

            if selected_provider == LLMProvider.PYDANTIC_AI:
                async for chunk in self.pydantic_ai.generate_streaming_response(
                    message,
                    character_name,
                    character_personality,
                    character_profile,
                    model,
                ):
                    chunk["provider_used"] = "pydantic_ai"
                    yield chunk

            elif selected_provider == LLMProvider.OPENROUTER:
                async for chunk in self.openrouter.generate_streaming_response(
                    message,
                    character_name,
                    character_personality,
                    character_profile,
                    model,
                ):
                    chunk["provider_used"] = "openrouter"
                    yield chunk

            else:
                # Non-streaming fallback
                result = await self._generate_fallback_response(
                    message, character_name, character_personality
                )
                result["provider_used"] = "fallback"
                result["final"] = True
                yield result

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            yield {
                "response": f"Error in streaming: {str(e)}",
                "emotion": "confused",
                "provider_used": "error",
                "final": True,
            }

    async def _select_provider(
        self, preferred: LLMProvider, use_tools: bool, model: Optional[str]
    ) -> LLMProvider:
        """Select the best provider based on preferences and availability"""

        if preferred != LLMProvider.AUTO:
            # Use specific provider if requested
            if await self._is_provider_available(preferred, model):
                return preferred
            else:
                logger.warning(
                    f"Requested provider {preferred} not available, falling back"
                )

        # Auto-selection logic
        for provider in self.provider_priority:
            if await self._is_provider_available(provider, model):
                # Prefer PydanticAI for tool usage
                if use_tools and provider == LLMProvider.PYDANTIC_AI:
                    return provider
                # Use first available otherwise
                return provider

        # No providers available - this should trigger fallback response
        return LLMProvider.OPENROUTER  # Will use enhanced fallback

    async def _is_provider_available(
        self, provider: LLMProvider, model: Optional[str]
    ) -> bool:
        """Check if a provider is available and configured"""

        try:
            if provider == LLMProvider.PYDANTIC_AI:
                available_models = await self.pydantic_ai.get_available_models()
                if available_models:
                    if model:
                        return model in available_models
                    return True
                return False

            elif provider == LLMProvider.OPENROUTER:
                # Check if OpenRouter is configured
                return bool(self.openrouter.api_key)

        except Exception as e:
            logger.error(f"Error checking provider {provider} availability: {e}")

        return False

    async def get_available_models(
        self, provider: Optional[LLMProvider] = None
    ) -> Dict[str, List[str]]:
        """Get available models from all or specific provider"""

        models = {}

        try:
            if provider is None or provider == LLMProvider.PYDANTIC_AI:
                models["pydantic_ai"] = await self.pydantic_ai.get_available_models()

            if provider is None or provider == LLMProvider.OPENROUTER:
                openrouter_models = await self.openrouter.get_available_models()
                models["openrouter"] = [
                    model.get("id", "") for model in openrouter_models
                ]

        except Exception as e:
            logger.error(f"Error getting available models: {e}")

        return models

    async def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers"""

        status = {}

        # PydanticAI status
        try:
            pydantic_models = await self.pydantic_ai.get_available_models()
            status["pydantic_ai"] = {
                "available": len(pydantic_models) > 0,
                "models": pydantic_models,
                "features": ["function_tools", "memory", "streaming", "emotions"],
            }
        except Exception as e:
            status["pydantic_ai"] = {
                "available": False,
                "error": str(e),
                "features": [],
            }

        # OpenRouter status
        try:
            openrouter_configured = bool(self.openrouter.api_key)
            status["openrouter"] = {
                "available": openrouter_configured,
                "api_key_configured": openrouter_configured,
                "features": ["multiple_models", "large_context"],
            }
        except Exception as e:
            status["openrouter"] = {"available": False, "error": str(e), "features": []}

        return status

    async def _generate_fallback_response(
        self, message: str, character_name: str, personality: str
    ) -> Dict[str, Any]:
        """Ultimate fallback when all providers fail"""

        responses = [
            f"I'm having trouble processing that right now, but I'm here to chat with you!",
            f"My AI systems are having a moment, but I'm still listening!",
            f"Technical difficulties on my end, but I appreciate you talking with me!",
        ]

        import random

        response_text = random.choice(responses)

        if character_name.lower() == "hatsune_miku":
            response_text = f"Hello! I'm Hatsune Miku! {response_text}"

        return {
            "response": response_text,
            "emotion": "apologetic",
            "model_used": "unified_fallback",
            "success": False,
            "provider_used": "fallback",
        }

    async def close(self):
        """Cleanup all services"""
        await self.pydantic_ai.close()
        await self.openrouter.close()

    # Convenience methods for backward compatibility
    async def generate_character_response(self, *args, **kwargs):
        """Alias for generate_response for backward compatibility"""
        return await self.generate_response(*args, **kwargs)
