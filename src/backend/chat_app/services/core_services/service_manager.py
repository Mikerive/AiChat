"""
Service manager with dependency injection pattern for flexible service management
"""

import logging
import time
from typing import Optional, Dict, Any, Callable, TypeVar
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ServiceConfig:
    """Base configuration for services"""
    # Make name optional with a sensible default so callers can omit it.
    name: str = ""
    singleton: bool = True
    max_idle_time: int = 3600  # 1 hour
    cleanup_on_dispose: bool = True


@dataclass
class WhisperConfig(ServiceConfig):
    """Configuration for Whisper service"""
    model_name: str = "base"
    device: str = "cpu"
    mock: bool = False
    
    def __post_init__(self):
        # If no explicit name supplied, derive a default
        if not getattr(self, "name", None):
            self.name = f"whisper_{self.model_name}_{self.device}"


@dataclass
class VoiceConfig(ServiceConfig):
    """Configuration for Voice service"""
    piper_model_path: Optional[str] = None
    
    def __post_init__(self):
        if not getattr(self, "name", None):
            self.name = "voice_service"


class ServiceFactory:
    """Factory for creating services with dependency injection"""
    
    def __init__(self):
        self._service_cache: Dict[str, Any] = {}
        self._service_metadata: Dict[str, Dict[str, Any]] = {}
        self._factory_functions: Dict[str, Callable] = {}
        
        # Register default factory functions
        self._register_default_factories()
    
    def _register_default_factories(self):
        """Register default service factory functions"""
        self._factory_functions.update({
            'whisper': self._create_whisper_service,
            'voice': self._create_voice_service,
            'chat': self._create_chat_service,
            'piper_tts': self._create_piper_tts_service,
            'openrouter': self._create_openrouter_service,
            'tts_finetune': self._create_tts_finetune_service,
        })
    
    def get_service(self, service_type: str, config: ServiceConfig = None) -> Any:
        """Get or create a service with dependency injection"""
        if config is None:
            config = self._get_default_config(service_type)
        
        cache_key = self._get_cache_key(service_type, config)
        
        # Return cached service if singleton and exists
        if config.singleton and cache_key in self._service_cache:
            self._update_last_used(cache_key)
            return self._service_cache[cache_key]
        
        # Create new service instance
        service = self._create_service(service_type, config)
        
        # Cache if singleton
        if config.singleton:
            self._service_cache[cache_key] = service
            self._service_metadata[cache_key] = {
                'config': config,
                'created_at': time.time(),
                'last_used': time.time(),
                'service_type': service_type
            }
        
        logger.info(f"Created {service_type} service with config: {config.name}")
        return service
    
    def create_service(self, service_type: str, config: ServiceConfig = None) -> Any:
        """Always create a new service instance (never cached)"""
        if config is None:
            config = self._get_default_config(service_type)
        
        config.singleton = False  # Force non-singleton behavior
        return self._create_service(service_type, config)
    
    def _create_service(self, service_type: str, config: ServiceConfig) -> Any:
        """Create service instance using factory function"""
        if service_type not in self._factory_functions:
            raise ValueError(f"Unknown service type: {service_type}")
        
        factory_func = self._factory_functions[service_type]
        return factory_func(config)
    
    def _create_whisper_service(self, config: WhisperConfig):
        """Factory function for WhisperService"""
        from ..stt_services.whisper_service import WhisperService
        return WhisperService(model_name=config.model_name)
    
    def _create_voice_service(self, config: VoiceConfig):
        """Factory function for VoiceService"""
        from .voice_service import VoiceService
        return VoiceService()
    
    def _create_chat_service(self, config: ServiceConfig):
        """Factory function for ChatService"""
        from .chat_service import ChatService
        return ChatService()
    
    def _create_piper_tts_service(self, config: ServiceConfig):
        """Factory function for PiperTTSService"""
        from ..tts_services.piper_tts_service import PiperTTSService
        return PiperTTSService()
    
    def _create_openrouter_service(self, config: ServiceConfig):
        """Factory function for OpenRouterService"""
        from ..llm_services.openrouter_service import OpenRouterService
        return OpenRouterService()
    
    def _create_tts_finetune_service(self, config: ServiceConfig):
        """Factory function for TTSFinetuneService"""
        from ..tts_services.tts_finetune_service import TTSFinetuneService
        return TTSFinetuneService()
    
    def _get_default_config(self, service_type: str) -> ServiceConfig:
        """Get default configuration for service type"""
        defaults = {
            'whisper': WhisperConfig(name="whisper_default"),
            'voice': VoiceConfig(name="voice_default"),
            'chat': ServiceConfig(name="chat_default"),
            'piper_tts': ServiceConfig(name="piper_tts_default"),
            'openrouter': ServiceConfig(name="openrouter_default"),
            'tts_finetune': ServiceConfig(name="tts_finetune_default"),
        }
        
        if service_type not in defaults:
            return ServiceConfig(name=f"{service_type}_default")
        
        return defaults[service_type]
    
    def _get_cache_key(self, service_type: str, config: ServiceConfig) -> str:
        """Generate cache key for service"""
        return f"{service_type}_{config.name}"
    
    def _update_last_used(self, cache_key: str):
        """Update last used timestamp for service"""
        if cache_key in self._service_metadata:
            self._service_metadata[cache_key]['last_used'] = time.time()
    
    def cleanup_unused_services(self, max_idle_time: Optional[int] = None):
        """Clean up services that haven't been used recently"""
        current_time = time.time()
        to_remove = []
        
        for cache_key, metadata in self._service_metadata.items():
            idle_time = max_idle_time or metadata['config'].max_idle_time
            if current_time - metadata['last_used'] > idle_time:
                to_remove.append(cache_key)
        
        for cache_key in to_remove:
            service = self._service_cache.pop(cache_key)
            metadata = self._service_metadata.pop(cache_key)
            
            # Call cleanup if service supports it
            if metadata['config'].cleanup_on_dispose and hasattr(service, 'cleanup'):
                try:
                    service.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up service {cache_key}: {e}")
            
            logger.info(f"Cleaned up unused service: {cache_key}")
    
    def reset_services(self):
        """Reset all services (useful for testing)"""
        logger.warning("Resetting all services")
        
        for cache_key, service in self._service_cache.items():
            if hasattr(service, 'cleanup'):
                try:
                    service.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up service during reset {cache_key}: {e}")
        
        self._service_cache.clear()
        self._service_metadata.clear()
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all managed services"""
        current_time = time.time()
        services_info = []
        
        for cache_key, metadata in self._service_metadata.items():
            services_info.append({
                'cache_key': cache_key,
                'service_type': metadata['service_type'],
                'config_name': metadata['config'].name,
                'created_at': metadata['created_at'],
                'last_used': metadata['last_used'],
                'idle_time': current_time - metadata['last_used'],
                'is_singleton': metadata['config'].singleton
            })
        
        return {
            'total_services': len(self._service_cache),
            'services': services_info,
            'factory_types': list(self._factory_functions.keys())
        }


# Global service factory instance
_service_factory: Optional[ServiceFactory] = None


def get_service_factory() -> ServiceFactory:
    """Get the global service factory instance"""
    global _service_factory
    if _service_factory is None:
        _service_factory = ServiceFactory()
        logger.info("Service Factory initialized with dependency injection")
    return _service_factory


# Convenience functions for common services
def get_whisper_service(model_name: str = "base", device: str = "cpu") -> Any:
    """Get WhisperService with optional configuration"""
    config = WhisperConfig(model_name=model_name, device=device)
    return get_service_factory().get_service('whisper', config)


def get_voice_service() -> Any:
    """Get VoiceService with default configuration"""
    return get_service_factory().get_service('voice')


def get_chat_service() -> Any:
    """Get ChatService with default configuration"""
    return get_service_factory().get_service('chat')


def get_piper_tts_service() -> Any:
    """Get PiperTTSService with default configuration"""
    return get_service_factory().get_service('piper_tts')


def get_openrouter_service() -> Any:
    """Get OpenRouterService with default configuration"""
    return get_service_factory().get_service('openrouter')


def get_tts_finetune_service() -> Any:
    """Get TTSFinetuneService with default configuration"""
    return get_service_factory().get_service('tts_finetune')