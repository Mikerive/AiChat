"""
Centralized LLM Model Configuration

This module provides a single source of truth for all LLM model selection,
avoiding the chaos of models scattered across multiple services.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars only

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Available model providers"""
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    TOGETHER = "together"


class ModelTier(Enum):
    """Model cost tiers"""
    FREE = "free"           # $0/1M tokens
    CHEAP = "cheap"         # <$1/1M tokens  
    BUDGET = "budget"       # $1-5/1M tokens
    EXPENSIVE = "expensive" # >$5/1M tokens (AVOID!)


@dataclass
class ModelSpec:
    """Model specification with cost and capability info"""
    name: str
    provider: ModelProvider
    tier: ModelTier
    cost_per_1m_tokens: float
    context_length: int
    supports_tools: bool = True
    description: str = ""


class CentralizedModelConfig:
    """Single source of truth for all model configurations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define all available models in order of preference
        self._models = {
            # FREE TIER - Always use these first!
            "openrouter-dolphin-free": ModelSpec(
                name="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                provider=ModelProvider.OPENROUTER,
                tier=ModelTier.FREE,
                cost_per_1m_tokens=0.0,
                context_length=32768,
                supports_tools=True,
                description="Free Dolphin Mistral model - primary choice"
            ),
            "openrouter-llama-free": ModelSpec(
                name="meta-llama/llama-3.2-3b-instruct:free",
                provider=ModelProvider.OPENROUTER,
                tier=ModelTier.FREE,
                cost_per_1m_tokens=0.0,
                context_length=8192,
                supports_tools=True,
                description="Free Llama 3.2 model - backup choice"
            ),
            
            # CHEAP TIER - Use if free models unavailable
            "openai-mini": ModelSpec(
                name="gpt-4o-mini",
                provider=ModelProvider.OPENAI,
                tier=ModelTier.CHEAP,
                cost_per_1m_tokens=0.15,
                context_length=128000,
                supports_tools=True,
                description="Cheapest OpenAI model"
            ),
            "openai-3.5": ModelSpec(
                name="gpt-3.5-turbo",
                provider=ModelProvider.OPENAI,
                tier=ModelTier.CHEAP,
                cost_per_1m_tokens=0.50,
                context_length=16384,
                supports_tools=True,
                description="Budget OpenAI model"
            ),
            
            # EXPENSIVE TIER - AVOID THESE!
            # "claude-haiku": ModelSpec(
            #     name="claude-3-haiku-20240307",
            #     provider=ModelProvider.ANTHROPIC,
            #     tier=ModelTier.EXPENSIVE,
            #     cost_per_1m_tokens=0.25,
            #     context_length=200000,
            #     description="DISABLED - Too expensive!"
            # ),
        }
        
        # Model selection priority (cheapest first)
        self._priority_order = [
            "openrouter-dolphin-free",  # FREE
            "openrouter-llama-free",    # FREE
            "openai-mini",              # CHEAP
            "openai-3.5",               # CHEAP
        ]
        
        # Load configuration from environment
        self._load_env_config()
    
    def _load_env_config(self):
        """Load model preferences from environment variables"""
        # Allow environment override of default model
        env_model = os.getenv("DEFAULT_LLM_MODEL")
        if env_model and env_model in self._models:
            # Move env model to front of priority list
            if env_model in self._priority_order:
                self._priority_order.remove(env_model)
            self._priority_order.insert(0, env_model)
            self.logger.info(f"Environment override: prioritizing {env_model}")
    
    def get_default_model(self) -> Optional[ModelSpec]:
        """Get the highest priority available model"""
        for model_key in self._priority_order:
            model = self._models.get(model_key)
            if model and self._is_provider_available(model.provider):
                self.logger.info(f"Selected default model: {model.name} (${model.cost_per_1m_tokens}/1M tokens)")
                return model
        
        self.logger.error("No LLM models available - check API keys")
        return None
    
    def get_model_by_key(self, key: str) -> Optional[ModelSpec]:
        """Get a specific model by key"""
        return self._models.get(key)
    
    def get_models_by_tier(self, tier: ModelTier) -> List[ModelSpec]:
        """Get all models in a specific cost tier"""
        return [model for model in self._models.values() if model.tier == tier]
    
    def get_free_models(self) -> List[ModelSpec]:
        """Get all free models"""
        return self.get_models_by_tier(ModelTier.FREE)
    
    def get_available_models(self) -> Dict[str, ModelSpec]:
        """Get all models with available providers"""
        available = {}
        for key, model in self._models.items():
            if self._is_provider_available(model.provider):
                available[key] = model
        return available
    
    def _is_provider_available(self, provider: ModelProvider) -> bool:
        """Check if a provider has required API keys"""
        env_keys = {
            ModelProvider.OPENROUTER: "OPENROUTER_API_KEY",
            ModelProvider.OPENAI: "OPENAI_API_KEY", 
            ModelProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            ModelProvider.GROQ: "GROQ_API_KEY",
            ModelProvider.TOGETHER: "TOGETHER_API_KEY",
        }
        
        key_name = env_keys.get(provider)
        if not key_name:
            return False
            
        return bool(os.getenv(key_name))
    
    def get_cost_summary(self) -> str:
        """Get a summary of model costs"""
        available = self.get_available_models()
        if not available:
            return "No models available"
        
        summary = ["Available models (in priority order):"]
        for key in self._priority_order:
            if key in available:
                model = available[key]
                cost = f"${model.cost_per_1m_tokens}/1M" if model.cost_per_1m_tokens > 0 else "FREE"
                summary.append(f"  {model.name} ({cost})")
        
        return "\n".join(summary)


# Global instance - single source of truth
model_config = CentralizedModelConfig()


def get_default_model() -> Optional[ModelSpec]:
    """Convenience function to get default model"""
    return model_config.get_default_model()


def get_model(key: str) -> Optional[ModelSpec]:
    """Convenience function to get specific model"""
    return model_config.get_model_by_key(key)