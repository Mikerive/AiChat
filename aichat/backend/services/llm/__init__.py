"""
LLM Services Package

Provides multiple AI/LLM service implementations:
- OpenRouterService: Traditional OpenRouter API integration
- PydanticAIService: Modern PydanticAI with function tools
- UnifiedLLMService: Orchestrates multiple providers with intelligent routing

Features:
- Function tools (emotion control, voice settings, memory)
- Multiple AI providers (OpenAI, Anthropic, OpenRouter)
- Streaming responses
- Conversation memory
- Automatic fallbacks
"""

from .openrouter_service import OpenRouterService
from .pydantic_ai_service import PydanticAIService
from .unified_llm_service import UnifiedLLMService, LLMProvider

__all__ = ["OpenRouterService", "PydanticAIService", "UnifiedLLMService", "LLMProvider"]
