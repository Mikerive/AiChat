"""
Proper Dependency Injection Container

Replaces singleton-based service factory with true dependency injection.
Supports:
- Constructor injection
- Interface/protocol binding
- Scoped lifetimes (singleton, transient, scoped)
- Easy testing and mocking
- Explicit dependency declarations
"""

import logging
import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, Type, TypeVar, Union
from dataclasses import dataclass
import inspect

logger = logging.getLogger(__name__)

T = TypeVar('T')

class Lifetime(Enum):
    """Service lifetime management"""
    SINGLETON = "singleton"      # One instance per application
    TRANSIENT = "transient"      # New instance every time
    SCOPED = "scoped"           # One instance per scope (request/session)

@dataclass
class ServiceDescriptor(Generic[T]):
    """Describes how to create and manage a service"""
    service_type: Type[T]
    implementation_factory: Optional[Callable[..., T]] = None
    implementation_type: Optional[Type[T]] = None
    lifetime: Lifetime = Lifetime.TRANSIENT
    instance: Optional[T] = None

class DIContainer:
    """Dependency Injection Container"""
    
    def __init__(self):
        self._services: Dict[Union[Type, str], ServiceDescriptor] = {}
        self._singletons: Dict[Union[Type, str], Any] = {}
        self._scoped_services: Dict[Union[Type, str], Any] = {}
        self._lock = threading.RLock()
        
        # Register self
        self.register_instance(DIContainer, self)
        
        logger.info("DI Container initialized")
    
    def register_transient(self, service_type: Type[T], implementation: Union[Type[T], Callable[..., T]]) -> 'DIContainer':
        """Register service with transient lifetime (new instance each time)"""
        return self._register(service_type, implementation, Lifetime.TRANSIENT)
    
    def register_singleton(self, service_type: Type[T], implementation: Union[Type[T], Callable[..., T]]) -> 'DIContainer':
        """Register service with singleton lifetime (one instance)"""
        return self._register(service_type, implementation, Lifetime.SINGLETON)
    
    def register_scoped(self, service_type: Type[T], implementation: Union[Type[T], Callable[..., T]]) -> 'DIContainer':
        """Register service with scoped lifetime (one instance per scope)"""
        return self._register(service_type, implementation, Lifetime.SCOPED)
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'DIContainer':
        """Register existing instance as singleton"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=type(instance),
                lifetime=Lifetime.SINGLETON,
                instance=instance
            )
            self._services[service_type] = descriptor
            self._singletons[service_type] = instance
            service_name = service_type.__name__ if hasattr(service_type, '__name__') else str(service_type)
            logger.debug(f"Registered instance: {service_name}")
            return self
    
    def register_factory(self, service_type: Union[Type[T], str], factory: Callable[..., T], lifetime: Lifetime = Lifetime.TRANSIENT) -> 'DIContainer':
        """Register factory function for service creation"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_factory=factory,
                lifetime=lifetime
            )
            self._services[service_type] = descriptor
            service_name = service_type.__name__ if hasattr(service_type, '__name__') else str(service_type)
            logger.debug(f"Registered factory: {service_name} ({lifetime.value})")
            return self
    
    def _register(self, service_type: Type[T], implementation: Union[Type[T], Callable[..., T]], lifetime: Lifetime) -> 'DIContainer':
        """Internal registration method"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_factory=implementation if callable(implementation) and not inspect.isclass(implementation) else None,
                implementation_type=implementation if inspect.isclass(implementation) else None,
                lifetime=lifetime
            )
            self._services[service_type] = descriptor
            service_name = service_type.__name__ if hasattr(service_type, '__name__') else str(service_type)
            impl_name = implementation.__name__ if hasattr(implementation, '__name__') else str(implementation)
            logger.debug(f"Registered: {service_name} -> {impl_name} ({lifetime.value})")
            return self
    
    def resolve(self, service_type: Union[Type[T], str]) -> T:
        """Resolve service instance with dependency injection"""
        with self._lock:
            return self._resolve_internal(service_type, set())
    
    def _resolve_internal(self, service_type: Union[Type[T], str], resolving: set) -> T:
        """Internal resolve with circular dependency detection"""
        if service_type in resolving:
            service_name = service_type.__name__ if hasattr(service_type, '__name__') else str(service_type)
            raise ValueError(f"Circular dependency detected for {service_name}")
        
        if service_type not in self._services:
            service_name = service_type.__name__ if hasattr(service_type, '__name__') else str(service_type)
            raise ValueError(f"Service not registered: {service_name}")
        
        descriptor = self._services[service_type]
        
        # Check for existing singleton
        if descriptor.lifetime == Lifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
            if descriptor.instance is not None:
                return descriptor.instance
        
        # Check for scoped instance
        if descriptor.lifetime == Lifetime.SCOPED:
            if service_type in self._scoped_services:
                return self._scoped_services[service_type]
        
        # Create new instance
        resolving.add(service_type)
        try:
            instance = self._create_instance(descriptor, resolving)
        finally:
            resolving.remove(service_type)
        
        # Cache based on lifetime
        if descriptor.lifetime == Lifetime.SINGLETON:
            self._singletons[service_type] = instance
        elif descriptor.lifetime == Lifetime.SCOPED:
            self._scoped_services[service_type] = instance
        
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor, resolving: set) -> Any:
        """Create instance using factory or constructor injection"""
        if descriptor.implementation_factory:
            # Use factory function
            return self._invoke_with_injection(descriptor.implementation_factory, resolving)
        
        if descriptor.implementation_type:
            # Use constructor injection
            constructor = descriptor.implementation_type.__init__
            if constructor == object.__init__:
                # No constructor parameters
                return descriptor.implementation_type()
            
            return self._invoke_with_injection(descriptor.implementation_type, resolving)
        
        service_name = descriptor.service_type.__name__ if hasattr(descriptor.service_type, '__name__') else str(descriptor.service_type)
        raise ValueError(f"No implementation defined for {service_name}")
    
    def _invoke_with_injection(self, callable_obj: Callable, resolving: set) -> Any:
        """Invoke callable with dependency injection"""
        signature = inspect.signature(callable_obj)
        kwargs = {}
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
                
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                continue
                
            if param.default != inspect.Parameter.empty:
                # Optional parameter - try to resolve, but continue if not registered
                try:
                    kwargs[param_name] = self._resolve_internal(param_type, resolving)
                except ValueError:
                    pass
            else:
                # Required parameter
                kwargs[param_name] = self._resolve_internal(param_type, resolving)
        
        return callable_obj(**kwargs)
    
    def clear_scoped(self):
        """Clear scoped services (call at end of request/session)"""
        with self._lock:
            self._scoped_services.clear()
            logger.debug("Cleared scoped services")
    
    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about registered services"""
        with self._lock:
            info = {}
            for service_type, descriptor in self._services.items():
                service_name = service_type.__name__ if hasattr(service_type, '__name__') else str(service_type)
                info[service_name] = {
                    "lifetime": descriptor.lifetime.value,
                    "implementation": (
                        descriptor.implementation_type.__name__ 
                        if descriptor.implementation_type 
                        else "factory"
                    ),
                    "is_singleton_created": service_type in self._singletons,
                    "is_scoped_created": service_type in self._scoped_services
                }
            return info

# Global container instance
_container: Optional[DIContainer] = None
_container_lock = threading.RLock()

def get_container() -> DIContainer:
    """Get global DI container instance"""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DIContainer()
                _setup_default_services(_container)
    return _container

def _setup_default_services(container: DIContainer):
    """Setup default service registrations"""
    logger.info("Setting up default service registrations")
    
    # Import and register services with proper DI
    def create_whisper_service():
        from aichat.backend.services.voice.stt.whisper_service import WhisperService
        return WhisperService()
    
    def create_chatterbox_tts_service():
        from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
        return ChatterboxTTSService()
    
    def create_audio_io_service():
        from aichat.backend.services.audio.audio_io_service import AudioIOService
        return AudioIOService()
    
    def create_chat_service():
        from aichat.backend.services.chat.chat_service import ChatService
        return ChatService()
    
    # Register with appropriate lifetimes
    container.register_factory("whisper_service", create_whisper_service, Lifetime.SINGLETON)
    container.register_factory("chatterbox_tts_service", create_chatterbox_tts_service, Lifetime.SINGLETON)
    container.register_factory("audio_io_service", create_audio_io_service, Lifetime.SINGLETON)
    container.register_factory("chat_service", create_chat_service, Lifetime.SCOPED)  # New instance per request

# Convenience functions for backward compatibility
def get_whisper_service():
    """Get WhisperService instance"""
    return get_container().resolve("whisper_service")

def get_chatterbox_tts_service():
    """Get ChatterboxTTSService instance"""  
    return get_container().resolve("chatterbox_tts_service")

def get_audio_io_service():
    """Get AudioIOService instance"""
    return get_container().resolve("audio_io_service")

def get_chat_service():
    """Get ChatService instance"""
    return get_container().resolve("chat_service")