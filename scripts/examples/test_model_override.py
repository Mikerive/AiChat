#!/usr/bin/env python3
"""Test the model override to GPT-4o-mini"""

from aichat.backend.services.llm.model_config import model_config

print('=== UPDATED MODEL CONFIGURATION ===')
print(model_config.get_cost_summary())
print()

default = model_config.get_default_model()
if default:
    print(f'New default model: {default.name}')
    print(f'Cost: ${default.cost_per_1m_tokens}/1M tokens')
    print(f'Provider: {default.provider.value}')
    print(f'Available: {"YES" if model_config._is_provider_available(default.provider) else "NO - missing API key"}')
else:
    print('No default model available - missing API keys?')

print()
print('Available models:')
for key, model in model_config.get_available_models().items():
    cost = f"${model.cost_per_1m_tokens}/1M" if model.cost_per_1m_tokens > 0 else "FREE"
    print(f"  {key}: {model.name} ({cost})")