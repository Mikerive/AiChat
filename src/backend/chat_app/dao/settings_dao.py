"""
Settings Data Access Object

Handles persistence operations for application settings and configuration.
Uses JSON files for storage with Pydantic model validation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, List
from datetime import datetime

try:
    from pydantic import BaseModel, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object
    class ValidationError(Exception):
        pass

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class SettingsError(Exception):
    """Raised when settings operations fail"""
    pass


class SettingsDAO:
    """
    Simplified Pydantic-based settings management
    
    Much simpler than the old custom validation approach:
    - Uses Pydantic's native JSON parsing
    - Automatic validation and coercion
    - Built-in enum handling
    """
    
    def __init__(self, settings_dir: Optional[Path] = None):
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic is required for settings management")
        
        self.settings_dir = settings_dir or Path("settings")
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        
        self._loaded_settings: Dict[str, BaseModel] = {}
        
        logger.info(f"Settings DAO initialized: {self.settings_dir}")
    
    def _get_settings_file(self, name: str) -> Path:
        """Get the settings file path for a given name"""
        return self.settings_dir / f"{name}.json"
    
    def load_settings(self, settings_class: Type[T], name: Optional[str] = None) -> T:
        """
        Load settings using Pydantic's native JSON parsing
        
        Much simpler than before - Pydantic handles all validation automatically
        """
        if name is None:
            name = settings_class.__name__.lower().replace('constants', '')
        
        settings_file = self._get_settings_file(name)
        
        # If file doesn't exist, return defaults and create file
        if not settings_file.exists():
            logger.info(f"Settings file not found: {settings_file}, creating with defaults")
            default_settings = settings_class()
            self.save_settings(default_settings, name)
            return default_settings
        
        try:
            # Load and parse with Pydantic - handles all validation automatically!
            with open(settings_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Remove metadata before parsing
            json_data.pop('_metadata', None)
            
            # Pydantic does all the heavy lifting: validation, coercion, enum handling
            settings = settings_class(**json_data)
            
            self._loaded_settings[name] = settings
            logger.info(f"Successfully loaded settings: {name}")
            return settings
            
        except ValidationError as e:
            logger.error(f"Validation errors in {settings_file}:")
            for error in e.errors():
                field = " -> ".join(str(x) for x in error['loc'])
                logger.error(f"  {field}: {error['msg']} (got {error.get('input', 'N/A')})")
            
            logger.info("Using default settings due to validation errors")
            return settings_class()
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in settings file {settings_file}: {e}")
            logger.info("Using default settings")
            return settings_class()
            
        except Exception as e:
            logger.error(f"Failed to load settings from {settings_file}: {e}")
            logger.info("Using default settings")
            return settings_class()
    
    def save_settings(self, settings: BaseModel, name: Optional[str] = None) -> bool:
        """
        Save settings using Pydantic's native JSON export
        
        Much simpler - Pydantic handles enum serialization automatically
        """
        if name is None:
            name = settings.__class__.__name__.lower().replace('constants', '')
        
        settings_file = self._get_settings_file(name)
        
        try:
            # Pydantic handles all serialization including enums!
            data = settings.dict()
            
            # Add metadata
            data['_metadata'] = {
                "version": "1.0",
                "last_modified": datetime.now().isoformat(),
                "source": "saved"
            }
            
            # Save to file
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._loaded_settings[name] = settings
            logger.info(f"Settings saved successfully: {settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save settings to {settings_file}: {e}")
            return False
    
    def reload_settings(self, settings_class: Type[T], name: Optional[str] = None) -> T:
        """Reload settings from file"""
        if name is None:
            name = settings_class.__name__.lower().replace('constants', '')
        
        # Remove from cache
        self._loaded_settings.pop(name, None)
        return self.load_settings(settings_class, name)
    
    def get_settings_info(self, name: str) -> Dict[str, Any]:
        """Get information about loaded settings"""
        settings_file = self._get_settings_file(name)
        
        return {
            'name': name,
            'file_path': str(settings_file),
            'exists': settings_file.exists(),
            'loaded': name in self._loaded_settings,
            'model_class': self._loaded_settings[name].__class__.__name__ if name in self._loaded_settings else None
        }
    
    def list_settings(self) -> List[str]:
        """List all available settings files"""
        return [f.stem for f in self.settings_dir.glob("*.json") if not f.stem.startswith('.')]
    
    def validate_settings(self, settings_class: Type[T], data: Dict[str, Any]) -> T:
        """Validate arbitrary data against a settings model"""
        try:
            return settings_class(**data)
        except ValidationError as e:
            logger.error("Validation failed:")
            for error in e.errors():
                field = " -> ".join(str(x) for x in error['loc'])
                logger.error(f"  {field}: {error['msg']}")
            raise SettingsError(f"Validation failed: {e}")
    
    def generate_schema(self, settings_class: Type[BaseModel]) -> Dict[str, Any]:
        """Generate JSON schema for a settings model"""
        return settings_class.schema()
    
    def update_setting(self, settings_class: Type[T], field_name: str, value: Any, name: Optional[str] = None) -> T:
        """
        Update a specific setting field at runtime and save to file
        
        Args:
            settings_class: The settings model class
            field_name: Name of the field to update
            value: New value for the field
            name: Settings name (defaults to class name)
        
        Returns:
            Updated settings instance
        """
        if name is None:
            name = settings_class.__name__.lower().replace('constants', '')
        
        # Load current settings
        current_settings = self.load_settings(settings_class, name)
        
        # Validate field exists
        if not hasattr(current_settings, field_name):
            raise SettingsError(f"Field '{field_name}' not found in {settings_class.__name__}")
        
        # Create updated dict
        updated_data = current_settings.dict()
        updated_data[field_name] = value
        
        # Validate the updated data
        try:
            updated_settings = settings_class(**updated_data)
        except ValidationError as e:
            raise SettingsError(f"Invalid value for {field_name}: {e}")
        
        # Save updated settings
        if not self.save_settings(updated_settings, name):
            raise SettingsError(f"Failed to save updated settings for {name}")
        
        logger.info(f"Updated setting {field_name} in {name}")
        return updated_settings
    
    def update_settings(self, settings_class: Type[T], updates: Dict[str, Any], name: Optional[str] = None) -> T:
        """
        Update multiple setting fields at runtime and save to file
        
        Args:
            settings_class: The settings model class  
            updates: Dictionary of field names and new values
            name: Settings name (defaults to class name)
        
        Returns:
            Updated settings instance
        """
        if name is None:
            name = settings_class.__name__.lower().replace('constants', '')
        
        # Load current settings
        current_settings = self.load_settings(settings_class, name)
        
        # Create updated dict
        updated_data = current_settings.dict()
        
        # Apply all updates
        for field_name, value in updates.items():
            if not hasattr(current_settings, field_name):
                raise SettingsError(f"Field '{field_name}' not found in {settings_class.__name__}")
            updated_data[field_name] = value
        
        # Validate the updated data
        try:
            updated_settings = settings_class(**updated_data)
        except ValidationError as e:
            raise SettingsError(f"Invalid updates: {e}")
        
        # Save updated settings
        if not self.save_settings(updated_settings, name):
            raise SettingsError(f"Failed to save updated settings for {name}")
        
        logger.info(f"Updated {len(updates)} settings in {name}: {list(updates.keys())}")
        return updated_settings
    
    def reset_settings(self, settings_class: Type[T], name: Optional[str] = None) -> T:
        """
        Reset settings to defaults and save to file
        
        Args:
            settings_class: The settings model class
            name: Settings name (defaults to class name)
        
        Returns:
            Default settings instance
        """
        if name is None:
            name = settings_class.__name__.lower().replace('constants', '')
        
        # Create default settings
        default_settings = settings_class()
        
        # Save defaults
        if not self.save_settings(default_settings, name):
            raise SettingsError(f"Failed to save default settings for {name}")
        
        logger.info(f"Reset settings to defaults: {name}")
        return default_settings